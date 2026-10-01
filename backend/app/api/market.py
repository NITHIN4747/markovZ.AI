from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List

from app.database import get_db
from app.collectors.price_collector import PriceCollector

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
