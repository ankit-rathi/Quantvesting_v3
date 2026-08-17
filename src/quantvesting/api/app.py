from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import pandas as pd
from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from .. import (
    PORTFOLIO_DISPLAY_COLUMNS,
    PROSPECT_DISPLAY_COLUMNS,
    Quantvesting,
    create_run_id,
    load_config,
    load_market_data,
    load_portfolio_data,
)


ROOT = Path(__file__).resolve().parents[3]
CONFIG_PATH = Path(os.getenv("QV_CONFIG_PATH", ROOT / "config" / "strategy.yaml"))
MARKET_DATA_DIR = Path(os.getenv("QV_MARKET_DATA_DIR", ROOT / "market_data"))
PORTFOLIO_DATA_ROOT = Path(os.getenv("QV_PORTFOLIO_DATA_ROOT", ROOT / "portfolio_data"))
WEB_DIR = ROOT / "web"
ACCESS_KEY = os.getenv("QV_ACCESS_KEY", "").strip()
DEFAULT_PORTFOLIO_ID = os.getenv("QV_PORTFOLIO_ID", "ankit").strip() or "ankit"


def _safe_id(value: str) -> str:
    value = str(value).strip()
    if not value or value in {".", ".."} or "/" in value or "\\" in value:
        raise HTTPException(status_code=400, detail="Invalid portfolio_id")
    return value


def _portfolio_dir(portfolio_id: str) -> Path:
    portfolio_id = _safe_id(portfolio_id)
    path = (PORTFOLIO_DATA_ROOT / portfolio_id).resolve()
    root = PORTFOLIO_DATA_ROOT.resolve()
    if root not in path.parents:
        raise HTTPException(status_code=400, detail="Invalid portfolio_id")
    if not path.is_dir():
        raise HTTPException(status_code=404, detail=f"Portfolio '{portfolio_id}' not found")
    return path


def _json_value(value: Any):
    if value is None:
        return None
    if isinstance(value, dict):
        return {str(k): _json_value(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_value(v) for v in value]
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    if hasattr(value, "item"):
        try:
            return value.item()
        except Exception:
            pass
    return value


def _records(df: pd.DataFrame, columns: list[str] | None = None) -> list[dict[str, Any]]:
    frame = df.copy()
    if columns:
        frame = frame[[c for c in columns if c in frame.columns]]
    frame = frame.replace({float("inf"): None, float("-inf"): None})
    return [
        {str(k): _json_value(v) for k, v in row.items()}
        for row in frame.to_dict(orient="records")
    ]


def _available_portfolios() -> list[str]:
    if not PORTFOLIO_DATA_ROOT.exists():
        return []
    return sorted(p.name for p in PORTFOLIO_DATA_ROOT.iterdir() if p.is_dir() and not p.name.startswith("."))


class RunRequest(BaseModel):
    portfolio_id: str = Field(default=DEFAULT_PORTFOLIO_ID)
    refresh_screener: bool = False
    eod: bool = False


class RunStore:
    """Small in-process run cache for the CSV-backed beta.

    Persistence of official run/EOD history remains the repository's job. This
    cache only prevents the web UI from recalculating the same run for every
    tab. PostgreSQL will later replace the repository without changing API
    contracts.
    """

    def __init__(self):
        self._runs: dict[str, dict[str, Any]] = {}

    def put(self, run_id: str, payload: dict[str, Any]) -> None:
        self._runs[run_id] = payload

    def get(self, run_id: str) -> dict[str, Any] | None:
        return self._runs.get(run_id)


store = RunStore()
app = FastAPI(
    title="Quantvesting API",
    version="0.1.0-beta",
    description="Web/API adapter over the existing Quantvesting engine and CSV repositories.",
)

# The beta UI is served by the same FastAPI process, so CORS is only needed for
# future external clients. Keep it configurable rather than embedding origins.
origins = [x.strip() for x in os.getenv("QV_CORS_ORIGINS", "*").split(",") if x.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


def require_access_key(x_qv_access_key: str | None = Header(default=None)):
    if ACCESS_KEY and x_qv_access_key != ACCESS_KEY:
        raise HTTPException(status_code=401, detail="Invalid or missing Quantvesting access key")


def _new_run(req: RunRequest) -> dict[str, Any]:
    portfolio_id = _safe_id(req.portfolio_id)
    portfolio_dir = _portfolio_dir(portfolio_id)
    config = load_config(CONFIG_PATH)
    qv = Quantvesting(config)

    if req.refresh_screener:
        qv.ingest_screener(MARKET_DATA_DIR)

    market_data = load_market_data(MARKET_DATA_DIR)
    portfolio_data = load_portfolio_data(portfolio_dir, portfolio_id=portfolio_id)
    run_id = create_run_id()

    prospects = qv.prospects(
        market_data,
        portfolio_data=portfolio_data,
        include_portfolio=True,
        portfolio_id=portfolio_id,
        run_id=run_id,
    )
    portfolio, summary = qv.portfolio(
        market_data,
        portfolio_data=portfolio_data,
        eod=req.eod,
        portfolio_id=portfolio_id,
        run_id=run_id,
    )
    prospect_actions = qv.prospect_actions(prospects, top_n=10)
    portfolio_actions = qv.portfolio_actions(portfolio)
    rotation = qv.capital_rotation(prospects, portfolio)

    validation = summary.get("validation", {}) if isinstance(summary, dict) else {}
    payload = {
        "run_id": run_id,
        "portfolio_id": portfolio_id,
        "strategy_version": config.get("strategy", {}).get("version"),
        "engine_version": getattr(__import__("quantvesting", fromlist=["ENGINE_VERSION"]), "ENGINE_VERSION", None),
        "eod": req.eod,
        "refresh_screener": req.refresh_screener,
        "summary": _json_value(summary),
        "validation": _json_value(validation),
        "prospects": _records(prospects, PROSPECT_DISPLAY_COLUMNS),
        "portfolio": _records(portfolio, PORTFOLIO_DISPLAY_COLUMNS),
        "prospect_actions": _records(prospect_actions, PROSPECT_DISPLAY_COLUMNS + ["Action"]),
        "portfolio_actions": _records(portfolio_actions, PORTFOLIO_DISPLAY_COLUMNS + ["Action", "ThesisCaptured%", "RemainingUpside%", "RotationStatus"]),
        "rotation": _records(rotation),
    }
    store.put(run_id, payload)
    return payload


@app.get("/health", tags=["system"])
def health():
    return {"status": "ok", "service": "quantvesting", "version": app.version}


@app.get("/api/v1/portfolios", dependencies=[Depends(require_access_key)], tags=["portfolio"])
def portfolios():
    return {"portfolios": _available_portfolios(), "default": DEFAULT_PORTFOLIO_ID}


@app.post("/api/v1/runs", dependencies=[Depends(require_access_key)], tags=["runs"])
def create_analysis_run(request: RunRequest):
    try:
        return _new_run(request)
    except HTTPException:
        raise
    except Exception as exc:
        # Keep the actual engine exception available in server logs while
        # returning a useful client-level error.
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/api/v1/runs/{run_id}", dependencies=[Depends(require_access_key)], tags=["runs"])
def get_run(run_id: str):
    payload = store.get(run_id)
    if payload is None:
        raise HTTPException(status_code=404, detail="Run is not available in this server session; start a new run.")
    return payload


@app.get("/api/v1/runs/{run_id}/summary", dependencies=[Depends(require_access_key)], tags=["runs"])
def get_summary(run_id: str):
    return _subresource(run_id, "summary")


@app.get("/api/v1/runs/{run_id}/prospects", dependencies=[Depends(require_access_key)], tags=["prospects"])
def get_prospects(run_id: str):
    return _subresource(run_id, "prospects")


@app.get("/api/v1/runs/{run_id}/portfolio", dependencies=[Depends(require_access_key)], tags=["portfolio"])
def get_portfolio(run_id: str):
    return _subresource(run_id, "portfolio")


@app.get("/api/v1/runs/{run_id}/decisions", dependencies=[Depends(require_access_key)], tags=["decisions"])
def get_decisions(run_id: str):
    payload = store.get(run_id)
    if payload is None:
        raise HTTPException(status_code=404, detail="Run not found")
    return {
        "prospect_actions": payload["prospect_actions"],
        "portfolio_actions": payload["portfolio_actions"],
        "rotation": payload["rotation"],
    }


def _subresource(run_id: str, key: str):
    payload = store.get(run_id)
    if payload is None:
        raise HTTPException(status_code=404, detail="Run not found")
    return payload[key]


@app.get("/", include_in_schema=False)
def web_root():
    index = WEB_DIR / "index.html"
    if not index.exists():
        raise HTTPException(status_code=404, detail="Web UI not installed")
    return FileResponse(index)


@app.get("/app.js", include_in_schema=False)
def web_js():
    return FileResponse(WEB_DIR / "app.js", media_type="application/javascript")


@app.get("/styles.css", include_in_schema=False)
def web_css():
    return FileResponse(WEB_DIR / "styles.css", media_type="text/css")
