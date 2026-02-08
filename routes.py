from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
from database import get_db
import models
from backend.services import data_service

router = APIRouter()

# --- Pydantic Schemas ---
class PortfolioItemBase(BaseModel):
    symbol: str
    quantity: float
    avg_price: float

class PortfolioItemCreate(PortfolioItemBase):
    pass

class PortfolioItemResponse(PortfolioItemBase):
    id: int
    current_price: Optional[float] = 0.0
    pnl: Optional[float] = 0.0
    pnl_percent: Optional[float] = 0.0
    market_value: Optional[float] = 0.0
    
    class Config:
        from_attributes = True

class WatchlistItemBase(BaseModel):
    symbol: str
    notes: Optional[str] = None

class WatchlistItemCreate(WatchlistItemBase):
    pass

class WatchlistItemResponse(WatchlistItemBase):
    id: int
    current_price: Optional[float] = 0.0
    
    class Config:
        from_attributes = True

# --- Routes ---

@router.get("/portfolio", response_model=List[PortfolioItemResponse])
def get_portfolio(db: Session = Depends(get_db)):
    items = db.query(models.PortfolioItem).all()
    response_items = []
    
    for item in items:
        # Enrich with real-time data
        current_price = data_service.get_current_price(item.symbol)
        market_value = current_price * item.quantity
        cost_basis = item.avg_price * item.quantity
        pnl = market_value - cost_basis
        pnl_percent = (pnl / cost_basis * 100) if cost_basis > 0 else 0.0
        
        response_items.append(PortfolioItemResponse(
            id=item.id,
            symbol=item.symbol,
            quantity=item.quantity,
            avg_price=item.avg_price,
            current_price=current_price,
            market_value=market_value,
            pnl=pnl,
            pnl_percent=pnl_percent
        ))
    
    return response_items

@router.post("/portfolio", response_model=PortfolioItemResponse)
def add_portfolio_item(item: PortfolioItemCreate, db: Session = Depends(get_db)):
    db_item = models.PortfolioItem(symbol=item.symbol.upper(), quantity=item.quantity, avg_price=item.avg_price)
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    # Return with current price 0 initially to save time, or fetch calls can be done
    return PortfolioItemResponse(
        id=db_item.id,
        symbol=db_item.symbol,
        quantity=db_item.quantity,
        avg_price=db_item.avg_price,
        current_price=0.0
    )

@router.delete("/portfolio/{item_id}")
def delete_portfolio_item(item_id: int, db: Session = Depends(get_db)):
    item = db.query(models.PortfolioItem).filter(models.PortfolioItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    db.delete(item)
    db.commit()
    return {"message": "Item deleted"}

@router.get("/watchlist", response_model=List[WatchlistItemResponse])
def get_watchlist(db: Session = Depends(get_db)):
    items = db.query(models.WatchlistItem).all()
    results = []
    for item in items:
        price = data_service.get_current_price(item.symbol)
        results.append(WatchlistItemResponse(
            id=item.id,
            symbol=item.symbol,
            notes=item.notes,
            current_price=price
        ))
    return results

@router.post("/watchlist", response_model=WatchlistItemResponse)
def add_watchlist_item(item: WatchlistItemCreate, db: Session = Depends(get_db)):
    # Check if exists
    exists = db.query(models.WatchlistItem).filter(models.WatchlistItem.symbol == item.symbol.upper()).first()
    if exists:
        raise HTTPException(status_code=400, detail="Symbol already in watchlist")
    
    db_item = models.WatchlistItem(symbol=item.symbol.upper(), notes=item.notes)
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return WatchlistItemResponse(id=db_item.id, symbol=db_item.symbol, notes=db_item.notes, current_price=0.0)

@router.post("/analyze")
async def analyze_portfolio(request: dict, db: Session = Depends(get_db)):
    """
    Endpoint to analyze portfolio or answer questions.
    Request body: {"query": "Tell me about AAPL"}
    """
    from backend.services import ai_service
    
    user_query = request.get("query", "")
    
    # Gather Portfolio Context
    items = db.query(models.PortfolioItem).all()
    portfolio_context = []
    for item in items:
        current_price = data_service.get_current_price(item.symbol)
        pnl = (current_price - item.avg_price) * item.quantity
        portfolio_context.append({
            "symbol": item.symbol,
            "quantity": item.quantity,
            "avg_price": item.avg_price,
            "current_price": current_price,
            "pnl": pnl
        })
        
    # Get Answer from AI Service
    response = await ai_service.analyze_query(user_query, portfolio_context)
    
    content = response["choices"][0]["message"]["content"]
    return {"message": content}

@router.get("/market/chart/{symbol}")
def get_chart_data(symbol: str, period: str = "1mo"):
    data = data_service.get_historical_data(symbol, period=period)
    return data

@router.get("/technical/{symbol}")
def get_technical_analysis(symbol: str):
    """Get technical analysis for a symbol"""
    return data_service.get_technical_analysis(symbol)

@router.get("/score/{symbol}")
def get_stock_score(symbol: str):
    """Get comprehensive score and recommendation for a symbol"""
    return data_service.get_stock_score(symbol)

@router.get("/macro")
def get_macro_data():
    """Get macro economic data and market regime"""
    from backend.services import macro_service
    return macro_service.get_macro_summary()

@router.post("/export/weekly")
def export_weekly_snapshot(db: Session = Depends(get_db)):
    """Export weekly portfolio snapshot for Perplexity analysis"""
    from backend.services import export_service
    
    # Get portfolio items
    items = db.query(models.PortfolioItem).all()
    portfolio_data = []
    for item in items:
        portfolio_data.append({
            'symbol': item.symbol,
            'quantity': item.quantity,
            'avg_price': item.avg_price
        })
    
    # Get watchlist items
    watchlist = db.query(models.WatchlistItem).all()
    watchlist_data = [{'symbol': w.symbol} for w in watchlist]
    
    # Export
    result = export_service.export_weekly_snapshot(portfolio_data, watchlist_data)
    
    return {
        "success": True,
        "files": result,
        "message": "Weekly snapshot exported successfully"
    }

@router.get("/export/prompt")
def get_analysis_prompt(db: Session = Depends(get_db)):
    """Get pre-written analysis prompt for Perplexity"""
    from backend.services import export_service
    
    items = db.query(models.PortfolioItem).all()
    portfolio_data = []
    for item in items:
        portfolio_data.append({
            'symbol': item.symbol,
            'quantity': item.quantity,
            'avg_price': item.avg_price
        })
    
    prompt = export_service.generate_analysis_prompt(portfolio_data)
    return {"prompt": prompt}

# ============================================================================
# AI AGENTS ENDPOINTS
# ============================================================================

@router.post("/ai/portfolio-analyzer")
async def run_portfolio_analyzer(db: Session = Depends(get_db)):
    """
    Agent 1: Auto-analyze entire portfolio
    Returns BUY/HOLD/SELL recommendations for each holding
    """
    from backend.services import ai_agents
    
    # Get portfolio items
    items = db.query(models.PortfolioItem).all()
    
    if not items:
        return {"error": "No portfolio items to analyze"}
    
    # Build portfolio data with current prices
    portfolio_data = []
    for item in items:
        current_price = data_service.get_current_price(item.symbol)
        market_value = current_price * item.quantity
        cost_basis = item.avg_price * item.quantity
        pnl = market_value - cost_basis
        pnl_percent = (pnl / cost_basis * 100) if cost_basis > 0 else 0
        
        portfolio_data.append({
            'symbol': item.symbol,
            'quantity': item.quantity,
            'avg_price': item.avg_price,
            'current_price': current_price,
            'pnl': pnl,
            'pnl_percent': pnl_percent
        })
    
    # Run analysis
    result = await ai_agents.analyze_portfolio_auto(portfolio_data)
    return result

@router.post("/ai/stock-screener")
async def run_stock_screener(request: dict):
    """
    Agent 2: Analyze a single symbol on-demand
    Returns: Recommendation, Confidence %, Reasoning
    
    Request body: {"symbol": "AAPL"}
    """
    from backend.services import ai_agents
    
    symbol = request.get("symbol", "").upper()
    if not symbol:
        return {"error": "Symbol is required"}
    
    result = await ai_agents.analyze_symbol(symbol)
    return result

@router.post("/ai/query-assistant")
async def run_query_assistant(request: dict, db: Session = Depends(get_db)):
    """
    Agent 3: Free-form query assistant
    Auto-fetches data for mentioned symbols
    
    Request body: {"query": "Should I buy AAPL?"}
    """
    from backend.services import ai_agents
    
    query = request.get("query", "")
    if not query:
        return {"error": "Query is required"}
    
    # Get portfolio context
    items = db.query(models.PortfolioItem).all()
    portfolio_context = []
    
    for item in items:
        current_price = data_service.get_current_price(item.symbol)
        market_value = current_price * item.quantity
        cost_basis = item.avg_price * item.quantity
        pnl = market_value - cost_basis
        
        portfolio_context.append({
            'symbol': item.symbol,
            'quantity': item.quantity,
            'avg_price': item.avg_price,
            'current_price': current_price,
            'pnl': pnl
        })
    
    result = await ai_agents.query_assistant(query, portfolio_context)
    return result

# ============================================================================
# SCHEDULER ENDPOINTS
# ============================================================================

@router.post("/scheduler/start")
async def start_scheduler(db: Session = Depends(get_db)):
    """Start the auto-portfolio analyzer"""
    from backend.services.scheduler import portfolio_scheduler
    from database import SessionLocal
    
    result = await portfolio_scheduler.start(SessionLocal)
    return result

@router.post("/scheduler/stop")
def stop_scheduler():
    """Stop the auto-portfolio analyzer"""
    from backend.services.scheduler import portfolio_scheduler
    return portfolio_scheduler.stop()

@router.post("/scheduler/configure")
def configure_scheduler(request: dict):
    """
    Configure scheduler interval
    Request body: {"interval_minutes": 60}
    """
    from backend.services.scheduler import portfolio_scheduler
    
    interval = request.get("interval_minutes", 60)
    portfolio_scheduler.set_interval(interval)
    return {
        "status": "configured",
        "interval_minutes": portfolio_scheduler.interval_minutes,
        "interval_display": portfolio_scheduler._format_interval()
    }

@router.get("/scheduler/status")
def get_scheduler_status():
    """Get scheduler status"""
    from backend.services.scheduler import portfolio_scheduler
    return portfolio_scheduler.get_status()

@router.get("/scheduler/latest")
def get_latest_analysis():
    """Get the latest auto-analysis result"""
    from backend.services.scheduler import portfolio_scheduler
    
    analysis = portfolio_scheduler.get_latest_analysis()
    if not analysis:
        return {"error": "No analysis available yet"}
    return analysis

@router.post("/scheduler/run-now")
async def run_analysis_now(db: Session = Depends(get_db)):
    """Manually trigger portfolio analysis now"""
    from backend.services.scheduler import portfolio_scheduler
    from database import SessionLocal
    
    result = await portfolio_scheduler.run_now(SessionLocal)
    return result

# ============================================================================
# PER-SYMBOL ANALYSIS ENDPOINTS
# ============================================================================

@router.post("/analysis/symbol/{symbol}")
async def analyze_single_symbol(symbol: str, db: Session = Depends(get_db)):
    """
    Analyze a single symbol and save to database
    Returns: Decision, Confidence, Reasoning
    """
    from backend.services import ai_agents
    from datetime import datetime
    
    # Get current price
    current_price = data_service.get_current_price(symbol)
    
    # Run AI analysis
    result = await ai_agents.analyze_symbol(symbol)
    
    if "error" in result:
        return {"error": result["error"]}
    
    # Save to database
    analysis = models.StockAnalysis(
        symbol=symbol.upper(),
        decision=result.get("recommendation", "HOLD").upper(),
        confidence=result.get("confidence", 50),
        reasoning=result.get("reasoning", ""),
        current_price=current_price
    )
    
    db.add(analysis)
    db.commit()
    db.refresh(analysis)
    
    return {
        "symbol": symbol,
        "decision": analysis.decision,
        "confidence": analysis.confidence,
        "reasoning": analysis.reasoning,
        "current_price": analysis.current_price,
        "analyzed_at": analysis.analyzed_at.isoformat()
    }

@router.get("/analysis/symbol/{symbol}/history")
def get_symbol_analysis_history(symbol: str, limit: int = 20, db: Session = Depends(get_db)):
    """
    Get analysis history for a specific symbol
    Returns last N analyses ordered by most recent first
    """
    analyses = db.query(models.StockAnalysis)\
        .filter(models.StockAnalysis.symbol == symbol.upper())\
        .order_by(models.StockAnalysis.analyzed_at.desc())\
        .limit(limit)\
        .all()
    
    return [{
        "id": a.id,
        "symbol": a.symbol,
        "decision": a.decision,
        "confidence": a.confidence,
        "reasoning": a.reasoning,
        "current_price": a.current_price,
        "analyzed_at": a.analyzed_at.isoformat()
    } for a in analyses]

@router.get("/analysis/portfolio/latest")
def get_latest_analyses_for_portfolio(db: Session = Depends(get_db)):
    """
    Get the latest analysis for each symbol in the portfolio
    """
    from sqlalchemy import func
    
    # Get all portfolio symbols
    portfolio_items = db.query(models.PortfolioItem).all()
    
    results = []
    for item in portfolio_items:
        # Get latest analysis for this symbol
        latest = db.query(models.StockAnalysis)\
            .filter(models.StockAnalysis.symbol == item.symbol)\
            .order_by(models.StockAnalysis.analyzed_at.desc())\
            .first()
        
        if latest:
            results.append({
                "symbol": item.symbol,
                "decision": latest.decision,
                "confidence": latest.confidence,
                "reasoning": latest.reasoning[:200] + "..." if len(latest.reasoning) > 200 else latest.reasoning,
                "current_price": latest.current_price,
                "analyzed_at": latest.analyzed_at.isoformat(),
                "quantity": item.quantity,
                "avg_price": item.avg_price
            })
        else:
            results.append({
                "symbol": item.symbol,
                "decision": None,
                "confidence": None,
                "reasoning": "No analysis yet",
                "current_price": data_service.get_current_price(item.symbol),
                "analyzed_at": None,
                "quantity": item.quantity,
                "avg_price": item.avg_price
            })
    
    return results

@router.post("/analysis/portfolio/run-all")
async def analyze_all_portfolio_symbols(db: Session = Depends(get_db)):
    """
    Analyze all symbols in the portfolio individually
    """
    from backend.services import ai_agents
    
    portfolio_items = db.query(models.PortfolioItem).all()
    
    if not portfolio_items:
        return {"error": "No portfolio items to analyze"}
    
    results = []
    for item in portfolio_items:
        try:
            # Get current price
            current_price = data_service.get_current_price(item.symbol)
            
            # Run AI analysis
            ai_result = await ai_agents.analyze_symbol(item.symbol)
            
            if "error" not in ai_result:
                # Save to database
                analysis = models.StockAnalysis(
                    symbol=item.symbol,
                    decision=ai_result.get("recommendation", "HOLD").upper(),
                    confidence=ai_result.get("confidence", 50),
                    reasoning=ai_result.get("reasoning", ""),
                    current_price=current_price
                )
                
                db.add(analysis)
                db.commit()
                
                results.append({
                    "symbol": item.symbol,
                    "decision": analysis.decision,
                    "confidence": analysis.confidence,
                    "status": "success"
                })
            else:
                results.append({
                    "symbol": item.symbol,
                    "error": ai_result["error"],
                    "status": "failed"
                })
        except Exception as e:
            results.append({
                "symbol": item.symbol,
                "error": str(e),
                "status": "failed"
            })
    
    return {
        "analyzed": len([r for r in results if r.get("status") == "success"]),
        "failed": len([r for r in results if r.get("status") == "failed"]),
        "results": results
    }
