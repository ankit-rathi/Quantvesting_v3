"""Input validation for the Quantvesting Phase-B data contract.

Validation is deliberately scope-aware:

* Shared market data may contain incomplete records for securities that are
  outside the current Quantvesting analysis universe. Those issues are
  reported as warnings and never stop the run.
* Data that belongs to the active analysis universe is checked more strictly.
* Missing numeric values (NaN/blank) are treated as missing data, not as
  malformed data. A calculation that requires such a field should mark the
  affected candidate as incomplete rather than failing the whole run.
* Actual non-numeric/corrupt populated values in the active universe remain
  validation errors.

This keeps the market repository broad while keeping investment decisions
safe and transparent.
"""
from __future__ import annotations

import warnings as _warnings
from typing import Iterable

import pandas as pd


class DataValidationError(ValueError):
    """Raised when active Quantvesting input violates the data contract."""


def _require_columns(df: pd.DataFrame, required: set[str], name: str) -> None:
    missing = sorted(required.difference(df.columns))
    if missing:
        raise DataValidationError(
            f"{name} is missing required columns: {missing}"
        )


def _require_non_empty(df: pd.DataFrame, name: str) -> None:
    if df is None or df.empty:
        raise DataValidationError(f"{name} is empty.")


def _normalise_symbols(values: Iterable) -> set[str]:
    return {
        str(value).strip()
        for value in values
        if pd.notna(value) and str(value).strip()
    }


def _emit_quality_warning(message: str, report: dict) -> None:
    report.setdefault("warnings", []).append(message)
    _warnings.warn(message, UserWarning, stacklevel=3)


def validate_market_data(
    market_data: dict,
    active_symbols: Iterable | None = None,
) -> dict:
    """Validate shared market/strategy data with active-universe scoping.

    Parameters
    ----------
    market_data:
        Shared market data containing at least ``prospects`` and ``screener``.
    active_symbols:
        Symbols currently participating in the analysis. When supplied,
        malformed records outside this set are warnings only.

    Returns
    -------
    dict
        Validation report with ``status``, ``warnings`` and ``info``.
    """
    if not isinstance(market_data, dict):
        raise DataValidationError("market_data must be a dictionary.")

    report = {
        "status": "SUCCESS",
        "errors": [],
        "warnings": [],
        "info": [],
        "active_symbols": sorted(_normalise_symbols(active_symbols or [])),
    }

    prospects = market_data.get("prospects")
    screener = market_data.get("screener")

    _require_non_empty(prospects, "Prospects data")
    _require_non_empty(screener, "Screener data")

    _require_columns(
        prospects,
        {
            "Symbol", "Target", "Criteria", "Strategy", "LatestQtr",
            "StarStock", "MBQ", "Conviction", "Cyclical", "Category",
        },
        "Prospects data",
    )
    _require_columns(
        screener,
        {"Symbol", "EPS", "MedPE", "MCap", "CapType"},
        "Screener data",
    )

    active = _normalise_symbols(active_symbols or prospects["Symbol"])
    report["active_symbols"] = sorted(active)

    # Prospects are themselves the analysis universe, so duplicate symbols
    # remain a hard error. They can otherwise silently duplicate technical
    # features and ranking rows.
    _validate_unique_symbols(
        prospects,
        "Prospects data",
        active_symbols=active,
        report=report,
    )

    # Screener is a broad market dataset. Duplicate/malformed records outside
    # the active universe are warnings; active duplicates remain errors.
    _validate_unique_symbols(
        screener,
        "Screener data",
        active_symbols=active,
        report=report,
    )

    _validate_numeric_columns(
        screener,
        {"EPS", "MedPE", "MCap"},
        "Screener data",
        active_symbols=active,
        report=report,
    )

    if report["warnings"]:
        report["status"] = "SUCCESS_WITH_WARNINGS"

    return report


def validate_portfolio_data(portfolio_data: dict) -> dict:
    """Validate one user's portfolio data bundle."""
    if not isinstance(portfolio_data, dict):
        raise DataValidationError("portfolio_data must be a dictionary.")

    stocks = portfolio_data.get("portfolio_stocks")
    investments = portfolio_data.get("investments")

    _require_non_empty(stocks, "Portfolio stocks")
    _require_non_empty(investments, "Investment history")

    _require_columns(
        stocks,
        {"Symbol", "Shares", "AvgCost", "InPortfolio"},
        "Portfolio stocks",
    )
    _require_columns(
        investments,
        {"Date", "Investment", "InPortfolio"},
        "Investment history",
    )

    _validate_numeric_columns(
        stocks,
        {"Shares", "AvgCost"},
        "Portfolio stocks",
    )
    _validate_numeric_columns(
        investments,
        {"Investment"},
        "Investment history",
    )

    if (stocks["Shares"] < 0).any():
        raise DataValidationError("Portfolio stocks contains negative Shares.")
    if (stocks["AvgCost"] < 0).any():
        raise DataValidationError("Portfolio stocks contains negative AvgCost.")

    if (
        stocks["Symbol"].isna().any()
        or stocks["Symbol"].astype(str).str.strip().eq("").any()
    ):
        raise DataValidationError("Portfolio stocks contains a blank Symbol.")

    return {
        "status": "SUCCESS",
        "errors": [],
        "warnings": [],
        "info": [],
    }


def validate_analysis_inputs(
    market_data: dict,
    portfolio_data: dict | None = None,
    active_symbols: Iterable | None = None,
) -> dict:
    """Validate inputs for an analysis run.

    ``active_symbols`` should be supplied by the analysis layer because that
    layer knows which securities will actually influence the calculation.
    """
    market_report = validate_market_data(
        market_data,
        active_symbols=active_symbols,
    )

    portfolio_report = (
        validate_portfolio_data(portfolio_data)
        if portfolio_data is not None
        else {"status": "SUCCESS", "errors": [], "warnings": [], "info": []}
    )

    warnings_list = (
        market_report.get("warnings", [])
        + portfolio_report.get("warnings", [])
    )

    return {
        "status": "SUCCESS_WITH_WARNINGS" if warnings_list else "SUCCESS",
        "errors": [],
        "warnings": warnings_list,
        "info": market_report.get("info", []) + portfolio_report.get("info", []),
        "market": market_report,
        "portfolio": portfolio_report,
    }


def _validate_unique_symbols(
    df: pd.DataFrame,
    name: str,
    active_symbols: set[str] | None = None,
    report: dict | None = None,
) -> None:
    if "Symbol" not in df.columns:
        return

    symbols = df["Symbol"].astype("string").str.strip()
    duplicate_symbols = (
        symbols[symbols.duplicated(keep=False)]
        .dropna()
        .unique()
        .tolist()
    )

    if not duplicate_symbols:
        return

    if active_symbols is None:
        raise DataValidationError(
            f"{name} contains duplicate Symbols: {duplicate_symbols}"
        )

    active_duplicates = [
        symbol for symbol in duplicate_symbols if symbol in active_symbols
    ]
    outside_duplicates = [
        symbol for symbol in duplicate_symbols if symbol not in active_symbols
    ]

    if active_duplicates:
        raise DataValidationError(
            f"{name} contains duplicate Symbols in the active universe: "
            f"{active_duplicates}"
        )

    if outside_duplicates and report is not None:
        _emit_quality_warning(
            f"{name} contains duplicate Symbols outside the active universe: "
            f"{outside_duplicates[:10]}"
            + (" ..." if len(outside_duplicates) > 10 else "")
            + ". Pipeline continues.",
            report,
        )


def _validate_numeric_columns(
    df: pd.DataFrame,
    columns: set[str],
    name: str,
    active_symbols: set[str] | None = None,
    report: dict | None = None,
) -> None:
    """Validate populated numeric values; NaN is treated as missing, not bad."""
    for column in columns:
        converted = pd.to_numeric(df[column], errors="coerce")

        # A missing value is legitimate market-data incompleteness. It is
        # handled later by the feature/ranking layer for candidates that need
        # the field. We still report it so a run is transparent.
        missing_mask = df[column].isna()
        if missing_mask.any() and report is not None:
            missing_active = (
                missing_mask
                & df["Symbol"].astype("string").str.strip().isin(active_symbols or set())
            )
            missing_outside = missing_mask & ~missing_active

            if missing_active.any():
                symbols = (
                    df.loc[missing_active, "Symbol"]
                    .astype(str).str.strip().head(10).tolist()
                )
                report.setdefault("info", []).append(
                    f"{name}.{column} is missing for active securities "
                    f"{symbols}"
                    + (" ..." if missing_active.sum() > 10 else "")
                    + ". Affected calculations may be incomplete."
                )

            if missing_outside.any():
                symbols = (
                    df.loc[missing_outside, "Symbol"]
                    .astype(str).str.strip().head(10).tolist()
                )
                report.setdefault("info", []).append(
                    f"{name}.{column} is missing outside the active universe "
                    f"for {symbols}"
                    + (" ..." if missing_outside.sum() > 10 else "")
                    + ". Pipeline continues."
                )

        invalid_mask = df[column].notna() & converted.isna()

        if not invalid_mask.any():
            continue

        bad = df.loc[invalid_mask, ["Symbol", column]].head(10)

        if active_symbols is None:
            bad_symbols = set(df.loc[invalid_mask, "Symbol"].astype(str).str.strip())
            raise DataValidationError(
                f"{name}.{column} contains non-numeric values for active data: "
                f"{bad[column].tolist()}"
            )

        active_mask = (
            invalid_mask
            & df["Symbol"].astype("string").str.strip().isin(active_symbols)
        )

        active_bad = df.loc[active_mask, column].head(5).tolist()
        outside_bad = df.loc[invalid_mask & ~active_mask, column].head(5).tolist()

        if active_mask.any():
            raise DataValidationError(
                f"{name}.{column} contains non-numeric values in the active "
                f"universe: {active_bad}"
            )

        if outside_bad and report is not None:
            symbols = (
                df.loc[invalid_mask & ~active_mask, "Symbol"]
                .astype(str)
                .str.strip()
                .head(10)
                .tolist()
            )
            _emit_quality_warning(
                f"{name}.{column} contains non-numeric populated values "
                f"outside the active universe for {symbols}. "
                f"Pipeline continues.",
                report,
            )
