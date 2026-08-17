from __future__ import annotations

from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

from .data import get_portfolio_amounts
from .repositories import FilePortfolioRepository
from .run_context import build_run_manifest
from .validation import validate_analysis_inputs
from .run_context import create_run_id, infer_portfolio_id, now_ist
from .features import (
    arrange_portfolio_features,
    build_common_features,
    build_portfolio_membership,
)
from .technical import get_date_range


PORTFOLIO_OUTPUT_COLUMNS = [
    "Symbol",
    "AvgCost",
    "FTT",
    "FTT Amt",
    "Dev%_PE",
    "Spread%",
    "Conviction",
    "RSI_14",
    "RSP",
    "Shares",
    "Current",
    "Current P/L",
    "Today P/L%",
    "Current P/L%",
    "FTT%",
    "OTT%",
    "XIRR",
    "CurrAlloc%",
    "RRR Ind",
    "Criteria",
    "Strategy",
    "Dev%_200",
    "Risk Ind",
    "Gained%",
    "LatestQtr",
    "StarStock",
    "CumlRnk",
    "Category",
    "MBQ",
    "BusinessQuality",
    "PortfolioClass",
    "ThesisCaptured%",
    "RemainingUpside%",
    "RotationStatus",
]


IST = ZoneInfo("Asia/Kolkata")


def config_priority_map_from_features(df, config=None):
    """Return the default conviction hierarchy without coupling portfolio math to config parsing."""
    # The exact map is imported lazily to avoid a module-level dependency cycle.
    from .prospects import DEFAULT_CONVICTION_PRIORITY
    configured = (config or {}).get("ranking", {}).get("conviction_priority")
    return configured or DEFAULT_CONVICTION_PRIORITY.copy()


def calculate_portfolio_features(
    df_common_features,
    portfolio_df,
    config=None,
):
    """
    Calculate stock-level portfolio features.

    This function contains portfolio calculations only.
    It does not print or display anything.
    """

    df = df_common_features.copy()

    # ---------------------------------------------------------
    # Targets
    # ---------------------------------------------------------

    df["NTT"] = np.where(
        df["Strategy"] == "NTT",
        df["Target"],
        df["Max"],
    )

    df["LTT"] = np.where(
        df["Strategy"] == "BTT",
        df["Target"],
        df["Max"],
    )

    df["BOL"] = df["Min"]

    # ---------------------------------------------------------
    # Select portfolio stocks
    # ---------------------------------------------------------

    symbols = portfolio_df.loc[
        portfolio_df["InPortfolio"] != "NA",
        "Symbol",
    ].values

    df = df[
        df["Symbol"].isin(symbols)
    ].copy()

    # ---------------------------------------------------------
    # Investment / current value
    # ---------------------------------------------------------

    df["Investment"] = (
        df["AvgCost"] * df["Shares"]
    )

    df["Current"] = round(
        df["Close"] * df["Shares"],
        0,
    )

    df["Previous"] = (
        df["Prev_Close"] * df["Shares"]
    )

    df["EstimatedST"] = (
        df["NTT"] * df["Shares"]
    )

    df["EstimatedLT"] = (
        df["LTT"] * df["Shares"]
    )

    # ---------------------------------------------------------
    # P/L
    # ---------------------------------------------------------

    df["Current P/L"] = round(
        df["Current"] - df["Investment"],
        0,
    )

    df["Today P/L%"] = round(
        (
            (df["Current"] - df["Previous"])
            * 100
            / df["Previous"]
        ),
        2,
    )

    df["Current P/L%"] = round(
        (
            (df["Current"] - df["Investment"])
            * 100
            / df["Investment"]
        ),
        2,
    )

    df["EstimatedST P/L%"] = round(
        (
            (df["EstimatedST"] - df["Investment"])
            * 100
            / df["Investment"]
        ),
        2,
    )

    df["EstimatedLT P/L%"] = round(
        (
            (df["EstimatedLT"] - df["Investment"])
            * 100
            / df["Investment"]
        ),
        2,
    )

    # ---------------------------------------------------------
    # Target percentages
    # ---------------------------------------------------------

    df["NTT%"] = round(
        (
            (df["NTT"] - df["Close"])
            * 100
            / df["Close"]
        ),
        2,
    )

    df["LTT%"] = round(
        (
            (df["LTT"] - df["Close"])
            * 100
            / df["Close"]
        ),
        2,
    )

    df["Gained%"] = round(
        (
            (df["Close"] - df["BOL"])
            * 100
            / df["BOL"]
        ),
        2,
    )

    # ---------------------------------------------------------
    # Portfolio allocation
    # ---------------------------------------------------------

    investment = round(
        (
            df["AvgCost"] * df["Shares"]
        ).sum(),
        0,
    )

    current = round(
        (
            df["Close"] * df["Shares"]
        ).sum(),
        0,
    )

    df["InitAlloc%"] = round(
        df["Investment"] * 100 / investment,
        2,
    )

    df["CurrAlloc%"] = round(
        df["Current"] * 100 / current,
        2,
    )

    # ---------------------------------------------------------
    # Final Target
    # ---------------------------------------------------------

    df["FTT"] = df["LTT"]

    df.loc[
        df["Strategy"] == "NTT",
        "FTT",
    ] = df["NTT"]

    df["FTT%"] = df["LTT%"]

    df.loc[
        df["Strategy"] == "NTT",
        "FTT%",
    ] = df["NTT%"]

    df["FTT Amt"] = round(
        df["FTT%"] * df["Current"] / 100,
        0,
    )

    # ---------------------------------------------------------
    # Return / Risk
    # ---------------------------------------------------------

    df["OTT%"] = round(
        (
            (df["FTT"] - df["AvgCost"])
            * 100
            / df["AvgCost"]
        ),
        2,
    )

    df["RRR Ind"] = round(
        df["Current P/L"] / df["FTT Amt"],
        2,
    )

    # ---------------------------------------------------------
    # Thesis completion / capital rotation state
    # ---------------------------------------------------------

    # ``Current`` is total position value, while AvgCost/FTT are per-share
    # values. Convert Current back to a per-share CMP before calculating the
    # thesis completion metrics.
    current_price = np.where(
        df["Shares"] > 0,
        df["Current"] / df["Shares"],
        np.nan,
    )
    thesis_denominator = df["FTT"] - df["AvgCost"]
    df["ThesisCaptured%"] = np.where(
        thesis_denominator > 0,
        (current_price - df["AvgCost"]) / thesis_denominator,
        np.nan,
    )
    df["RemainingUpside%"] = np.where(
        current_price > 0,
        (df["FTT"] - current_price) / current_price,
        np.nan,
    )

    # The conviction hierarchy is deliberately kept as the source of truth.
    # The first six buckets are the current preferred/core universe; the rest
    # remain valid portfolio holdings but are treated as legacy positions.
    priority_map = config_priority_map_from_features(df, config)
    core_convictions = set(priority_map.keys())
    if len(priority_map) >= 6:
        first_six = list(priority_map)[:6]
        core_convictions = set(first_six)
    df["PortfolioClass"] = np.where(
        df["Conviction"].isin(core_convictions), "CORE", "LEGACY"
    )
    df["BusinessQuality"] = (
        df["Conviction"].astype(str).str.split("-").str[0]
    )

    review = float(
        (config or {}).get("rotation", {})
        .get("thesis_captured", {})
        .get("review", 0.80)
    )
    strong_review = float(
        (config or {}).get("rotation", {})
        .get("thesis_captured", {})
        .get("strong_review", 0.90)
    )

    df["RotationStatus"] = "HOLD"
    df.loc[df["PortfolioClass"].eq("LEGACY"), "RotationStatus"] = "LEGACY_HOLD"
    df.loc[
        df["PortfolioClass"].eq("CORE")
        & (df["ThesisCaptured%"] >= review),
        "RotationStatus",
    ] = "ROTATION_REVIEW"
    df.loc[
        df["PortfolioClass"].eq("CORE")
        & (df["ThesisCaptured%"] >= strong_review),
        "RotationStatus",
    ] = "STRONG_ROTATION_REVIEW"
    df.loc[
        current_price >= df["FTT"],
        "RotationStatus",
    ] = "TARGET_REACHED"

    df["Risk Ind"] = round(
        df["Current P/L%"] * df["CurrAlloc%"],
        0,
    )

    return df


def calculate_portfolio_summary(
    df,
    investments_df,
    data,
    config=None,
    *,
    portfolio_id=None,
    run_id=None,
):
    """
    Calculate portfolio-level summary metrics.

    This function calculates and returns data only.
    It does not print, display, or format the result.

    Parameters
    ----------
    df : pandas.DataFrame
        Portfolio features.

    investments_df : pandas.DataFrame
        Historical investment transactions.

    data : dict
        Quantvesting data dictionary.

    config : dict, optional
        Strategy configuration. Reserved for future use.

    Returns
    -------
    dict
        Structured portfolio summary suitable for Jupyter,
        API or Web UI consumption.
    """

    # ---------------------------------------------------------
    # Portfolio amounts
    # ---------------------------------------------------------

    (
        total_booked_amt,
        reserve_amt,
        cy_booked_amt,
        py_booked_amt,
    ) = get_portfolio_amounts(data)

    # ---------------------------------------------------------
    # Run timestamp
    # ---------------------------------------------------------

    run_datetime = now_ist().strftime("%Y-%m-%d %H:%M:%S")
    portfolio_id = (
        portfolio_id
        or data.get("portfolio_id")
        or infer_portfolio_id(data.get("portfolio_dir"))
    )
    run_id = run_id or create_run_id()

    # ---------------------------------------------------------
    # XIRR
    # ---------------------------------------------------------

    dates = investments_df["Date"].values

    # Use the same IST business date used by EOD persistence. This avoids a
    # UTC/local-date mismatch around midnight.
    dates = np.append(
        dates,
        now_ist().strftime("%d-%b-%y"),
    )

    investment_values = (
        investments_df["Investment"].values
    )

    dates = pd.to_datetime(dates)

    current = (
        round(
            (
                df["Close"] * df["Shares"]
            ).sum(),
            0,
        )
        + reserve_amt
    )

    try:
        from pyxirr import xirr

        investment_xirr = np.append(
            investment_values,
            current,
        )

        cagr = round(
            xirr(
                pd.DataFrame(
                    {
                        "dates": dates,
                        "amounts": investment_xirr,
                    }
                )
            )
            * 100,
            2,
        )

    except Exception:
        # Keep engine usable if pyxirr is not installed
        # or XIRR cannot be calculated.
        cagr = np.nan

    # ---------------------------------------------------------
    # Investment
    # ---------------------------------------------------------

    initial_investment = -sum(
        investment_values
    )

    invested = (
        round(
            (
                df["AvgCost"] * df["Shares"]
            ).sum(),
            0,
        )
        + reserve_amt
    )

    previous = (
        round(
            (
                df["Prev_Close"] * df["Shares"]
            ).sum(),
            0,
        )
        + reserve_amt
    )

    cy_invested = (
        initial_investment
        + py_booked_amt
    )

    # ---------------------------------------------------------
    # Today's P/L
    # ---------------------------------------------------------

    today_pnl_amount = (
        current - previous
    )

    today_pnl_percentage = round(
        today_pnl_amount
        * 100
        / previous,
        2,
    )

    # ---------------------------------------------------------
    # Current P/L
    # ---------------------------------------------------------

    curr_pnl_amount = (
        current - invested
    )

    curr_pnl_percentage = round(
        curr_pnl_amount
        * 100
        / cy_invested,
        2,
    )

    # ---------------------------------------------------------
    # Current year P/L
    # ---------------------------------------------------------

    cy_pnl_amount = (
        cy_booked_amt
        + curr_pnl_amount
    )

    cy_pnl_percentage = round(
        cy_pnl_amount
        * 100
        / cy_invested,
        2,
    )

    # ---------------------------------------------------------
    # Overall P/L
    # ---------------------------------------------------------

    overall_pnl_amount = (
        total_booked_amt
        + curr_pnl_amount
    )

    overall_pnl_percentage = round(
        overall_pnl_amount
        * 100
        / initial_investment,
        2,
    )

    # ---------------------------------------------------------
    # Short-term estimate
    # ---------------------------------------------------------

    estimate_st = (
        round(
            (
                df["FTT"] * df["Shares"]
            ).sum(),
            0,
        )
        + reserve_amt
    )

    est_st_pnl_amount = (
        estimate_st - current
    )

    est_st_pnl_percentage = round(
        est_st_pnl_amount
        * 100
        / current,
        2,
    )

    # ---------------------------------------------------------
    # Long-term estimate
    # ---------------------------------------------------------

    estimate_lt = (
        round(
            (
                df["LTT"] * df["Shares"]
            ).sum(),
            0,
        )
        + reserve_amt
    )

    est_lt_pnl_amount = (
        estimate_lt - current
    )

    est_lt_pnl_percentage = round(
        est_lt_pnl_amount
        * 100
        / current,
        2,
    )

    # ---------------------------------------------------------
    # Profit / Loss split
    # ---------------------------------------------------------

    profitable = df[
        df["Current P/L%"] > 0
    ]

    losing = df[
        df["Current P/L%"] < 0
    ]

    total_profit = round(
        profitable["Current"].sum()
        - profitable["Investment"].sum(),
        0,
    )

    total_loss = round(
        losing["Current"].sum()
        - losing["Investment"].sum(),
        0,
    )

    # ---------------------------------------------------------
    # Booked P/L percentages
    # ---------------------------------------------------------

    total_booked_percentage = (
        round(total_booked_amt * 100 / initial_investment, 2)
        if initial_investment
        else np.nan
    )
    cy_booked_percentage = (
        round(cy_booked_amt * 100 / current, 2)
        if current
        else np.nan
    )
    py_booked_percentage = (
        round(py_booked_amt * 100 / initial_investment, 2)
        if initial_investment
        else np.nan
    )

    # ---------------------------------------------------------
    # Structured summary
    # ---------------------------------------------------------

    return {
        # Run identity / ownership metadata
        "portfolio_id": portfolio_id,
        "run_id": run_id,
        "run_datetime": run_datetime,
        "strategy_version": (
            config.get("strategy", {}).get("version")
            if config
            else None
        ),

        # Headline values used by the compact Jupyter/Web summary.
        # Investment transactions are stored as negative cash flows, so the
        # deployed capital shown to the user is the positive initial amount.
        "deployed": initial_investment,

        # Core portfolio values
        "initial_investment": initial_investment,
        "cy_invested": cy_invested,
        "reserve_amt": reserve_amt,
        "current": current,

        # Return
        "cagr_xirr": cagr,

        # Today's movement
        "today_pnl_amount": today_pnl_amount,
        "today_pnl_percentage": today_pnl_percentage,

        # Current P/L
        "curr_pnl_amount": curr_pnl_amount,
        "curr_pnl_percentage": curr_pnl_percentage,

        # Current year
        "cy_pnl_amount": cy_pnl_amount,
        "cy_pnl_percentage": cy_pnl_percentage,

        # Overall
        "overall_pnl_amount": overall_pnl_amount,
        "overall_pnl_percentage": overall_pnl_percentage,

        # Profit / Loss
        "total_profit": total_profit,
        "total_loss": total_loss,

        # Booked profits
        "total_booked_amt": total_booked_amt,
        "total_booked_percentage": total_booked_percentage,
        "cy_booked_amt": cy_booked_amt,
        "cy_booked_percentage": cy_booked_percentage,
        "py_booked_amt": py_booked_amt,
        "py_booked_percentage": py_booked_percentage,

        # Target estimates
        "estimate_st": estimate_st,
        "est_st_pnl_amount": est_st_pnl_amount,
        "est_st_pnl_percentage": est_st_pnl_percentage,

        "estimate_lt": estimate_lt,
        "est_lt_pnl_amount": est_lt_pnl_amount,
        "est_lt_pnl_percentage": est_lt_pnl_percentage,
    }


def run_portfolio_analysis(
    market_data,
    config=None,
    eod=False,
    portfolio_data=None,
    *,
    portfolio_id=None,
    run_id=None,
):
    """
    Main Quantvesting portfolio-analysis engine.

    Returns
    -------
    tuple
        (
            portfolio_dataframe,
            portfolio_summary
        )

    The function does not display or print anything.
    """

    # ---------------------------------------------------------
    # Load source data
    # ---------------------------------------------------------

    # Backward compatibility with the original single-directory data bundle.
    if portfolio_data is None and "portfolio_stocks" in market_data:
        legacy_data = market_data
        portfolio_data = legacy_data
        market_data = {
            "prospects": legacy_data["prospects"],
            "screener": legacy_data["screener"],
            "momentum": legacy_data.get("momentum", pd.DataFrame()),
        }

    if portfolio_data is None:
        raise ValueError(
            "Portfolio analysis requires portfolio_data. "
            "Use load_portfolio_data() for the user's portfolio folder."
        )

    # Only securities that can influence this portfolio run are treated as
    # active for market-data quality checks. The shared screener may contain
    # many other NSE securities; their issues are warnings only.
    active_symbols = set(
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

    portfolio_id = (
        portfolio_id
        or portfolio_data.get("portfolio_id")
        or infer_portfolio_id(portfolio_data.get("portfolio_dir"))
    )
    run_id = run_id or create_run_id()

    pfs = portfolio_data["portfolio_stocks"].copy()
    pps = market_data["prospects"].copy()
    screener = market_data["screener"].copy()
    investments = portfolio_data["investments"].copy()

    # ---------------------------------------------------------
    # Merge portfolio + prospect data
    # ---------------------------------------------------------

    # Keep the original holding-level rows in pfs because DM/SV shares and
    # AvgCost must still be aggregated separately below. However, InFolio is
    # a symbol-level reporting attribute, so derive it from the actual
    # portfolio holdings rather than trusting the prospect source's stale
    # value.
    portfolio_membership = build_portfolio_membership(pfs)
    pps = pps.drop(columns=["InFolio"], errors="ignore").merge(
        portfolio_membership,
        on="Symbol",
        how="left",
        validate="one_to_one",
    )
    pps["InFolio"] = pps["InFolio"].fillna("NA")

    mypf = pd.merge(
        pfs,
        pps,
        on="Symbol",
        validate="many_to_one",
    )

    # Keep every user holding. The original implementation explicitly
    # selected DM and SV, but the product boundary is now account-agnostic:
    # InPortfolio is treated as an account label and all holdings belonging
    # to the supplied portfolio are analysed together. DM/SV therefore keep
    # their existing combined behaviour, while future users can use other
    # account labels without changing the engine.
    stocks = mypf.copy()

    # ---------------------------------------------------------
    # Arrange portfolio features
    # ---------------------------------------------------------

    common_cols = [
        "Symbol",
        "Target",
        "Criteria",
        "Strategy",
        "CumlRnk",
        "LatestQtr",
        "StarStock",
        "MBQ",
        "Conviction",
        "Category",
        "InFolio",
        "Cyclical",
        "XIRR",
        "Remarks",
    ]

    diff_cols = [
        "Symbol",
        "AvgCost",
        "Shares",
    ]

    stocks = arrange_portfolio_features(
        stocks,
        common_cols,
        diff_cols,
    )

    # ---------------------------------------------------------
    # Date range
    # ---------------------------------------------------------

    start_date, end_date = get_date_range(
        config.get("data", {}).get(
            "lookback_days",
            365,
        ),
        config.get("data", {}).get(
            "end_date_offset_days",
            1,
        ),
    )

    # ---------------------------------------------------------
    # Common features
    # ---------------------------------------------------------

    common = build_common_features(
        stocks,
        screener,
        start_date,
        end_date,
        config,
    )

    # ---------------------------------------------------------
    # Portfolio features
    # ---------------------------------------------------------

    portfolio = calculate_portfolio_features(
        common,
        mypf,
        config=config,
    )

    # ---------------------------------------------------------
    # Portfolio summary
    # ---------------------------------------------------------

    summary = calculate_portfolio_summary(
        portfolio,
        investments,
        portfolio_data,
        config,
        portfolio_id=portfolio_id,
        run_id=run_id,
    )
    summary["validation"] = validation_report

    # ---------------------------------------------------------
    # Final output columns
    # ---------------------------------------------------------

    cols = [
        c
        for c in PORTFOLIO_OUTPUT_COLUMNS
        if c in portfolio.columns
    ]

    result = portfolio[
        cols
    ].copy()

    result.attrs["validation_report"] = validation_report
    result.attrs["portfolio_id"] = portfolio_id
    result.attrs["run_id"] = run_id
    result.attrs["strategy_version"] = summary.get("strategy_version")

    # ---------------------------------------------------------
    # Phase B: execution manifest / reproducibility metadata
    # ---------------------------------------------------------

    manifest = build_run_manifest(
        analysis_type="portfolio",
        run_id=run_id,
        portfolio_id=portfolio_id,
        strategy_version=summary.get("strategy_version"),
        config=config,
        market_data=market_data,
        portfolio_data=portfolio_data,
        eod=eod,
    )

    repository = portfolio_data.get("repository") or FilePortfolioRepository(
        portfolio_data["portfolio_dir"],
        portfolio_id=portfolio_id,
    )
    repository.append_run_manifest(manifest)

    # ---------------------------------------------------------
    # Optional EOD snapshot
    # ---------------------------------------------------------

    if eod:
        _save_eod_snapshot(
            portfolio_data,
            summary,
        )

    return result, summary



def _save_eod_snapshot(data, summary):
    """Persist the final portfolio summary for the current IST date.

    The repository canonicalises the date to DD-MM-YYYY, upserts by the
    parsed calendar date and sorts the complete history chronologically.
    This also fixes the old YYYY-MM-DD vs DD-MM-YYYY mismatch that could
    create duplicate snapshots for the same day.
    """
    portfolio_dir = data.get("portfolio_dir")

    snapshot_date = now_ist().strftime("%d-%m-%Y")
    row = {
        "date": snapshot_date,
        **summary,
    }

    if not portfolio_dir:
        # Legacy callers may pass an in-memory data dictionary. Preserve the
        # previous behaviour by returning the row instead of failing.
        return row

    repository = data.get("repository") or FilePortfolioRepository(
        portfolio_dir,
        portfolio_id=summary.get("portfolio_id"),
    )
    repository.append_eod_snapshot(row)

    return row
