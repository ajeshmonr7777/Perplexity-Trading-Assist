from sqlalchemy import Column, Integer, String, Float, DateTime, Text
from sqlalchemy.sql import func
from database import Base

class PortfolioItem(Base):
    __tablename__ = "portfolio"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, index=True)
    quantity = Column(Float)
    avg_price = Column(Float)
    side = Column(String, default="BUY")  # BUY or SELL
    added_at = Column(DateTime(timezone=True), server_default=func.now())

class WatchlistItem(Base):
    __tablename__ = "watchlist"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, index=True, unique=True)
    notes = Column(String, nullable=True)
    added_at = Column(DateTime(timezone=True), server_default=func.now())

class StockAnalysis(Base):
    __tablename__ = "stock_analysis"
    
    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, index=True)
    decision = Column(String)  # BUY, HOLD, SELL
    confidence = Column(Integer)  # 0-100
    reasoning = Column(Text)  # Full AI reasoning
    current_price = Column(Float)
    analyzed_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # NEW: Fields for full transparency
    full_prompt = Column(Text, nullable=True)  # Complete prompt sent to AI
    raw_response = Column(Text, nullable=True)  # Full AI response
    model_used = Column(String(50), nullable=True)  # e.g., "sonar-pro"
    temperature = Column(Float, nullable=True)  # Model temperature setting

