import csv
import json
from datetime import datetime
from backend.services import data_service, macro_service

def export_portfolio_to_csv(portfolio_items, filename=None):
    """Export portfolio with technical analysis to CSV for Perplexity"""
    if not filename:
        filename = f"portfolio_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    
    filepath = f"exports/{filename}"
    
    # Ensure exports directory exists
    import os
    os.makedirs("exports", exist_ok=True)
    
    with open(filepath, 'w', newline='') as csvfile:
        fieldnames = [
            'symbol', 'name', 'quantity', 'avg_price', 'current_price',
            'market_value', 'pnl', 'pnl_percent', 'sector',
            'trend', 'rsi', 'rsi_signal', 'macd_signal',
            'sma_50', 'sma_200', 'score', 'recommendation'
        ]
        
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        
        for item in portfolio_items:
            # Get technical analysis
            tech = data_service.get_technical_analysis(item['symbol'])
            info = data_service.get_stock_info(item['symbol'])
            score_data = data_service.get_stock_score(item['symbol'])
            
            current_price = data_service.get_current_price(item['symbol'])
            market_value = current_price * item['quantity']
            cost_basis = item['avg_price'] * item['quantity']
            pnl = market_value - cost_basis
            pnl_percent = (pnl / cost_basis * 100) if cost_basis > 0 else 0
            
            row = {
                'symbol': item['symbol'],
                'name': info.get('name', item['symbol']),
                'quantity': item['quantity'],
                'avg_price': item['avg_price'],
                'current_price': current_price,
                'market_value': market_value,
                'pnl': pnl,
                'pnl_percent': pnl_percent,
                'sector': info.get('sector', 'N/A'),
                'trend': tech.get('trend', 'N/A') if 'error' not in tech else 'N/A',
                'rsi': tech.get('rsi', 'N/A') if 'error' not in tech else 'N/A',
                'rsi_signal': tech.get('rsi_signal', 'N/A') if 'error' not in tech else 'N/A',
                'macd_signal': tech.get('macd', {}).get('trend', 'N/A') if 'error' not in tech else 'N/A',
                'sma_50': tech.get('sma_50', 'N/A') if 'error' not in tech else 'N/A',
                'sma_200': tech.get('sma_200', 'N/A') if 'error' not in tech else 'N/A',
                'score': score_data.get('score', 0),
                'recommendation': score_data.get('recommendation', 'N/A')
            }
            
            writer.writerow(row)
    
    return filepath

def export_macro_data_to_csv(filename=None):
    """Export macro economic data to CSV"""
    if not filename:
        filename = f"macro_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    
    filepath = f"exports/{filename}"
    
    import os
    os.makedirs("exports", exist_ok=True)
    
    macro = macro_service.get_macro_summary()
    
    with open(filepath, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        
        # Header
        writer.writerow(['Macro Economic Indicators', 'Value', 'Date'])
        writer.writerow([])
        
        # Fed Funds Rate
        writer.writerow(['Federal Funds Rate', 
                        f"{macro['fed_funds_rate']['rate']}%",
                        macro['fed_funds_rate']['date']])
        
        # Treasury Yields
        writer.writerow(['2-Year Treasury Yield', 
                        f"{macro['treasury_yields']['2_year']}%",
                        macro['treasury_yields']['date']])
        writer.writerow(['10-Year Treasury Yield', 
                        f"{macro['treasury_yields']['10_year']}%",
                        macro['treasury_yields']['date']])
        writer.writerow(['30-Year Treasury Yield', 
                        f"{macro['treasury_yields']['30_year']}%",
                        macro['treasury_yields']['date']])
        writer.writerow(['Yield Curve (10Y-2Y Spread)', 
                        f"{macro['treasury_yields']['spread_10y_2y']}%",
                        macro['treasury_yields']['date']])
        
        # Economic Indicators
        writer.writerow([])
        writer.writerow(['CPI (Inflation)', 
                        f"{macro['economic_indicators']['cpi']['value']}%",
                        macro['economic_indicators']['cpi']['date']])
        writer.writerow(['Unemployment Rate', 
                        f"{macro['economic_indicators']['unemployment']['value']}%",
                        macro['economic_indicators']['unemployment']['date']])
        writer.writerow(['GDP Growth', 
                        f"{macro['economic_indicators']['gdp_growth']['value']}%",
                        macro['economic_indicators']['gdp_growth']['date']])
        
        # Market Regime
        writer.writerow([])
        writer.writerow(['Market Regime', 
                        macro['market_regime']['regime'],
                        ''])
        writer.writerow(['Risk Level', 
                        macro['market_regime']['risk_level'],
                        ''])
        writer.writerow(['Recommendation', 
                        macro['market_regime']['recommendation'],
                        ''])
        
        # Next Fed Meeting
        if macro['fed_meetings']['next_meeting']:
            writer.writerow([])
            writer.writerow(['Next FOMC Meeting', 
                            macro['fed_meetings']['next_meeting']['date'],
                            ''])
    
    return filepath

def export_weekly_snapshot(portfolio_items, watchlist_items=None):
    """Export comprehensive weekly snapshot for Perplexity analysis"""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    # Export portfolio
    portfolio_file = export_portfolio_to_csv(portfolio_items, f"portfolio_{timestamp}.csv")
    
    # Export macro data
    macro_file = export_macro_data_to_csv(f"macro_{timestamp}.csv")
    
    # Export watchlist if provided
    watchlist_file = None
    if watchlist_items:
        watchlist_file = export_watchlist_to_csv(watchlist_items, f"watchlist_{timestamp}.csv")
    
    # Create summary JSON
    summary = {
        "export_date": datetime.now().isoformat(),
        "files": {
            "portfolio": portfolio_file,
            "macro": macro_file,
            "watchlist": watchlist_file
        },
        "portfolio_summary": get_portfolio_summary(portfolio_items),
        "macro_summary": macro_service.get_macro_summary(),
        "analysis_prompt": generate_analysis_prompt(portfolio_items)
    }
    
    summary_file = f"exports/weekly_snapshot_{timestamp}.json"
    with open(summary_file, 'w') as f:
        json.dump(summary, f, indent=2)
    
    return {
        "portfolio_csv": portfolio_file,
        "macro_csv": macro_file,
        "watchlist_csv": watchlist_file,
        "summary_json": summary_file
    }

def export_watchlist_to_csv(watchlist_items, filename=None):
    """Export watchlist with scores to CSV"""
    if not filename:
        filename = f"watchlist_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    
    filepath = f"exports/{filename}"
    
    import os
    os.makedirs("exports", exist_ok=True)
    
    with open(filepath, 'w', newline='') as csvfile:
        fieldnames = [
            'symbol', 'name', 'current_price', 'sector',
            'trend', 'rsi', 'rsi_signal', 'score', 'recommendation'
        ]
        
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        
        for item in watchlist_items:
            score_data = data_service.get_stock_score(item['symbol'])
            info = data_service.get_stock_info(item['symbol'])
            tech = score_data.get('technical', {})
            
            row = {
                'symbol': item['symbol'],
                'name': info.get('name', item['symbol']),
                'current_price': data_service.get_current_price(item['symbol']),
                'sector': info.get('sector', 'N/A'),
                'trend': tech.get('trend', 'N/A'),
                'rsi': tech.get('rsi', 'N/A'),
                'rsi_signal': tech.get('rsi_signal', 'N/A'),
                'score': score_data.get('score', 0),
                'recommendation': score_data.get('recommendation', 'N/A')
            }
            
            writer.writerow(row)
    
    return filepath

def get_portfolio_summary(portfolio_items):
    """Get portfolio-level summary statistics"""
    total_value = 0
    total_cost = 0
    sectors = {}
    
    for item in portfolio_items:
        current_price = data_service.get_current_price(item['symbol'])
        market_value = current_price * item['quantity']
        cost_basis = item['avg_price'] * item['quantity']
        
        total_value += market_value
        total_cost += cost_basis
        
        # Sector allocation
        info = data_service.get_stock_info(item['symbol'])
        sector = info.get('sector', 'Unknown')
        sectors[sector] = sectors.get(sector, 0) + market_value
    
    total_pnl = total_value - total_cost
    total_pnl_percent = (total_pnl / total_cost * 100) if total_cost > 0 else 0
    
    # Calculate sector percentages
    sector_allocation = {
        sector: (value / total_value * 100) if total_value > 0 else 0
        for sector, value in sectors.items()
    }
    
    return {
        "total_value": total_value,
        "total_cost": total_cost,
        "total_pnl": total_pnl,
        "total_pnl_percent": total_pnl_percent,
        "num_positions": len(portfolio_items),
        "sector_allocation": sector_allocation
    }

def generate_analysis_prompt(portfolio_items):
    """Generate a pre-written prompt for Perplexity analysis"""
    summary = get_portfolio_summary(portfolio_items)
    macro = macro_service.get_macro_summary()
    
    prompt = f"""I have a portfolio worth ${summary['total_value']:,.2f} with {summary['num_positions']} positions.
Current P/L: ${summary['total_pnl']:,.2f} ({summary['total_pnl_percent']:.2f}%)

Market Conditions:
- Fed Funds Rate: {macro['fed_funds_rate']['rate']}%
- Market Regime: {macro['market_regime']['regime']}
- Risk Level: {macro['market_regime']['risk_level']}

Please analyze my portfolio (see attached CSV) and provide:
1. Top 3 stocks to BUY this week (with reasoning)
2. Top 3 stocks to SELL or reduce (with reasoning)
3. Position sizing recommendations (max 2% risk per trade)
4. Sector rebalancing suggestions
5. Overall portfolio health assessment

Focus on swing trading opportunities (holding period: days to weeks, not day trading).
Consider both technical signals and macro conditions in your analysis.
"""
    
    return prompt
