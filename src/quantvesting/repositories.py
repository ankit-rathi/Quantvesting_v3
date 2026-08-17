from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Mapping

import json
import pandas as pd

from .run_context import canonical_date, infer_portfolio_id


EOD_HISTORY_COLUMNS = [
    "date", "investment", "cy_invested", "reserve_amt", "current",
    "today_pnl_amount", "today_pnl_percentage", "curr_pnl_amount",
    "curr_pnl_percentage", "cy_pnl_amount", "cy_pnl_percentage",
    "total_profit", "total_loss", "overall_pnl_amount",
    "overall_pnl_percentage", "total_booked_amt", "total_booked_percentage",
    "cy_booked_amt", "cy_booked_percentage", "py_booked_amt",
    "py_booked_percentage", "estimate_st", "est_st_pnl_amount",
    "est_st_pnl_percentage", "estimate_lt", "est_lt_pnl_amount",
    "est_lt_pnl_percentage", "cagr", "portfolio_id", "run_id",
    "run_datetime", "strategy_version", "deployed", "initial_investment",
    "cagr_xirr",
]

class MarketDataRepository(ABC):
    """Storage contract for shared Quantvesting market data."""

    @abstractmethod
    def load(self) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def save_screener(self, df: pd.DataFrame) -> None:
        raise NotImplementedError


class PortfolioRepository(ABC):
    """Storage contract for one user's portfolio data and run history."""

    @abstractmethod
    def load(self) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def append_eod_snapshot(self, row: Mapping[str, Any]) -> None:
        raise NotImplementedError

    def append_run_manifest(self, row: Mapping[str, Any]) -> None:
        """Persist a run manifest when the repository supports run history."""
        raise NotImplementedError(
            f"{type(self).__name__} does not implement run-manifest persistence."
        )


class FileMarketDataRepository(MarketDataRepository):
    """Filesystem implementation used by Colab/Jupyter and the free MVP."""

    FILES = {
        "prospects": "myProspectsScrips.csv",
        "screener": "myScreenerDB.csv",
        "momentum": "myProspects-Momentum.csv",
        "screener_xlsx": "myScreenerDB.xlsx",
    }

    def __init__(self, market_dir):
        self.market_dir = Path(market_dir)

    def _csv(self, key: str, required: bool = True) -> pd.DataFrame:
        path = self.market_dir / self.FILES[key]
        if not path.exists():
            if required:
                raise FileNotFoundError(f"Required market data file not found: {path}")
            return pd.DataFrame()
        return pd.read_csv(path)

    def load(self) -> dict[str, Any]:
        return {
            "prospects": self._csv("prospects", required=True),
            "screener": self._csv("screener", required=True),
            "momentum": self._csv("momentum", required=False),
        }

    def save_screener(self, df: pd.DataFrame) -> None:
        self.market_dir.mkdir(parents=True, exist_ok=True)
        df.to_csv(self.market_dir / self.FILES["screener"], index=False)


class FilePortfolioRepository(PortfolioRepository):
    """Filesystem implementation for one portfolio/user."""

    FILES = {
        "portfolio_stocks": "myPortfolioStocks.csv",
        "investments": "myInvestments.csv",
        "xirr": "myStocks-XIRR.csv",
        "portfolio_history": "myPortfolioDB.csv",
        "portfolio_amounts": "myPortfolioAmts.json",
        "runs": "myRuns.csv",
    }

    def __init__(self, portfolio_dir, portfolio_id: str | None = None):
        self.portfolio_dir = Path(portfolio_dir)
        self.portfolio_id = portfolio_id or infer_portfolio_id(self.portfolio_dir)

    def _csv(self, key: str, required: bool = True) -> pd.DataFrame:
        path = self.portfolio_dir / self.FILES[key]
        if not path.exists():
            if required:
                raise FileNotFoundError(f"Required portfolio data file not found: {path}")
            return pd.DataFrame()
        return pd.read_csv(path)

    def _json(self, key: str, required: bool = False) -> dict[str, Any]:
        path = self.portfolio_dir / self.FILES[key]
        if not path.exists():
            if required:
                raise FileNotFoundError(f"Required portfolio data file not found: {path}")
            return {}
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def load(self) -> dict[str, Any]:
        return {
            "portfolio_stocks": self._csv("portfolio_stocks", required=True),
            "investments": self._csv("investments", required=True),
            "xirr": self._csv("xirr", required=False),
            "portfolio_history": self._csv("portfolio_history", required=False),
            "runs": self._csv("runs", required=False),
            "portfolio_amounts": self._json("portfolio_amounts", required=False),
            "portfolio_dir": str(self.portfolio_dir),
            "portfolio_id": self.portfolio_id,
            "repository": self,
        }

    def append_eod_snapshot(self, row: Mapping[str, Any]) -> None:
        """Upsert one official EOD snapshot and persist history chronologically.

        Older Quantvesting snapshots used both ``DD-MM-YYYY`` and
        ``YYYY-MM-DD``.  The old implementation compared raw strings, so a
        new snapshot could coexist with an older representation of the same
        day and lexical sorting was not chronological.  Phase B canonicalises
        dates before upsert and sorts using parsed dates, while writing the
        familiar ``DD-MM-YYYY`` representation back to CSV.
        """
        self.portfolio_dir.mkdir(parents=True, exist_ok=True)
        path = self.portfolio_dir / self.FILES["portfolio_history"]

        new_row = dict(row)
        snapshot_date = canonical_date(new_row.get("date"))
        if not snapshot_date:
            raise ValueError("EOD snapshot requires a valid 'date'.")
        new_row["date"] = snapshot_date
        new_row.setdefault("portfolio_id", self.portfolio_id)

        # Keep the historical CSV contract populated. ``investment``/``cagr``
        # are the legacy names; ``initial_investment``/``cagr_xirr`` are their
        # Phase-B/API-friendly aliases. Both are written for new snapshots so
        # old and new rows remain schema-compatible.
        if "investment" not in new_row:
            new_row["investment"] = new_row.get(
                "initial_investment", new_row.get("deployed")
            )
        if "deployed" not in new_row:
            new_row["deployed"] = new_row.get("initial_investment", new_row.get("investment"))
        if "initial_investment" not in new_row:
            new_row["initial_investment"] = new_row.get("investment")
        if "cagr" not in new_row:
            new_row["cagr"] = new_row.get("cagr_xirr")
        if "cagr_xirr" not in new_row:
            new_row["cagr_xirr"] = new_row.get("cagr")

        history = pd.read_csv(path) if path.exists() else pd.DataFrame()

        if not history.empty:
            if "date" not in history.columns:
                raise ValueError(
                    f"Existing portfolio history has no 'date' column: {path}"
                )
            history["date"] = history["date"].map(canonical_date)
            # Remove malformed blank dates rather than allowing them to float
            # unpredictably in the final history.
            history = history[history["date"].ne("")].copy()
            history = history[history["date"] != snapshot_date].copy()

            # Backfill aliases in legacy rows without changing their numeric
            # values. This makes the persisted schema consistent after the
            # first Phase-B EOD save. Create missing alias columns when an
            # older history file predates them.
            for column in ("initial_investment", "deployed", "cagr_xirr"):
                if column not in history.columns:
                    history[column] = pd.NA
            if "investment" in history.columns:
                history["initial_investment"] = (
                    pd.to_numeric(history["initial_investment"], errors="coerce")
                    .fillna(pd.to_numeric(history["investment"], errors="coerce"))
                )
            history["deployed"] = (
                pd.to_numeric(history["deployed"], errors="coerce")
                .fillna(pd.to_numeric(history["initial_investment"], errors="coerce"))
            )
            if "cagr" in history.columns:
                history["cagr_xirr"] = (
                    pd.to_numeric(history["cagr_xirr"], errors="coerce")
                    .fillna(pd.to_numeric(history["cagr"], errors="coerce"))
                )

        history = pd.concat(
            [history, pd.DataFrame([new_row])],
            ignore_index=True,
            sort=False,
        )

        if "portfolio_id" in history.columns:
            history["portfolio_id"] = history["portfolio_id"].fillna(self.portfolio_id)

        sort_dates = pd.to_datetime(
            history["date"],
            errors="coerce",
            dayfirst=True,
        )
        history = (
            history.assign(_sort_date=sort_dates)
            .sort_values(
                by=["_sort_date", "date"],
                kind="stable",
                na_position="last",
            )
            .drop(columns="_sort_date")
            .reset_index(drop=True)
        )

        # Keep the established historical columns first, then any future
        # metadata columns. This makes CSV output deterministic for downstream
        # consumers and keeps the legacy fields intact.
        ordered = [c for c in EOD_HISTORY_COLUMNS if c in history.columns]
        ordered += [c for c in history.columns if c not in ordered]
        history = history[ordered]

        history.to_csv(path, index=False)

    def append_run_manifest(self, row: Mapping[str, Any]) -> None:
        """Append a run manifest, replacing an existing row with the same run_id."""
        self.portfolio_dir.mkdir(parents=True, exist_ok=True)
        path = self.portfolio_dir / self.FILES["runs"]
        new_row = dict(row)
        run_id = str(new_row.get("run_id", "")).strip()
        analysis_type = str(new_row.get("analysis_type", "")).strip()
        if not run_id:
            raise ValueError("Run manifest requires a non-empty 'run_id'.")
        new_row.setdefault("portfolio_id", self.portfolio_id)

        history = pd.read_csv(path) if path.exists() else pd.DataFrame()
        if not history.empty and "run_id" in history.columns:
            # A single end-to-end notebook run can produce both a prospects
            # and portfolio manifest. Treat (run_id, analysis_type) as the
            # natural manifest key so the two records coexist.
            if "analysis_type" in history.columns:
                history = history[
                    ~((history["run_id"].astype(str) == run_id) &
                      (history["analysis_type"].astype(str) == analysis_type))
                ].copy()
            else:
                history = history[history["run_id"].astype(str) != run_id].copy()

        history = pd.concat(
            [history, pd.DataFrame([new_row])],
            ignore_index=True,
            sort=False,
        )

        if "run_datetime" in history.columns:
            history["_sort_datetime"] = pd.to_datetime(
                history["run_datetime"], errors="coerce"
            )
            history = (
                history.sort_values("_sort_datetime", kind="stable")
                .drop(columns="_sort_datetime")
                .reset_index(drop=True)
            )

        history.to_csv(path, index=False)


# Backward-compatible aliases that also make the storage choice explicit.
CSVMarketDataRepository = FileMarketDataRepository
CSVPortfolioRepository = FilePortfolioRepository
