from __future__ import annotations

import numpy as np
import pandas as pd

from .technical import get_common_technical_features, get_relative_strength


SCREENER_COLUMNS = [
    "Symbol", "EPS", "MedPE", "ROCE%", "ROE%", "CapType",
    "Sales_Grwth%", "Profit_Grwth%", "MCap", "CFO_2_EBITDA%"
]


def get_screener_features(df):
    return df[SCREENER_COLUMNS].copy()


def build_portfolio_membership(portfolio_stocks):
    """
    Build a symbol-level portfolio membership view.

    ``myPortfolioStocks.csv`` is intentionally holding/account-level data:
    the same Symbol may appear once for DM and once for SV (or, in future,
    across multiple accounts). Prospect analysis is security-level and must
    therefore see exactly one row per Symbol.

    Examples
    --------
    ABBOTINDIA / DM + ABBOTINDIA / SV -> ABBOTINDIA / ``DM+SV``
    ASIANPAINT / DM                  -> ASIANPAINT / ``DM``

    The original holding-level dataframe is never modified.
    """
    required = {"Symbol", "InPortfolio"}
    missing = required.difference(portfolio_stocks.columns)
    if missing:
        raise ValueError(
            "Portfolio data is missing required columns: "
            f"{sorted(missing)}"
        )

    membership = portfolio_stocks[
        ["Symbol", "InPortfolio"]
    ].copy()

    membership = membership.dropna(subset=["Symbol", "InPortfolio"])
    membership["Symbol"] = membership["Symbol"].astype(str).str.strip()
    membership["InPortfolio"] = membership["InPortfolio"].astype(str).str.strip()
    membership = membership[membership["Symbol"] != ""]
    membership = membership[membership["InPortfolio"].ne("")]

    def _combine_accounts(values):
        # Preserve first-seen account order while removing duplicates.
        accounts = list(dict.fromkeys(values))
        return "+".join(accounts)

    membership = (
        membership
        .groupby("Symbol", as_index=False, sort=False)["InPortfolio"]
        .agg(_combine_accounts)
        .rename(columns={"InPortfolio": "InFolio"})
    )

    return membership


def validate_unique_symbols(df, name="DataFrame"):
    """Raise an error when a security-level dataframe has duplicate Symbols."""
    if "Symbol" not in df.columns:
        raise ValueError(f"{name} must contain a 'Symbol' column.")

    duplicates = df.loc[
        df["Symbol"].duplicated(keep=False),
        "Symbol",
    ].dropna().unique().tolist()

    if duplicates:
        raise ValueError(
            f"{name} contains duplicate Symbols: {duplicates}"
        )


def arrange_portfolio_features(df_stocks, common_cols, diff_cols):
    """Preserve the current averaging/aggregation logic for holdings."""
    common = df_stocks[common_cols].drop_duplicates().copy()
    diff = df_stocks[diff_cols].copy()

    diff["Investment"] = diff["AvgCost"] * diff["Shares"]
    diff = (
        diff.groupby("Symbol")[["Shares", "Investment"]]
        .sum()
        .reset_index()
    )
    diff["AvgCost"] = round(diff["Investment"] / diff["Shares"], 2)

    return pd.merge(diff, common, on="Symbol")


def build_common_features(df_symbols, screener_df, start_date, end_date, config):
    """Combine technical, screener and relative-strength features."""
    technical = get_common_technical_features(
        df_symbols["Symbol"], start_date, end_date, config
    )
    screener = get_screener_features(screener_df)
    rs = get_relative_strength(
        df_symbols["Symbol"],
        period=config.get("data", {}).get("relative_strength_period", "1mo"),
    )

    common = pd.merge(technical, df_symbols, on="Symbol")
    common = pd.merge(common, screener, on="Symbol", how="left")
    common = pd.merge(common, rs, on="Symbol", how="left")

    # Current framework calculations.
    common["Curr_PE"] = round(common["Close"] / common["EPS"], 1)
    common["Dev%_PE"] = round(
        (common["Curr_PE"] - common["MedPE"]) * 100 / common["MedPE"], 2
    )
    common["Conviction"] = (
        common["Conviction"].astype(str) + "-" + common["CapType"].astype(str)
    )

    if "ROE%" in common.columns:
        common["ROE%/PE"] = round(common["ROE%"] / common["Curr_PE"], 1)

    if "Date" in common.columns:
        common = common.drop(columns=["Date"])

    return common.reset_index(drop=True)
