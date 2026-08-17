from __future__ import annotations

import numpy as np
import pandas as pd

from .run_context import (
    build_run_manifest,
    create_run_id,
    infer_portfolio_id,
)
from .repositories import FilePortfolioRepository
from .validation import validate_analysis_inputs

from .features import (
    build_common_features,
    build_portfolio_membership,
    validate_unique_symbols,
)


PROSPECT_OUTPUT_COLUMNS = [
    "BusinessQuality", "PortfolioClass", "Eligible", "OpportunityScore", "OpportunityBand",
    "Symbol", "Close", "FTT", "Dev%_200", "Dev%_PE", "Spread%",
    "Curr_PE", "MedPE", "Conviction", "Cyclical", "RSI_14", "RSP",
    "Today%", "FTT%", "ATH%", "Gained%", "CumlRnk", "ROE%/PE",
    "Criteria", "Strategy", "Sales_Grwth%", "Profit_Grwth%", "Category",
    "InFolio", "MCap", "MBQ", "CFO_2_EBITDA%", "ROE%",
]

DEFAULT_CONVICTION_PRIORITY = {
    "X-LC": 0,
    "H-LC": 1,
    "X-MC": 2,
    "X-SC": 3,
    "M-LC": 4,
    "H-MC": 5,
    "H-SC": 6,
    "L-LC": 7,
    "M-MC": 8,
    "M-SC": 9,
    "L-MC": 10,
    "L-SC": 11,
}

DEFAULT_RANKING = {
    "value": ["Dev%_200", "Dev%_PE", "ROE%/PE"],
    "growth": ["Sales_Grwth%", "Profit_Grwth%"],
    "quality": ["FTT%", "MCap", "ROE%", "CFO_2_EBITDA%"],
    "momentum": ["Gained%", "RSI_14"],
}

CORE_CONVICTION_COUNT = 6


DEFAULT_RANK_DIRECTIONS = {
    "Dev%_200": True,
    "Dev%_PE": True,
    "ROE%/PE": False,
    "Sales_Grwth%": False,
    "Profit_Grwth%": False,
    "FTT%": False,
    "MCap": False,
    "ROE%": False,
    "CFO_2_EBITDA%": False,
    "Gained%": True,
    "RSI_14": False,
}


def calculate_prospect_features(df):
    """Calculate the prospect target, return and FTT features."""
    df = df.copy()

    df["NTT"] = np.where(
        df["Strategy"] == "NTT", df["Target"], df["Max"]
    )
    df["LTT"] = np.where(
        df["Strategy"] == "BTT", df["Target"], df["Max"]
    )
    df["BOL"] = df["Min"]

    df["Today%"] = round(
        (df["Close"] - df["Prev_Close"]) * 100 / df["Prev_Close"], 2
    )
    df["ATH%"] = round(
        (df["Max"] - df["Close"]) * 100 / df["Close"], 2
    )
    df["NTT%"] = round(
        (df["NTT"] - df["Close"]) * 100 / df["Close"], 2
    )
    df["LTT%"] = round(
        (df["LTT"] - df["Close"]) * 100 / df["Close"], 2
    )
    df["Gained%"] = round(
        (df["Close"] - df["BOL"]) * 100 / df["BOL"], 2
    )

    df["FTT"] = df["LTT"]
    df.loc[df["Strategy"] == "NTT", "FTT"] = df["NTT"]

    df["FTT%"] = df["LTT%"]
    df.loc[df["Strategy"] == "NTT", "FTT%"] = df["NTT%"]

    return df


def _get_ranking_config(config):
    ranking_cfg = config.get("ranking", {})

    categories = ranking_cfg.get("categories", DEFAULT_RANKING)
    directions = ranking_cfg.get("directions", DEFAULT_RANK_DIRECTIONS)
    weights = ranking_cfg.get("category_weights", {
        "value": 1.0,
        "growth": 1.0,
        "quality": 1.0,
        "momentum": 1.0,
    })

    return categories, directions, weights


def _eligible_prospect_mask(df, config):
    """Apply the MBQ/Conviction candidate rules used by the notebook."""
    ranking_cfg = config.get("ranking", {})
    mbq_include = ranking_cfg.get(
        "quality_mbq_contains",
        ["X40", "X5K"],
    )
    mbq_exclude = ranking_cfg.get(
        "quality_mbq_exclude_contains",
        ["OX40", "OX40N"],
    )
    conviction_include = ranking_cfg.get(
        "quality_convictions",
        ["X-LC", "H-LC", "X-MC", "X-SC"],
    )

    mbq = df["MBQ"].fillna("").astype(str)
    conviction = df["Conviction"].fillna("").astype(str)

    include_mbq = pd.Series(False, index=df.index)
    for token in mbq_include:
        include_mbq |= mbq.str.contains(str(token), na=False)

    exclude_mbq = pd.Series(False, index=df.index)
    for token in mbq_exclude:
        exclude_mbq |= mbq.str.contains(str(token), na=False)

    include_conviction = conviction.isin(conviction_include)

    return (include_mbq | include_conviction) & ~exclude_mbq


def calculate_cumulative_rank(df, config):
    """Calculate the current Quantvesting rank while preserving the conviction hierarchy.

    The twelve-level ``conviction_priority`` map remains the strategic ordering.
    Only the first six configured convictions are rankable for new opportunities;
    lower-priority convictions remain visible as LEGACY rows but do not compete
    for new capital through ``CumlRnk``.
    """
    df = df.copy()
    categories, directions, category_weights = _get_ranking_config(config)
    priority_map = ranking_cfg_priority_map(config)
    rankable = config.get("ranking", {}).get(
        "rankable_convictions", list(priority_map)[:CORE_CONVICTION_COUNT]
    )

    ranked = df.copy()
    ranked["Conviction_Priority"] = ranked["Conviction"].map(priority_map).fillna(9999)
    ranked["PortfolioClass"] = np.where(
        ranked["Conviction"].isin(rankable), "CORE", "LEGACY"
    )
    ranked["BusinessQuality"] = ranked["Conviction"].astype(str).str.split("-").str[0]
    ranked["Eligible"] = ranked["PortfolioClass"].eq("CORE")

    core = ranked[ranked["Eligible"]].copy()

    category_score_columns = []
    for category, metrics in categories.items():
        metric_rank_columns = []
        for metric in metrics:
            if metric not in core.columns:
                continue
            rank_column = f"Rnk_{metric}"
            ascending = directions.get(metric, DEFAULT_RANK_DIRECTIONS.get(metric, True))
            core[rank_column] = core[metric].rank(method="min", ascending=ascending)
            metric_rank_columns.append(rank_column)

        score_column = f"Rank_{category.title()}"
        if metric_rank_columns:
            core[score_column] = core[metric_rank_columns].sum(axis=1)
            core[score_column] *= category_weights.get(category, 1.0)
        else:
            core[score_column] = np.nan
        category_score_columns.append(score_column)

    core["Ovrl_Rank"] = (
        core[category_score_columns].sum(axis=1) if category_score_columns else np.nan
    )
    core["OpportunityScore"] = core["Ovrl_Rank"]
    core["Cat_Rank"] = core.groupby("Conviction")["Ovrl_Rank"].rank(ascending=True, method="min")

    core = core.sort_values(
        by=["Conviction_Priority", "Cat_Rank"],
        ascending=[True, True],
        kind="stable",
    ).reset_index(drop=True)
    core["CumlRnk"] = core.index + 1

    # A deliberately simple, rank-relative band. It is descriptive only and
    # does not alter the existing ranking methodology.
    n = len(core)
    if n:
        top_n = max(1, int(np.ceil(n * 0.10)))
        attractive_n = max(top_n, int(np.ceil(n * 0.25)))
        core["OpportunityBand"] = np.select(
            [
                core["CumlRnk"] <= top_n,
                core["CumlRnk"] <= attractive_n,
            ],
            ["HIGH", "ATTRACTIVE"],
            default="WATCH",
        )
    else:
        core["OpportunityBand"] = np.nan

    # Legacy holdings remain visible but intentionally do not receive a new
    # opportunity rank. This prevents mediocre historical positions from
    # competing with the six preferred conviction buckets.
    legacy = ranked[~ranked["Eligible"]].copy()
    for col in ["Ovrl_Rank", "OpportunityScore", "Cat_Rank", "CumlRnk", "OpportunityBand"]:
        legacy[col] = np.nan

    combined = pd.concat([core, legacy], ignore_index=True, sort=False)
    return combined[["Symbol", "CumlRnk", "Ovrl_Rank", "Cat_Rank",
                     "Conviction_Priority", "BusinessQuality", "PortfolioClass",
                     "Eligible", "OpportunityScore", "OpportunityBand"]].copy()

def ranking_cfg_priority_map(config):
    configured = config.get("ranking", {}).get("conviction_priority")
    if configured:
        return configured
    return DEFAULT_CONVICTION_PRIORITY.copy()


def run_prospect_analysis(
    market_data,
    config,
    include_portfolio=True,
    portfolio_data=None,
    *,
    portfolio_id=None,
    run_id=None,
):
    """Main Quantvesting prospect-analysis engine.

    ``market_data`` contains shared Quantvesting data. ``portfolio_data`` is
    optional because prospect analysis can be run without a user's portfolio.

    For backward compatibility, the original single ``data`` dictionary
    produced by ``load_all_data()`` is also accepted as ``market_data``.
    """
    # Backward compatibility with the pre-v0.4 single-directory data bundle.
    if "portfolio_stocks" in market_data:
        legacy_data = market_data
        market_data = {
            "prospects": legacy_data["prospects"],
            "screener": legacy_data["screener"],
            "momentum": legacy_data.get("momentum", pd.DataFrame()),
        }
        portfolio_data = legacy_data

    pps = market_data["prospects"].copy()
    screener = market_data["screener"].copy()

    # The active market universe is the securities actually being analysed:
    # prospect securities plus current portfolio holdings when portfolio
    # context is enabled. Market records outside this set are reference data
    # and their quality issues must not fail the run.
    active_symbols = set(
        pps["Symbol"].dropna().astype(str).str.strip()
    )
    if include_portfolio and portfolio_data is not None:
        active_symbols.update(
            portfolio_data["portfolio_stocks"]["Symbol"]
            .dropna()
            .astype(str)
            .str.strip()
        )

    validation_report = validate_analysis_inputs(
        market_data,
        portfolio_data,
        active_symbols=active_symbols,
    )

    pfs = (
        portfolio_data["portfolio_stocks"].copy()
        if portfolio_data is not None
        else pd.DataFrame(columns=["Symbol", "InPortfolio"])
    )

    # Portfolio stocks are holding/account-level data and may contain
    # multiple rows for the same Symbol (e.g. one DM and one SV holding).
    # Prospects, however, is a security-level dataset and must contain one
    # row per Symbol. Aggregate portfolio membership before joining.
    if include_portfolio:
        portfolio_membership = build_portfolio_membership(pfs)
    else:
        portfolio_membership = pd.DataFrame(
            columns=["Symbol", "InFolio"]
        )

    prospects = pps.drop(columns=["InFolio"], errors="ignore").copy()
    prospects = pd.merge(
        prospects,
        portfolio_membership,
        how="left",
        on="Symbol",
        validate="one_to_one",
    )
    prospects["InFolio"] = prospects["InFolio"].fillna("NA")

    if not include_portfolio:
        prospects = prospects[prospects["InFolio"] == "NA"].copy()

    # This is a security-level dataset. Fail early rather than allowing a
    # duplicate Symbol to silently distort technical features or ranking.
    validate_unique_symbols(prospects, "Prospects")

    excluded = config.get("universe", {}).get("exclude_symbols", [])
    prospects = prospects[~prospects["Symbol"].isin(excluded)].copy()

    common_cols = [
        "Symbol", "Target", "Criteria", "Strategy", "LatestQtr",
        "StarStock", "MBQ", "Conviction", "Cyclical", "Category", "InFolio"
    ]
    prospects = prospects[common_cols].copy()

    start_date, end_date = _date_range(config)

    common = build_common_features(
        prospects, screener, start_date, end_date, config
    )
    common = calculate_prospect_features(common)

    rank_df = calculate_cumulative_rank(common, config)
    common = pd.merge(common, rank_df, on="Symbol", how="left")

    output_cols = [c for c in PROSPECT_OUTPUT_COLUMNS if c in common.columns]
    result = common[output_cols].copy()

    if "CumlRnk" in result.columns:
        result = result.sort_values("CumlRnk", na_position="last")

    max_count = config.get("prospects", {}).get("max_count")
    if max_count:
        result = result.head(max_count)

    result = result.reset_index(drop=True)

    # Lightweight run metadata keeps the DataFrame API unchanged while making
    # each execution identifiable for later historical/API persistence.
    result.attrs["portfolio_id"] = (
        portfolio_id
        or (
            portfolio_data.get("portfolio_id")
            if portfolio_data is not None
            else None
        )
        or infer_portfolio_id(
            portfolio_data.get("portfolio_dir")
            if portfolio_data is not None
            else None
        )
    )
    result.attrs["run_id"] = run_id or create_run_id()
    result.attrs["strategy_version"] = (
        config.get("strategy", {}).get("version")
        if config else None
    )
    result.attrs["validation_report"] = validation_report

    # Phase B: persist an execution manifest when a user portfolio is available.
    # Pure market-only prospect runs remain side-effect free.
    if portfolio_data is not None and portfolio_data.get("portfolio_dir"):
        manifest = build_run_manifest(
            analysis_type="prospects",
            run_id=result.attrs["run_id"],
            portfolio_id=result.attrs["portfolio_id"],
            strategy_version=result.attrs["strategy_version"],
            config=config,
            market_data=market_data,
            portfolio_data=portfolio_data,
            eod=False,
        )
        repository = portfolio_data.get("repository") or FilePortfolioRepository(
            portfolio_data["portfolio_dir"],
            portfolio_id=result.attrs["portfolio_id"],
        )
        repository.append_run_manifest(manifest)

    return result


def _date_range(config):
    from .technical import get_date_range

    data_cfg = config.get("data", {})
    return get_date_range(
        data_cfg.get("lookback_days", 365),
        data_cfg.get("end_date_offset_days", 1),
    )
