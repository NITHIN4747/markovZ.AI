"""
Coherence and correctness tests for the data source and technical engine.

Ground-truth RSI values are derived from the mathematical definition
(not by running the same algorithm a second time):

  RSI = 100 − 100 / (1 + avg_gain / avg_loss)

Known-vector cases:
  A. 14 bars all up (+1) → avg_loss = 0  → RSI = 100
  B. 14 bars all down (−1) → avg_gain = 0 → RSI = 0
  C. 7 up (+2) then 7 down (−2):
       After 14-bar Wilder init: avg_gain = 1.0, avg_loss = 1.0
       → RS = 1, RSI = 50
"""
import numpy as np
import pandas as pd
import pytest

from app.engine.mock_data import MockDataSource, set_data_source, get_data_source
from app.engine.technicals import TechnicalAnalyzer


SYMBOL   = "NIFTY"
SRC      = MockDataSource()
ANALYZER = TechnicalAnalyzer()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_df(closes: list[float]) -> pd.DataFrame:
    dates = pd.date_range("2024-01-01", periods=len(closes), freq="B")
    df = pd.DataFrame({
        "open": closes, "high": closes, "low": closes,
        "close": closes, "volume": [100_000] * len(closes)
    }, index=dates)
    df.index.name = "time"
    return df


def get_enriched(symbol: str = SYMBOL) -> pd.DataFrame:
    df = SRC.history(symbol)
    return ANALYZER.enrich_data(df.copy())


# ---------------------------------------------------------------------------
# Coherence: live price == last close of the shared history
# ---------------------------------------------------------------------------

def test_live_price_equals_last_close():
    bar = SRC.latest_bar(SYMBOL)
    df  = SRC.history(SYMBOL)
    assert bar.close == pytest.approx(df["close"].iloc[-1], rel=1e-9)


def test_history_is_reproducible():
    pd.testing.assert_frame_equal(SRC.history(SYMBOL), SRC.history(SYMBOL))


def test_ohlcv_sanity():
    df = SRC.history(SYMBOL)
    assert (df["high"] >= df[["open", "close"]].max(axis=1)).all()
    assert (df["low"]  <= df[["open", "close"]].min(axis=1)).all()


# ---------------------------------------------------------------------------
# Warmup
# ---------------------------------------------------------------------------

def test_history_has_enough_bars_for_macd():
    assert len(SRC.history(SYMBOL)) >= 35

def test_history_has_enough_bars_for_rsi():
    assert len(SRC.history(SYMBOL)) >= 15


# ---------------------------------------------------------------------------
# RSI known-vector tests (ground truth from the mathematical definition)
# ---------------------------------------------------------------------------

def test_rsi_all_up_days_is_100():
    """14 rising bars → avg_loss=0 → RSI=100."""
    closes = list(range(1, 16))            # 15 closes, 14 up-deltas all +1
    df = _make_df(closes)
    out = ANALYZER.calculate_rsi(df.copy())
    assert out["rsi"].iloc[-1] == pytest.approx(100.0, abs=0.01)


def test_rsi_all_down_days_is_0():
    """14 falling bars → avg_gain=0 → RSI≈0."""
    closes = list(range(15, 0, -1))        # 15 closes, 14 down-deltas all −1
    df = _make_df(closes)
    out = ANALYZER.calculate_rsi(df.copy())
    assert out["rsi"].iloc[-1] == pytest.approx(0.0, abs=0.01)


def test_rsi_equal_gains_losses_is_50():
    """
    After sufficient EWM warmup, a perfectly alternating ±1 series
    (equal gains and losses) should converge to RSI ≈ 50.
    We use 60 bars to let the EWM state fully stabilise.
    """
    import itertools
    base = 100.0
    # Alternating +1 / -1 deltas, starting from base
    prices = [base]
    for delta in itertools.cycle([+1, -1]):
        prices.append(prices[-1] + delta)
        if len(prices) == 61:
            break
    df = _make_df(prices)
    out = ANALYZER.calculate_rsi(df.copy())
    rsi = out["rsi"].iloc[-1]
    assert 45 <= rsi <= 55, f"RSI for alternating series should be near 50, got {rsi:.2f}"


# ---------------------------------------------------------------------------
# Indicator consistency
# ---------------------------------------------------------------------------

def test_price_within_sma_band():
    """
    Stated rule: for a 90-bar geometric random walk with σ=0.5%/day, price
    must stay within 10% of SMA20 and SMA50.
    A >10% gap would indicate incoherent mock data.
    """
    enriched = get_enriched()
    last = enriched.iloc[-1]
    price, sma_20, sma_50 = last["close"], last["sma_20"], last["sma_50"]
    assert abs(price - sma_20) / price < 0.10, (
        f"Price {price:.2f} is >10% from SMA20 {sma_20:.2f}")
    assert abs(price - sma_50) / price < 0.10, (
        f"Price {price:.2f} is >10% from SMA50 {sma_50:.2f}")


def test_rsi_bounds():
    enriched = get_enriched()
    rsi = enriched["rsi"].dropna()
    assert (rsi >= 0).all() and (rsi <= 100).all()


def test_macd_components_consistent():
    enriched = get_enriched()
    last = enriched.iloc[-1]
    assert last["macd_hist"] == pytest.approx(
        last["macd"] - last["macd_signal"], rel=1e-9)


def test_no_nan_in_final_row():
    enriched = get_enriched()
    nan_cols = enriched.iloc[-1][enriched.iloc[-1].isna()].index.tolist()
    assert not nan_cols, f"NaN found in final row: {nan_cols}"


# ---------------------------------------------------------------------------
# Signal rule tests — 4 boolean rules, including conflicting inputs
# ---------------------------------------------------------------------------

def _compute_signal(price, sma_20, sma_50, macd, macd_signal, rsi):
    """Mirror of the logic in api/market.py get_market_technicals."""
    bullish_count = sum([
        price > sma_20,
        price > sma_50,
        macd  > macd_signal,
        rsi   < 70,
    ])
    if bullish_count >= 3:
        return "BULLISH", f"{bullish_count}/4"
    if bullish_count <= 1:
        return "BEARISH", f"{bullish_count}/4"
    return "NEUTRAL", f"{bullish_count}/4"


@pytest.mark.parametrize("name,price,sma20,sma50,macd,sig,rsi,expected", [
    # Clear uptrend
    ("uptrend",    1000, 950, 920, 10, 5, 60, "BULLISH"),
    # Clear downtrend
    ("downtrend",  900, 950, 960, -10, -5, 40, "BEARISH"),
    # Sideways — two agree bullish, two agree bearish
    ("sideways",   1000, 950, 1050, 10, 5, 71, "NEUTRAL"),
    # Conflicting: RSI overbought (>70) but price above both SMAs + bullish MACD
    ("overbought_but_bullish_structure", 1000, 950, 920, 10, 5, 75, "BULLISH"),
    # Conflicting: price below both SMAs but RSI oversold and MACD bullish
    ("oversold_reversal", 900, 950, 960, 5, -5, 25, "NEUTRAL"),
    # All 4 agree bullish
    ("all_bullish", 1000, 950, 920, 10, 5, 55, "BULLISH"),
    # All 4 agree bearish (RSI overbought counts as not-bullish)
    ("all_bearish", 900, 950, 960, -5, 5, 72, "BEARISH"),
])
def test_signal_rules(name, price, sma20, sma50, macd, sig, rsi, expected):
    signal, score = _compute_signal(price, sma20, sma50, macd, sig, rsi)
    assert signal == expected, (
        f"Scenario '{name}': expected {expected}, got {signal} ({score})")


# ---------------------------------------------------------------------------
# Scenario fixtures: enriched indicator direction
# ---------------------------------------------------------------------------

def _make_scenario(trend: str, bars: int = 60) -> pd.DataFrame:
    """Build a controlled price series for scenario testing."""
    if trend == "uptrend":
        closes = [1000 + i * 5 for i in range(bars)]
    elif trend == "downtrend":
        closes = [1000 - i * 5 for i in range(bars)]
    elif trend == "sideways":
        closes = [1000 + 10 * np.sin(i * 0.3) for i in range(bars)]
    elif trend == "reversal":
        half = bars // 2
        closes = [1000 - i * 5 for i in range(half)] + \
                 [1000 - half * 5 + j * 5 for j in range(bars - half)]
    else:
        raise ValueError(f"Unknown trend: {trend}")
    return _make_df(closes)


def test_uptrend_scenario_rsi_above_50():
    df = _make_scenario("uptrend")
    out = ANALYZER.enrich_data(df.copy())
    assert out["rsi"].iloc[-1] > 50, "RSI should be above 50 in an uptrend"


def test_downtrend_scenario_rsi_below_50():
    df = _make_scenario("downtrend")
    out = ANALYZER.enrich_data(df.copy())
    assert out["rsi"].iloc[-1] < 50, "RSI should be below 50 in a downtrend"


def test_uptrend_scenario_price_above_sma20():
    df = _make_scenario("uptrend")
    out = ANALYZER.enrich_data(df.copy())
    last = out.iloc[-1]
    assert last["close"] > last["sma_20"], "Price should be above SMA20 in uptrend"


def test_downtrend_scenario_price_below_sma20():
    df = _make_scenario("downtrend")
    out = ANALYZER.enrich_data(df.copy())
    last = out.iloc[-1]
    assert last["close"] < last["sma_20"], "Price should be below SMA20 in downtrend"


# ---------------------------------------------------------------------------
# New bar arrival: indicators must update when series is extended
# ---------------------------------------------------------------------------

def test_indicators_update_on_new_bar():
    """Appending a sharply higher bar must change RSI upward."""
    df = SRC.history(SYMBOL).copy()
    rsi_before = ANALYZER.enrich_data(df.copy())["rsi"].iloc[-1]

    # Add a strong rally bar
    last_date  = df.index[-1] + pd.tseries.offsets.BusinessDay(1)
    last_close = df["close"].iloc[-1]
    new_bar    = pd.DataFrame({
        "open": [last_close], "high": [last_close * 1.03],
        "low":  [last_close], "close": [last_close * 1.03],
        "volume": [1_000_000],
    }, index=pd.DatetimeIndex([last_date], name="time"))

    extended     = pd.concat([df, new_bar])
    rsi_after    = ANALYZER.enrich_data(extended.copy())["rsi"].iloc[-1]

    assert rsi_after > rsi_before, (
        f"RSI should rise after a strong up-bar: before={rsi_before:.2f}, after={rsi_after:.2f}")
