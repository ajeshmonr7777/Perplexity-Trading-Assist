import asyncio
from datetime import datetime, timedelta
from typing import Optional
import json
import os

class PortfolioAnalyzerScheduler:
    """
    Scheduler for auto-running portfolio analysis
    User can configure the interval (1 hour, 4 hours, daily, etc.)
    """
    
    def __init__(self):
        self.is_running = False
        self.interval_minutes = 60  # Default: 1 hour
        self.last_run = None
        self.next_run = None
        self.task = None
        self.latest_analysis = None
        
    def set_interval(self, minutes: int):
        """Set analysis interval in minutes"""
        if minutes < 15:  # Minimum 15 minutes
            minutes = 15
        if minutes > 1440:  # Maximum 24 hours
            minutes = 1440
        self.interval_minutes = minutes
        
    def get_status(self) -> dict:
        """Get scheduler status"""
        return {
            "is_running": self.is_running,
            "interval_minutes": self.interval_minutes,
            "interval_display": self._format_interval(),
            "last_run": self.last_run.isoformat() if self.last_run else None,
            "next_run": self.next_run.isoformat() if self.next_run else None,
            "has_latest_analysis": self.latest_analysis is not None
        }
    
    def _format_interval(self) -> str:
        """Format interval for display"""
        if self.interval_minutes < 60:
            return f"{self.interval_minutes} minutes"
        elif self.interval_minutes == 60:
            return "1 hour"
        elif self.interval_minutes < 1440:
            hours = self.interval_minutes // 60
            return f"{hours} hours"
        else:
            return "24 hours (daily)"
    
    async def start(self, db_session_factory):
        """Start the scheduler"""
        if self.is_running:
            return {"status": "already_running"}
        
        self.is_running = True
        self.task = asyncio.create_task(self._run_loop(db_session_factory))
        return {"status": "started", "interval": self._format_interval()}
    
    def stop(self):
        """Stop the scheduler"""
        if not self.is_running:
            return {"status": "not_running"}
        
        self.is_running = False
        if self.task:
            self.task.cancel()
        return {"status": "stopped"}
    
    async def _run_loop(self, db_session_factory):
        """Main scheduler loop"""
        from backend.services import ai_agents, data_service
        from models import PortfolioItem
        
        while self.is_running:
            try:
                # Calculate next run time
                self.next_run = datetime.now() + timedelta(minutes=self.interval_minutes)
                
                # Get portfolio items
                db = db_session_factory()
                items = db.query(PortfolioItem).all()
                
                if items:
                    # Build portfolio data
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
                    self.latest_analysis = result
                    self.last_run = datetime.now()
                    
                    # Save to file
                    self._save_analysis(result)
                
                db.close()
                
                # Wait for next interval
                await asyncio.sleep(self.interval_minutes * 60)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"Error in portfolio analyzer scheduler: {e}")
                await asyncio.sleep(60)  # Wait 1 minute before retry
    
    def _save_analysis(self, result: dict):
        """Save analysis to file"""
        os.makedirs("analysis_history", exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"analysis_history/portfolio_analysis_{timestamp}.json"
        
        with open(filename, 'w') as f:
            json.dump(result, f, indent=2)
    
    def get_latest_analysis(self) -> Optional[dict]:
        """Get the latest analysis result"""
        return self.latest_analysis
    
    async def run_now(self, db_session_factory):
        """Manually trigger analysis now"""
        from backend.services import ai_agents, data_service
        from models import PortfolioItem
        
        db = db_session_factory()
        items = db.query(PortfolioItem).all()
        
        if not items:
            db.close()
            return {"error": "No portfolio items to analyze"}
        
        # Build portfolio data
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
        self.latest_analysis = result
        self.last_run = datetime.now()
        
        # Save to file
        self._save_analysis(result)
        
        db.close()
        return result


# Global scheduler instance
portfolio_scheduler = PortfolioAnalyzerScheduler()
