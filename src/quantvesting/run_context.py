from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo
import hashlib
import json
import uuid
from typing import Any

import pandas as pd


IST = ZoneInfo("Asia/Kolkata")
ENGINE_VERSION = "0.5.0"
DATE_FORMAT = "%d-%m-%Y"


def now_ist() -> datetime:
    """Return the current timezone-aware timestamp in India Standard Time."""
    return datetime.now(IST)


def create_run_id(prefix: str = "run") -> str:
    """Create a compact, unique run identifier."""
    timestamp = now_ist().strftime("%Y%m%d_%H%M%S")
    suffix = uuid.uuid4().hex[:8]
    return f"{prefix}_{timestamp}_{suffix}"


def infer_portfolio_id(portfolio_dir) -> str:
    """Infer a portfolio_id from the portfolio directory name."""
    if portfolio_dir is None:
        return "default"

    name = str(portfolio_dir).rstrip("/\\")
    name = name.replace("\\", "/").split("/")[-1]
    return name or "default"


def canonical_date(value) -> str:
    """Return a portfolio-history date in the canonical DD-MM-YYYY format."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""
    text = str(value).strip()
    parsed = pd.NaT
    # Prefer the formats Quantvesting has historically written, then fall
    # back to pandas' scalar parser for other valid date representations.
    for fmt, dayfirst in (("%d-%m-%Y", False), ("%Y-%m-%d", False), ("%d-%b-%y", False)):
        parsed = pd.to_datetime(text, format=fmt, errors="coerce")
        if not pd.isna(parsed):
            break
    if pd.isna(parsed):
        parsed = pd.to_datetime(text, errors="coerce", dayfirst=True)
    if pd.isna(parsed):
        return str(value)
    return parsed.strftime(DATE_FORMAT)


def hash_dataframe(df: pd.DataFrame | None) -> str | None:
    """Create a deterministic SHA-256 fingerprint for a DataFrame."""
    if df is None:
        return None
    frame = df.copy()
    # Column order is part of the data contract; row order is intentionally
    # preserved because it can matter to stable ranking/tie behaviour.
    frame.columns = [str(c) for c in frame.columns]
    payload = pd.util.hash_pandas_object(frame, index=True).values.tobytes()
    metadata = json.dumps(
        {"columns": list(frame.columns), "shape": list(frame.shape)},
        sort_keys=True,
        default=str,
    ).encode("utf-8")
    return hashlib.sha256(metadata + payload).hexdigest()


def hash_config(config: dict | None) -> str | None:
    """Create a deterministic SHA-256 fingerprint for strategy configuration."""
    if config is None:
        return None
    payload = json.dumps(config, sort_keys=True, default=str).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def build_data_fingerprints(market_data: dict, portfolio_data: dict | None = None) -> dict[str, Any]:
    """Build deterministic input fingerprints for reproducible runs."""
    result = {
        "prospects_hash": hash_dataframe(market_data.get("prospects")),
        "screener_hash": hash_dataframe(market_data.get("screener")),
        "momentum_hash": hash_dataframe(market_data.get("momentum")),
    }
    if portfolio_data is not None:
        result.update({
            "portfolio_stocks_hash": hash_dataframe(portfolio_data.get("portfolio_stocks")),
            "investments_hash": hash_dataframe(portfolio_data.get("investments")),
            "portfolio_amounts_hash": _hash_json(portfolio_data.get("portfolio_amounts", {})),
        })
    return result


def _hash_json(value) -> str:
    payload = json.dumps(value or {}, sort_keys=True, default=str).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def build_run_manifest(
    *,
    analysis_type: str,
    run_id: str,
    portfolio_id: str | None,
    strategy_version: str | None,
    config: dict | None,
    market_data: dict,
    portfolio_data: dict | None,
    eod: bool = False,
    status: str = "COMPLETED",
    run_datetime: datetime | None = None,
) -> dict[str, Any]:
    """Build a self-contained manifest describing an analysis execution."""
    timestamp = run_datetime or now_ist()
    manifest = {
        "run_id": run_id,
        "portfolio_id": portfolio_id,
        "analysis_type": analysis_type,
        "run_datetime": timestamp.strftime("%Y-%m-%d %H:%M:%S"),
        "strategy_version": strategy_version,
        "engine_version": ENGINE_VERSION,
        "config_hash": hash_config(config),
        "eod": bool(eod),
        "status": status,
    }
    manifest.update(build_data_fingerprints(market_data, portfolio_data))
    reproducibility_payload = {
        key: manifest.get(key)
        for key in (
            "strategy_version",
            "engine_version",
            "config_hash",
            "prospects_hash",
            "screener_hash",
            "momentum_hash",
            "portfolio_stocks_hash",
            "investments_hash",
            "portfolio_amounts_hash",
        )
    }
    manifest["reproducibility_hash"] = hashlib.sha256(
        json.dumps(reproducibility_payload, sort_keys=True, default=str).encode("utf-8")
    ).hexdigest()
    return manifest
