from sqlalchemy import Column, String, Float, BigInteger, DateTime
from app.database import Base

class OHLCV(Base):
    __tablename__ = "ohlcv"
    
    # In TimescaleDB, the primary key is typically a composite of time + symbol
    time = Column(DateTime(timezone=True), primary_key=True)
    symbol = Column(String(20), primary_key=True)
    
    open = Column(Float)
    high = Column(Float)
    low = Column(Float)
    close = Column(Float)
    volume = Column(BigInteger)
    vwap = Column(Float, nullable=True)
