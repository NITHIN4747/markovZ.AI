"""
Tests for data coherence and indicator correctness.

Rules:
- live_price  == history()['close'].iloc[-1]
- RSI(14) is valid only after ≥15 bars of warmup
- MACD signal is valid only after ≥35 bars of warmup
- Indicator values match reference figures computed inline
"""
import numpy as np
import pandas as pd
import pytest

from app.engine.mock_data import MockDataSource
from app.engine.technicals import TechnicalAnalyzer


SYMBOL = "NIFTY"
SRC = MockDataSource()
ANALYZER = TechnicalAnalyzer()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def get_enriched(symbol: str = SYMBOL) -> pd.DataFrame:
    df = SRC.history(symbol)
    return ANALYZER.enrich_data(df.copy())


# ---------------------------------------------------------------------------
# Coherence: live price == last close of the shared history
# ---------------------------------------------------------------------------

def test_live_price_equals_last_close():
    """The number shown on the dashboard must come from the same series."""
    bar = SRC.latest_bar(SYMBOL)
    df  = SRC.history(SYMBOL)
    assert bar.close == pytest.approx(df["close"].iloc[-1], rel=1e-9)


def test_history_is_reproducible():
    """Same seed → same data every call."""
    df1 = SRC.history(SYMBOL)
    df2 = SRC.history(SYMBOL)
    pd.testing.assert_frame_equal(df1, df2)


def test_ohlcv_sanity():
    """high ≥ max(open,close) ≥ min(open,close) ≥ low for every bar."""
    df = SRC.history(SYMBOL)
    assert (df["high"] >= df[["open", "close"]].max(axis=1)).all()
    assert (df["low"]  <= df[["open", "close"]].min(axis=1)).all()


# ---------------------------------------------------------------------------
# Warmup: enough bars for valid indicators
# ---------------------------------------------------------------------------

def test_history_has_enough_bars_for_macd():
    """MACD signal line needs 26 (slow EMA) + 9 (signal EMA) = 35 bars."""
    df = SRC.history(SYMBOL)
    assert len(df) >= 35, f"Only {len(df)} bars — MACD signal will be NaN"


def test_history_has_enough_bars_for_rsi():
    """RSI(14) needs at least 15 bars."""
    df = SRC.history(SYMBOL)
    assert len(df) >= 15, f"Only {len(df)} bars — RSI will be NaN"


# ---------------------------------------------------------------------------
# Indicator consistency: price and indicators live in the same world
# ---------------------------------------------------------------------------

def test_price_within_sma_band():
    """
    Price should not be more than 20% away from SMA20 or SMA50.
    A >20% gap would signal the mock data is incoherent.
    """
    enriched = get_enriched()
    last = enriched.iloc[-1]
    price  = last["close"]
    sma_20 = last["sma_20"]
    sma_50 = last["sma_50"]

    assert abs(price - sma_20) / price < 0.20, (
        f"Price {price:.2f} is >20% from SMA20 {sma_20:.2f}"
    )
    assert abs(price - sma_50) / price < 0.20, (
        f"Price {price:.2f} is >20% from SMA50 {sma_50:.2f}"
    )


def test_rsi_bounds():
    """RSI must be in [0, 100]."""
    enriched = get_enriched()
    rsi = enriched["rsi"].dropna()
    assert (rsi >= 0).all() and (rsi <= 100).all(), "RSI out of [0,100] bounds"


def test_rsi_reference_value():
    """
    RSI computed by TechnicalAnalyzer must match a reference
    implementation computed inline (Wilder smoothing via ewm).
    """
    df = SRC.history(SYMBOL).copy()
    delta = df["close"].diff()
    gain  = delta.clip(lower=0)
    loss  = (-delta).clip(lower=0)

    alpha = 1 / 14
    avg_gain = gain.ewm(alpha=alpha, min_periods=14, adjust=False).mean()
    avg_loss = loss.ewm(alpha=alpha, min_periods=14, adjust=False).mean()
    rs  = avg_gain / avg_loss.replace(0, np.nan)
    ref = (100 - 100 / (1 + rs)).iloc[-1]

    enriched = ANALYZER.enrich_data(df)
    calc = enriched["rsi"].iloc[-1]

    assert calc == pytest.approx(ref, abs=1.0), (
        f"RSI mismatch: engine={calc:.4f}, reference={ref:.4f}"
    )


def test_macd_components_consistent():
    """MACD histogram must equal MACD line minus signal line."""
    enriched = get_enriched()
    last = enriched.iloc[-1]
    hist  = last["macd_hist"]
    diff  = last["macd"] - last["macd_signal"]
    assert hist == pytest.approx(diff, rel=1e-9)


def test_no_nan_in_final_row():
    """Enriched DataFrame must have no NaN in the last row after fillna."""
    enriched = get_enriched()
    last_row = enriched.iloc[-1]
    nan_cols  = last_row[last_row.isna()].index.tolist()
    assert not nan_cols, f"NaN found in last row: {nan_cols}"
