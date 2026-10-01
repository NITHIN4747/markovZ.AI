import asyncio
from celery import Celery
from app.config import settings
from app.collectors.price_collector import PriceCollector
from app.database import AsyncSessionLocal
from app.models.ohlcv import OHLCV

# Initialize Celery using Redis as the broker
celery_app = Celery(
    "market_worker",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL
)

# Configure Celery to run tasks periodically
celery_app.conf.update(
    beat_schedule={
        "fetch-nifty-prices-every-minute": {
            "task": "app.worker.fetch_and_store_prices",
            "schedule": 60.0, # Run every 60 seconds
        }
    },
    timezone="Asia/Kolkata",
)

collector = PriceCollector()

async def async_fetch_and_store():
    """Async core of the Celery task."""
    symbols = ["NIFTY", "BANKNIFTY", "RELIANCE", "HDFCBANK"]
    
    async with AsyncSessionLocal() as session:
        for symbol in symbols:
            data = await collector.fetch_latest_price(symbol)
            if data:
                # Store in TimescaleDB
                record = OHLCV(
                    time=data["time"],
                    symbol=data["symbol"],
                    open=data["open"],
                    high=data["high"],
                    low=data["low"],
                    close=data["close"],
                    volume=data["volume"]
                )
                session.add(record)
                
        # Commit all new prices at once
        await session.commit()
        print(f"Successfully stored latest prices for {len(symbols)} symbols.")

@celery_app.task
def fetch_and_store_prices():
    """Synchronous Celery wrapper for the async ingestion task."""
    asyncio.run(async_fetch_and_store())
