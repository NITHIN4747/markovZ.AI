from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.collectors.price_collector import PriceCollector
from app.engine.technicals import TechnicalAnalyzer
import pandas as pd

router = APIRouter(prefix="/api/v1/market", tags=["market"])
collector = PriceCollector()

@router.get("/state/{symbol}")
async def get_market_state(symbol: str, db: AsyncSession = Depends(get_db)):
    """
    Get the absolute latest live market state for a specific symbol.
    For Phase 1, it hits yfinance directly to guarantee live data.
    """
    try:
        latest_data = await collector.fetch_latest_price(symbol.upper())
        if not latest_data:
            raise HTTPException(status_code=404, detail="Symbol data not found or market closed.")
            
        return {
            "status": "success",
            "data": latest_data
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/technicals/{symbol}")
async def get_market_technicals(symbol: str):
    """
    Fetch historical data and compute live technical indicators (RSI, MACD, SMA).
    """
    try:
        # Fetch 60 days of historical data to get accurate EMAs/SMAs
        import yfinance as yf
        yf_ticker = f"{symbol.upper()}.NS"
        if symbol.upper() == "NIFTY":
            yf_ticker = "^NSEI"
        elif symbol.upper() == "BANKNIFTY":
            yf_ticker = "^NSEBANK"
            
        ticker = yf.Ticker(yf_ticker)
        hist = ticker.history(period="60d", interval="1d")
        
        if hist.empty:
            raise HTTPException(status_code=404, detail="No historical data found.")
            
        # Clean dataframe for engine
        hist = hist.rename(columns={"Open": "open", "High": "high", "Low": "low", "Close": "close", "Volume": "volume"})
        hist.index.name = "time"
        
        # Run through Technical Engine
        analyzer = TechnicalAnalyzer()
        enriched = analyzer.enrich_data(hist)
        
        # Get the absolute latest day's technicals
        latest_technicals = enriched.iloc[-1].to_dict()
        
        # Convert timestamps for JSON serialization
        if pd.api.types.is_datetime64_any_dtype(latest_technicals.get('time')):
             latest_technicals['time'] = latest_technicals['time'].isoformat()
        
        return {
            "status": "success",
            "symbol": symbol.upper(),
            "technicals": {
                "rsi": latest_technicals.get("rsi", 0),
                "macd": latest_technicals.get("macd", 0),
                "macd_signal": latest_technicals.get("macd_signal", 0),
                "sma_20": latest_technicals.get("sma_20", 0),
                "sma_50": latest_technicals.get("sma_50", 0)
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
