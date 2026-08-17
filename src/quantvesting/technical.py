from __future__ import annotations

import datetime
import numpy as np
import pandas as pd
import yfinance as yfin
import ta


def get_date_range(lookback_days=365, end_date_offset_days=1):
    start = datetime.date.today() + datetime.timedelta(days=-lookback_days)
    end = datetime.date.today() + datetime.timedelta(days=end_date_offset_days)
    return start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d")


def fetch_price_history(symbol, period="max"):
    ticker = str(symbol).strip() + ".NS"
    df = yfin.Ticker(ticker).history(period=period, interval="1d")
    if df.empty:
        return df

    # Keep the same columns/semantics as the original code.
    cols = [c for c in ["Open", "Close", "Low", "High", "Volume"] if c in df.columns]
    return df[cols].copy()


def calculate_technical_features(
    stock_symbol,
    start_date,
    end_date,
    sma_short=20,
    sma_mid=50,
    sma_long=200,
    rsi_window=14,
):
    """Reimplementation of the current stock_prec_dev() logic."""
    stock_df = fetch_price_history(stock_symbol)

    if stock_df.empty:
        return pd.DataFrame()

    stock_df["Max"] = round(stock_df["Close"].max(), 2)

    # Original implementation computes Max before filtering.
    stock_df = stock_df[
        (stock_df.index <= end_date) & (stock_df.index >= start_date)
    ].copy()

    if stock_df.empty:
        return pd.DataFrame()

    stock_df[f"{sma_long}_SMA"] = round(
        stock_df["Close"].rolling(window=sma_long, min_periods=1).mean(), 0
    )
    stock_df["Dev%_200"] = round(
        (stock_df["Close"] - stock_df[f"{sma_long}_SMA"])
        * 100
        / stock_df[f"{sma_long}_SMA"],
        2,
    )

    stock_df.dropna(axis=0, inplace=True)

    stock_df[f"{sma_short}_SMA"] = stock_df["Close"].rolling(window=sma_short).mean()
    stock_df[f"{sma_mid}_SMA"] = stock_df["Close"].rolling(window=sma_mid).mean()

    stock_df["Symbol"] = str(stock_symbol).strip()
    stock_df["Close"] = round(stock_df["Close"], 2)
    stock_df["Min"] = round(stock_df["Close"].min(), 2)

    stock_df["RSI_14"] = ta.momentum.RSIIndicator(
        close=stock_df["Close"], window=rsi_window
    ).rsi()
    stock_df["RSI_14"] = round(stock_df["RSI_14"], 0)
    stock_df["Prev_Close"] = stock_df["Close"].shift(1)

    max_sma = max(
        stock_df[f"{sma_short}_SMA"].iloc[-1],
        stock_df[f"{sma_mid}_SMA"].iloc[-1],
        stock_df[f"{sma_long}_SMA"].iloc[-1],
    )
    min_sma = min(
        stock_df[f"{sma_short}_SMA"].iloc[-1],
        stock_df[f"{sma_mid}_SMA"].iloc[-1],
        stock_df[f"{sma_long}_SMA"].iloc[-1],
    )
    abs_spread = max_sma - min_sma

    stock_df["Spread%"] = round(
        (abs_spread / stock_df[f"{sma_long}_SMA"].iloc[-1]) * 100, 2
    )

    return stock_df.tail(1).reset_index()


def get_common_technical_features(symbols, start_date, end_date, config=None):
    """Calculate the latest technical row for every symbol."""
    cfg = (config or {}).get("technical", {})
    rows = []

    for symbol in pd.Series(symbols).dropna().unique():
        try:
            row = calculate_technical_features(
                symbol,
                start_date,
                end_date,
                sma_short=cfg.get("sma_short", 20),
                sma_mid=cfg.get("sma_mid", 50),
                sma_long=cfg.get("sma_long", 200),
                rsi_window=cfg.get("rsi_window", 14),
            )
            if not row.empty:
                rows.append(row)
        except Exception as exc:
            print(f"Technical data error for {symbol}: {exc}")

    if not rows:
        return pd.DataFrame()

    return pd.concat(rows, ignore_index=True)


def get_relative_strength(symbols, period="1mo"):
    """Preserve current 1-month percentage-change percentile logic."""
    changes = {}

    for stock in pd.Series(symbols).dropna().unique():
        try:
            ticker = str(stock).strip() + ".NS"
            stock_data = yfin.Ticker(ticker).history(period=period, interval="1d")

            if len(stock_data) > 0:
                start_price = stock_data["Close"].iloc[0]
                end_price = stock_data["Close"].iloc[-1]
                changes[str(stock).strip()] = round(
                    ((end_price - start_price) / start_price) * 100, 2
                )
            else:
                changes[str(stock).strip()] = np.nan
        except Exception as exc:
            print(f"Relative strength error for {stock}: {exc}")
            changes[str(stock).strip()] = np.nan

    df = pd.DataFrame(
        list(changes.items()), columns=["Symbol", "Percent_Change"]
    ).dropna()

    if df.empty:
        return pd.DataFrame(columns=["Symbol", "RSP"])

    df["RSP"] = round(df["Percent_Change"].rank(pct=True) * 100, 2)
    return df[["Symbol", "RSP"]].sort_values(
        "RSP", ascending=False
    ).reset_index(drop=True)
