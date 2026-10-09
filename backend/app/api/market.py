from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.engine.mock_data import get_data_source
from app.engine.technicals import TechnicalAnalyzer
import pandas as pd

router = APIRouter(prefix="/api/v1/market", tags=["market"])
analyzer = TechnicalAnalyzer()


@router.get("/state/{symbol}")
async def get_market_state(symbol: str, db: AsyncSession = Depends(get_db)):
    """
    Get the latest live market bar for a symbol.
    The close price is the last bar of the shared DataSource,
    so it is guaranteed to match the technicals endpoint.
    """
    try:
        bar = get_data_source().latest_bar(symbol.upper())
        return {
            "status": "success",
            "data": {
                "symbol": bar.symbol if hasattr(bar, "symbol") else symbol.upper(),
                "time":   bar.time.isoformat(),
                "open":   bar.open,
                "high":   bar.high,
                "low":    bar.low,
                "close":  bar.close,
                "volume": bar.volume,
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/technicals/{symbol}")
async def get_market_technicals(symbol: str):
    """
    Compute RSI, MACD and SMAs from the same DataSource as /state.
    All numbers are internally consistent.
    """
    try:
        hist = get_data_source().history(symbol.upper())

        if len(hist) < 35:
            raise HTTPException(
                status_code=422,
                detail=f"Only {len(hist)} bars — need ≥35 for valid MACD signal."
            )

        enriched = analyzer.enrich_data(hist.copy())
        last     = enriched.iloc[-1]

        # Compute code-side signal: how many indicators agree?
        price  = last["close"]
        sma_20 = last["sma_20"]
        sma_50 = last["sma_50"]
        rsi    = last["rsi"]
        macd   = last["macd"]
        macd_s = last["macd_signal"]

        bullish_count = sum([
            price > sma_20,
            price > sma_50,
            macd  > macd_s,
            rsi   < 70,          # not overbought
        ])
        signal = "BULLISH" if bullish_count >= 3 else ("BEARISH" if bullish_count <= 1 else "NEUTRAL")

        return {
            "status":  "success",
            "symbol":  symbol.upper(),
            "signal":  signal,                       # code-computed, not LLM
            "agreement_score": f"{bullish_count}/4", # how many indicators agree
            "technicals": {
                "rsi":         round(float(rsi),    2),
                "macd":        round(float(macd),   2),
                "macd_signal": round(float(macd_s), 2),
                "sma_20":      round(float(sma_20), 2),
                "sma_50":      round(float(sma_50), 2),
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
