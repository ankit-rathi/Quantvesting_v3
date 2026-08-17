from __future__ import annotations

import numpy as np
import pandas as pd


CORE_CONVICTION_COUNT = 6


def _rotation_config(config=None):
    config = config or {}
    rotation = config.get("rotation", {})
    thresholds = rotation.get("thesis_captured", {})
    return {
        "watch": float(thresholds.get("watch", 0.75)),
        "review": float(thresholds.get("review", 0.80)),
        "strong_review": float(thresholds.get("strong_review", 0.90)),
        "target": float(thresholds.get("target", 1.00)),
        "minimum_alternative_upside": float(
            rotation.get("minimum_alternative_upside", 0.20)
        ),
    }


def _ensure_thesis_metrics(df):
    """Add thesis metrics using per-share CMP even when Current is total value."""
    result = df.copy()
    if "ThesisCaptured%" in result.columns:
        return result
    if not {"Current", "AvgCost", "FTT"}.issubset(result.columns):
        return result

    if "Shares" in result.columns:
        current_price = np.where(
            pd.to_numeric(result["Shares"], errors="coerce") > 0,
            pd.to_numeric(result["Current"], errors="coerce")
            / pd.to_numeric(result["Shares"], errors="coerce"),
            np.nan,
        )
    else:
        # Backward-compatible fallback for a stock-level dataframe where
        # Current is already a per-share CMP.
        current_price = pd.to_numeric(result["Current"], errors="coerce")

    denominator = pd.to_numeric(result["FTT"], errors="coerce") - pd.to_numeric(result["AvgCost"], errors="coerce")
    result["ThesisCaptured%"] = np.where(
        denominator > 0,
        (current_price - pd.to_numeric(result["AvgCost"], errors="coerce")) / denominator,
        np.nan,
    )
    result["RemainingUpside%"] = np.where(
        current_price > 0,
        (pd.to_numeric(result["FTT"], errors="coerce") - current_price) / current_price,
        np.nan,
    )
    return result


def add_portfolio_actions(df, config=None):
    """Add transparent portfolio actions without forcing a sale.

    Priority:
      1. EXIT_TARGET when Current >= FTT.
      2. REVIEW_ROTATION when the original thesis is substantially captured.
      3. HOLD otherwise.

    REVIEW_ROTATION is deliberately an alert, not an instruction to sell. A
    true rotation decision requires comparison with an available prospect and
    is handled by ``capital_rotation_actions``.
    """
    cfg = _rotation_config(config)
    result = _ensure_thesis_metrics(df)

    result["Action"] = "HOLD"
    if "PortfolioClass" in result.columns:
        result.loc[
            result["PortfolioClass"].eq("LEGACY"),
            "Action",
        ] = "WAIT_FOR_EXIT_WINDOW"

    if "ThesisCaptured%" in result.columns:
        core_mask = (
            result.get("PortfolioClass", pd.Series("CORE", index=result.index))
            .eq("CORE")
        )
        result.loc[
            core_mask & (result["ThesisCaptured%"] >= cfg["review"]),
            "Action",
        ] = "REVIEW_ROTATION"

    if "Shares" in result.columns:
        current_price = np.where(
            pd.to_numeric(result["Shares"], errors="coerce") > 0,
            pd.to_numeric(result["Current"], errors="coerce")
            / pd.to_numeric(result["Shares"], errors="coerce"),
            np.nan,
        )
    else:
        current_price = pd.to_numeric(result["Current"], errors="coerce")

    result.loc[
        current_price >= pd.to_numeric(result["FTT"], errors="coerce"),
        "Action",
    ] = "EXIT_TARGET"

    return result


def add_prospect_actions(df, top_n=10):
    """Add prospect candidate signals using the final CumlRnk.

    Only rankable/core prospects can become BUY_CANDIDATEs. Legacy rows are
    retained for visibility but remain WATCHLIST and are not promoted by rank.
    """
    result = df.copy()
    result["Action"] = "WATCHLIST"

    rank_col = "CumlRnk" if "CumlRnk" in result.columns else "Cuml_Rank"

    if rank_col in result.columns:
        eligible = result[rank_col].notna()
        top_symbols = (
            result.loc[eligible]
            .sort_values(rank_col)
            .head(top_n)["Symbol"]
            .tolist()
        )
        result.loc[result["Symbol"].isin(top_symbols), "Action"] = "BUY_CANDIDATE"

    return result


def capital_rotation_actions(prospects, portfolio, config=None):
    """Compare mature portfolio positions with the best available prospects.

    This is intentionally advisory. It identifies a possible capital rotation
    rather than issuing an automatic SELL instruction.

    A portfolio position is a rotation candidate when its thesis is at least
    the configured review threshold and a core prospect offers sufficient
    upside. The best prospect is selected by lowest CumlRnk.
    """
    cfg = _rotation_config(config)

    if prospects is None or portfolio is None:
        return pd.DataFrame()

    p = prospects.copy()
    h = portfolio.copy()

    if "CumlRnk" not in p.columns or "Symbol" not in p.columns:
        return pd.DataFrame()

    if "PortfolioClass" in p.columns:
        p = p[p["PortfolioClass"].eq("CORE")].copy()

    p = p[p["CumlRnk"].notna()].copy()
    if p.empty:
        return pd.DataFrame()

    p["FTT%"] = pd.to_numeric(p.get("FTT%"), errors="coerce")
    p = p[p["FTT%"] >= cfg["minimum_alternative_upside"] * 100].copy()
    p = p.sort_values(["CumlRnk", "FTT%"], ascending=[True, False])
    if p.empty:
        return pd.DataFrame()

    best = p.iloc[0]

    h = _ensure_thesis_metrics(h)

    candidates = h[
        h["ThesisCaptured%"].fillna(-np.inf) >= cfg["review"]
    ].copy()

    if candidates.empty:
        return pd.DataFrame(
            columns=[
                "Symbol", "Action", "Reason", "ThesisCaptured%",
                "AlternativeSymbol", "AlternativeCumlRnk",
                "AlternativeFTT%",
            ]
        )

    candidates["Action"] = "REVIEW_ROTATION"
    candidates["Reason"] = "THESIS_SUBSTANTIALLY_CAPTURED"
    candidates["AlternativeSymbol"] = best["Symbol"]
    candidates["AlternativeCumlRnk"] = best["CumlRnk"]
    candidates["AlternativeFTT%"] = best["FTT%"]

    return candidates[
        [
            "Symbol", "Action", "Reason", "ThesisCaptured%",
            "AlternativeSymbol", "AlternativeCumlRnk", "AlternativeFTT%",
        ]
    ].sort_values("ThesisCaptured%", ascending=False).reset_index(drop=True)
