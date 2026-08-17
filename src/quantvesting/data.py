from __future__ import annotations

from pathlib import Path
import json

import pandas as pd
import yaml

from .repositories import (
    FileMarketDataRepository,
    FilePortfolioRepository,
)
from .run_context import infer_portfolio_id


# -----------------------------------------------------------------------------
# Data ownership model
# -----------------------------------------------------------------------------

DEFAULT_MARKET_FILES = {
    "prospects": "myProspectsScrips.csv",
    "screener": "myScreenerDB.csv",
    "momentum": "myProspects-Momentum.csv",
    "screener_xlsx": "myScreenerDB.xlsx",
}

DEFAULT_PORTFOLIO_FILES = {
    "portfolio_stocks": "myPortfolioStocks.csv",
    "investments": "myInvestments.csv",
    "xirr": "myStocks-XIRR.csv",
    "portfolio_history": "myPortfolioDB.csv",
    "portfolio_amounts": "myPortfolioAmts.json",
    "runs": "myRuns.csv",
}

# Kept for backward compatibility with the original single-directory layout.
DEFAULT_FILES = {
    **DEFAULT_PORTFOLIO_FILES,
    **DEFAULT_MARKET_FILES,
}


class DataLoadError(FileNotFoundError):
    """Raised when a required Quantvesting data file is missing."""


def load_config(config_path):
    """Load strategy YAML."""
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_csv(data_dir, filename, required=True):
    """Load a CSV from a directory with a useful missing-file error."""
    path = Path(data_dir) / filename
    if not path.exists():
        if required:
            raise DataLoadError(f"Required data file not found: {path}")
        return pd.DataFrame()
    return pd.read_csv(path)


def _load_json(data_dir, filename, required=False):
    path = Path(data_dir) / filename
    if not path.exists():
        if required:
            raise DataLoadError(f"Required data file not found: {path}")
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_market_data(market_dir):
    """
    Load Quantvesting-owned/shared market and strategy data.

    The loader is backed by ``FileMarketDataRepository`` so the engine already
    has a storage boundary. A PostgreSQL repository can later replace the file
    repository without changing the analysis modules.
    """
    return FileMarketDataRepository(market_dir).load()


def load_portfolio_data(portfolio_dir, portfolio_id=None):
    """
    Load one user's portfolio data.

    ``portfolio_id`` is optional for backward compatibility. When omitted,
    it is inferred from the final directory name, e.g. ``portfolio_data/ankit``
    -> ``ankit``.
    """
    return FilePortfolioRepository(
        portfolio_dir,
        portfolio_id=portfolio_id,
    ).load()


def load_quantvesting_data(
    market_dir,
    portfolio_dir=None,
    portfolio_id=None,
):
    """
    Load the separated Quantvesting data model.

    Returns
    -------
    tuple
        ``(market_data, portfolio_data)``.

    ``portfolio_dir`` may be ``None`` when only prospect analysis is required.
    """
    market_data = load_market_data(market_dir)

    portfolio_data = (
        load_portfolio_data(
            portfolio_dir,
            portfolio_id=portfolio_id,
        )
        if portfolio_dir is not None
        else None
    )

    return market_data, portfolio_data


def load_all_data(data_dir):
    """
    Backward-compatible loader for the original single-directory layout.

    New notebooks/application code should use ``load_market_data`` and
    ``load_portfolio_data`` (or ``load_quantvesting_data``) instead.
    """
    data_dir = Path(data_dir)

    data = {
        "portfolio_stocks": load_csv(
            data_dir,
            DEFAULT_FILES["portfolio_stocks"],
        ),
        "prospects": load_csv(
            data_dir,
            DEFAULT_FILES["prospects"],
        ),
        "screener": load_csv(
            data_dir,
            DEFAULT_FILES["screener"],
        ),
        "investments": load_csv(
            data_dir,
            DEFAULT_FILES["investments"],
        ),
        "momentum": load_csv(
            data_dir,
            DEFAULT_FILES["momentum"],
            required=False,
        ),
        "xirr": load_csv(
            data_dir,
            DEFAULT_FILES["xirr"],
            required=False,
        ),
        "runs": load_csv(
            data_dir,
            DEFAULT_FILES["runs"],
            required=False,
        ),
        "portfolio_id": infer_portfolio_id(data_dir),
        "portfolio_dir": str(data_dir),
    }

    data["portfolio_amounts"] = _load_json(
        data_dir,
        DEFAULT_FILES["portfolio_amounts"],
        required=False,
    )

    history_path = data_dir / DEFAULT_FILES["portfolio_history"]
    data["portfolio_history"] = (
        pd.read_csv(history_path)
        if history_path.exists()
        else pd.DataFrame()
    )

    return data


def get_portfolio_amounts(data):
    """Preserve the current DM + SV booked/reserve calculation."""
    pf_amts = data.get("portfolio_amounts", {})

    py_booked_amt = (
        pf_amts.get("py_booked_amt_dm", 0)
        + pf_amts.get("py_booked_amt_sv", 0)
    )
    cy_booked_amt = (
        pf_amts.get("cy_booked_amt_dm", 0)
        + pf_amts.get("cy_booked_amt_sv", 0)
    )
    reserve_amt = (
        pf_amts.get("reserve_amt_dm", 0)
        + pf_amts.get("reserve_amt_sv", 0)
    )
    total_booked_amt = py_booked_amt + cy_booked_amt

    return (
        total_booked_amt,
        reserve_amt,
        cy_booked_amt,
        py_booked_amt,
    )


def append_portfolio_history(data_dir, row):
    """
    Backward-compatible EOD persistence helper.

    New code should prefer ``FilePortfolioRepository.append_eod_snapshot``.
    """
    repository = FilePortfolioRepository(data_dir)
    repository.append_eod_snapshot(row)


def format_amt(number):
    """Backward-compatible Indian K/L/C amount formatter."""
    abs_number = abs(number)
    if abs_number >= 1_00_00_000:
        return f"{number / 1_00_00_000:.2f} C"
    if abs_number >= 1_00_000:
        return f"{number / 1_00_000:.2f} L"
    if abs_number >= 1_000:
        return f"{number / 1_000:.2f} K"
    return f"{number:.2f}"
