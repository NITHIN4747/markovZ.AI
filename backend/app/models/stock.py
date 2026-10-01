from sqlalchemy import Column, String, Boolean, DateTime, ARRAY
from sqlalchemy.sql import func
from app.database import Base

class Stock(Base):
    __tablename__ = "stocks"

    symbol = Column(String(20), primary_key=True, index=True)
    name = Column(String(255))
    sector = Column(String(100))
    industry = Column(String(100))
    market_cap_category = Column(String(20)) # LARGECAP/MIDCAP/SMALLCAP
    index_membership = Column(ARRAY(String)) # ['NIFTY50', 'NIFTY500']
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
