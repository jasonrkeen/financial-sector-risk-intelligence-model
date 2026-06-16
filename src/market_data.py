"""
Live market data connector for the Financial Sector Risk Intelligence Model.

This module pulls public market data through yfinance and converts it into
market stress, banking stress, and volatility proxy adjustments.

Responsible-use note:
This module is for research, education, and strategic risk analysis.
It does not provide investment advice, trading advice, or financial recommendations.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import yfinance as yf


MARKET_TICKERS = {
    "XLF": "U.S. Financial Select Sector ETF",
    "KBE": "U.S. Bank ETF",
    "KRE": "U.S. Regional Bank ETF",
    "^VIX": "CBOE Volatility Index",
    "DX-Y.NYB": "U.S. Dollar Index Proxy",
}


def fetch_market_history(
    tickers: list[str] | None = None,
    period: str = "1y",
    interval: str = "1d",
) -> pd.DataFrame:
    """Fetch historical market data from yfinance."""

    if tickers is None:
        tickers = list(MARKET_TICKERS.keys())

    data = yf.download(
        tickers=tickers,
        period=period,
        interval=interval,
        group_by="ticker",
        auto_adjust=True,
        progress=False,
        threads=True,
    )

    records = []

    for ticker in tickers:
        try:
            ticker_df = data[ticker].copy()
        except Exception:
            continue

        if ticker_df.empty or "Close" not in ticker_df.columns:
            continue

        ticker_df = ticker_df.reset_index()
        ticker_df["ticker"] = ticker
        ticker_df["description"] = MARKET_TICKERS.get(ticker, ticker)

        records.append(
            ticker_df[
                [
                    "Date",
                    "ticker",
                    "description",
                    "Open",
                    "High",
                    "Low",
                    "Close",
                    "Volume",
                ]
            ]
        )

    if not records:
        return pd.DataFrame()

    history = pd.concat(records, ignore_index=True)
    history = history.rename(
        columns={
            "Date": "date",
            "Open": "open",
            "High": "high",
            "Low": "low",
            "Close": "close",
            "Volume": "volume",
        }
    )

    history["date"] = pd.to_datetime(history["date"]).dt.date

    return history


def calculate_ticker_metrics(history: pd.DataFrame) -> pd.DataFrame:
    """Calculate return, volatility, drawdown, and momentum metrics by ticker."""

    if history.empty:
        return pd.DataFrame()

    metrics = []

    for ticker, group in history.groupby("ticker"):
        group = group.sort_values("date").copy()
        close = pd.to_numeric(group["close"], errors="coerce").dropna()

        if len(close) < 30:
            continue

        returns = close.pct_change().dropna()

        latest_close = float(close.iloc[-1])
        first_close = float(close.iloc[0])
        one_year_return = ((latest_close / first_close) - 1) * 100

        rolling_peak = close.cummax()
        drawdown = ((close / rolling_peak) - 1) * 100
        max_drawdown = float(drawdown.min())

        volatility = float(returns.std() * np.sqrt(252) * 100)

        momentum_20d = np.nan
        if len(close) >= 21:
            momentum_20d = ((close.iloc[-1] / close.iloc[-21]) - 1) * 100

        latest_value = latest_close

        metrics.append(
            {
                "ticker": ticker,
                "description": MARKET_TICKERS.get(ticker, ticker),
                "latest_close": round(latest_value, 2),
                "one_year_return_pct": round(one_year_return, 2),
                "annualized_volatility_pct": round(volatility, 2),
                "max_drawdown_pct": round(max_drawdown, 2),
                "momentum_20d_pct": round(float(momentum_20d), 2)
                if not pd.isna(momentum_20d)
                else np.nan,
                "observations": int(len(close)),
            }
        )

    return pd.DataFrame(metrics)


def _score_higher_is_riskier(
    value: float,
    low: float,
    high: float,
    fallback: float = 50.0,
) -> float:
    """Map a value to a 0-100 risk score where higher values are riskier."""

    if pd.isna(value):
        return fallback

    if high == low:
        return fallback

    score = (value - low) / (high - low) * 100
    return round(float(np.clip(score, 0, 100)), 2)


def _score_lower_is_riskier(
    value: float,
    low: float,
    high: float,
    fallback: float = 50.0,
) -> float:
    """Map a value to a 0-100 risk score where lower values are riskier."""

    if pd.isna(value):
        return fallback

    if high == low:
        return fallback

    score = (high - value) / (high - low) * 100
    return round(float(np.clip(score, 0, 100)), 2)


def build_market_stress_signal(metrics: pd.DataFrame) -> pd.DataFrame:
    """
    Build market stress signals from market metrics.

    Outputs:
    - market_data_stress_signal
    - market_data_banking_signal
    - market_data_volatility_signal
    """

    if metrics.empty:
        return pd.DataFrame(
            [
                {
                    "market_data_stress_signal": 50.0,
                    "market_data_banking_signal": 50.0,
                    "market_data_volatility_signal": 50.0,
                    "market_data_status": "Fallback: no market data",
                }
            ]
        )

    lookup = metrics.set_index("ticker").to_dict(orient="index")

    xlf = lookup.get("XLF", {})
    kbe = lookup.get("KBE", {})
    kre = lookup.get("KRE", {})
    vix = lookup.get("^VIX", {})
    dxy = lookup.get("DX-Y.NYB", {})

    xlf_return_risk = _score_lower_is_riskier(
        xlf.get("one_year_return_pct", np.nan),
        low=-35,
        high=25,
    )
    xlf_drawdown_risk = _score_lower_is_riskier(
        xlf.get("max_drawdown_pct", np.nan),
        low=-35,
        high=0,
    )
    xlf_volatility_risk = _score_higher_is_riskier(
        xlf.get("annualized_volatility_pct", np.nan),
        low=10,
        high=45,
    )

    banking_return_risk_values = [
        _score_lower_is_riskier(kbe.get("one_year_return_pct", np.nan), -40, 25),
        _score_lower_is_riskier(kre.get("one_year_return_pct", np.nan), -45, 25),
    ]

    banking_drawdown_risk_values = [
        _score_lower_is_riskier(kbe.get("max_drawdown_pct", np.nan), -45, 0),
        _score_lower_is_riskier(kre.get("max_drawdown_pct", np.nan), -50, 0),
    ]

    vix_risk = _score_higher_is_riskier(
        vix.get("latest_close", np.nan),
        low=12,
        high=45,
    )

    dollar_pressure = _score_higher_is_riskier(
        dxy.get("one_year_return_pct", np.nan),
        low=-10,
        high=15,
    )

    market_data_stress_signal = round(
        0.35 * xlf_return_risk
        + 0.25 * xlf_drawdown_risk
        + 0.20 * xlf_volatility_risk
        + 0.20 * vix_risk,
        2,
    )

    market_data_banking_signal = round(
        0.45 * float(np.nanmean(banking_return_risk_values))
        + 0.35 * float(np.nanmean(banking_drawdown_risk_values))
        + 0.20 * vix_risk,
        2,
    )

    market_data_volatility_signal = round(
        0.70 * vix_risk + 0.30 * dollar_pressure,
        2,
    )

    return pd.DataFrame(
        [
            {
                "market_data_stress_signal": market_data_stress_signal,
                "market_data_banking_signal": market_data_banking_signal,
                "market_data_volatility_signal": market_data_volatility_signal,
                "market_data_status": "Active",
            }
        ]
    )


def build_market_data_outputs() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Fetch market history and return history, metrics, and stress signal.

    If the public market data pull fails, return empty history/metrics and
    a neutral fallback signal so the full model pipeline can continue.
    """

    try:
        history = fetch_market_history()
        metrics = calculate_ticker_metrics(history)
        signal = build_market_stress_signal(metrics)

        return history, metrics, signal

    except Exception as exc:
        fallback_signal = pd.DataFrame(
            [
                {
                    "market_data_stress_signal": 50.0,
                    "market_data_banking_signal": 50.0,
                    "market_data_volatility_signal": 50.0,
                    "market_data_status": f"Fallback: {exc}",
                }
            ]
        )

        return pd.DataFrame(), pd.DataFrame(), fallback_signal


def apply_market_data_layer(df: pd.DataFrame, signal: pd.DataFrame) -> pd.DataFrame:
    """
    Apply market stress signal to the model input dataset.

    This applies a broad global market-context adjustment. It is intentionally
    conservative because the current market connector uses global/U.S. proxies.
    """

    adjusted = df.copy()

    if signal.empty:
        market_signal = 50.0
        banking_signal = 50.0
        volatility_signal = 50.0
        market_status = "Fallback: no market signal"
    else:
        row = signal.iloc[0]
        market_signal = float(row.get("market_data_stress_signal", 50.0))
        banking_signal = float(row.get("market_data_banking_signal", 50.0))
        volatility_signal = float(row.get("market_data_volatility_signal", 50.0))
        market_status = str(row.get("market_data_status", "Active"))

    adjusted["market_data_stress_signal"] = market_signal
    adjusted["market_data_banking_signal"] = banking_signal
    adjusted["market_data_volatility_signal"] = volatility_signal
    adjusted["market_data_status"] = market_status

    adjusted["market_stress_proxy"] = (
        0.75 * adjusted["market_stress_proxy"]
        + 0.25 * market_signal
    ).clip(0, 100).round(2)

    adjusted["banking_stress_proxy"] = (
        0.75 * adjusted["banking_stress_proxy"]
        + 0.25 * banking_signal
    ).clip(0, 100).round(2)

    adjusted["cyber_operational_pressure"] = (
        0.85 * adjusted["cyber_operational_pressure"]
        + 0.15 * volatility_signal
    ).clip(0, 100).round(2)

    return adjusted