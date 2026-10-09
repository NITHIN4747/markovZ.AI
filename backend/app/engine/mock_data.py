"""
Coherent mock data source with a seeded RNG.

All endpoints (live price, technicals, LLM context) draw from
this single source so the numbers are internally consistent.

Put the real NSE/yfinance adapter behind the same DataSource
interface later — indicator and LLM code never need to change.
"""
from __future__ import annotations

import abc
from dataclasses import dataclass

import numpy as np
import pandas as pd


# ---------------------------------------------------------------------------
# Interface — swap mock for real by subclassing DataSource
# ---------------------------------------------------------------------------

@dataclass
class OHLCVBar:
    time: pd.Timestamp
    open: float
    high: float
    low: float
    close: float
    volume: int


class DataSource(abc.ABC):
    @abc.abstractmethod
    def history(self, symbol: str, bars: int = 90) -> pd.DataFrame:
        """Return a DataFrame with columns [open, high, low, close, volume]
        and a DatetimeIndex named 'time', newest row last.
        At least `bars` rows must be returned (90 gives enough MACD warmup).
        """

    @abc.abstractmethod
    def latest_bar(self, symbol: str) -> OHLCVBar:
        """Return the newest bar.  close == history()['close'].iloc[-1]."""


# ---------------------------------------------------------------------------
# Seeded mock implementation
# ---------------------------------------------------------------------------

_BASE_PRICES: dict[str, float] = {
    "NIFTY":     22500.0,
    "BANKNIFTY": 48000.0,
    "RELIANCE":  2900.0,
    "HDFCBANK":  1450.0,
}
_SEED = 42          # fixed seed → reproducible numbers across restarts
_BARS = 90          # enough warmup: RSI-14 needs 15, MACD-signal needs 35


class MockDataSource(DataSource):
    """
    Deterministic synthetic OHLCV.

    The random series is seeded per-symbol so symbols are uncorrelated,
    but each symbol always produces the same series.
    """

    def history(self, symbol: str, bars: int = _BARS) -> pd.DataFrame:
        rng = np.random.default_rng(seed=_SEED + hash(symbol) % 1000)
        base = _BASE_PRICES.get(symbol.upper(), 1000.0)
        vol_frac = 0.005                   # 0.5% daily σ

        # Geometric random walk so price can't go negative
        log_returns = rng.normal(0, vol_frac, bars)
        closes = base * np.exp(np.cumsum(log_returns))

        daily_range = closes * vol_frac
        opens  = closes - rng.uniform(-0.5, 0.5, bars) * daily_range
        highs  = np.maximum(opens, closes) + rng.uniform(0, 0.5, bars) * daily_range
        lows   = np.minimum(opens, closes) - rng.uniform(0, 0.5, bars) * daily_range
        vols   = rng.integers(100_000, 5_000_000, bars)

        dates = pd.date_range(end=pd.Timestamp.now().floor("D"), periods=bars, freq="B")

        df = pd.DataFrame(
            {"open": opens, "high": highs, "low": lows, "close": closes, "volume": vols},
            index=dates,
        )
        df.index.name = "time"
        return df

    def latest_bar(self, symbol: str) -> OHLCVBar:
        df = self.history(symbol)
        row = df.iloc[-1]
        return OHLCVBar(
            time=row.name,
            open=float(row["open"]),
            high=float(row["high"]),
            low=float(row["low"]),
            close=float(row["close"]),
            volume=int(row["volume"]),
        )


# ---------------------------------------------------------------------------
# Singleton — import this everywhere
# ---------------------------------------------------------------------------

_data_source: DataSource = MockDataSource()


def get_data_source() -> DataSource:
    """Return the active DataSource.  Replace with a real adapter in prod."""
    return _data_source


def set_data_source(source: DataSource) -> None:
    """Override for testing or when switching to real market data."""
    global _data_source
    _data_source = source
