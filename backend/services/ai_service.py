import httpx
import json
import os

# Load API Key from environment
PERPLEXITY_API_KEY = os.getenv("PERPLEXITY_API_KEY", "")

SYSTEM_PROMPT = """
You are a professional swing trader and financial analyst specializing in position-style trading.
Your goal is to help the user manage their portfolio and identify trading opportunities.

Trading Philosophy:
- Focus on swing trades (holding period: days to weeks, not day trading)
- Max 1-2 trades per week to avoid overtrading
- Position size: 1-2% portfolio risk per trade
- Always consider macro conditions before recommending trades

When analyzing, consider:
1. **Technical Analysis**: Trend, RSI, MACD, Moving Averages, Support/Resistance
2. **Macro Economic Factors**: Fed policy, interest rates, yield curve, inflation
3. **Risk Management**: Position sizing, stop losses, sector diversification
4. **Market Regime**: Adjust recommendations based on current market conditions

Keep answers concise, actionable, and data-driven. Use **bold** for key points.
"""

async def analyze_query(query: str, portfolio_context: list = None, include_macro: bool = True):
    """
    Sends a query to Perplexity AI with the user's portfolio context and macro data.
    
    Args:
        query (str): The user's question (e.g., "Analyze my AAPL position")
        portfolio_context (list): List of dicts [{"symbol": "AAPL", "avg_price": 150, "current_price": 155}, ...]
        include_macro (bool): Whether to include macro economic context
    """
    
    # 1. Construct the Portfolio Context String
    context_str = ""
    if portfolio_context:
        context_str = "**Current Portfolio Holdings:**\n"
        for item in portfolio_context:
            pnl_str = "PROFIT" if item['pnl'] > 0 else "LOSS"
            context_str += f"- {item['symbol']}: {item['quantity']} shares @ ${item['avg_price']:.2f} (Current: ${item['current_price']:.2f}). Status: {pnl_str}\n"
    
    # 2. Add Macro Context if requested
    macro_str = ""
    if include_macro:
        try:
            from backend.services import macro_service
            macro = macro_service.get_macro_summary()
            
            macro_str = f"""
**Current Market Conditions:**
- Fed Funds Rate: {macro['fed_funds_rate']['rate']}%
- Market Regime: {macro['market_regime']['regime']}
- Risk Level: {macro['market_regime']['risk_level']}
- Yield Curve: {macro['market_regime']['yield_curve']}
- Inflation (CPI): {macro['economic_indicators']['cpi']['value']}%
- Recommendation: {macro['market_regime']['recommendation']}
"""
        except Exception as e:
            print(f"Error fetching macro data: {e}")
            macro_str = ""
    
    # 3. Construct the Messages
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"{context_str}\n{macro_str}\n\n**User Question:** {query}"}
    ]
    
    if not PERPLEXITY_API_KEY:
        # Mock Response if no Key
        return {
            "choices": [{
                "message": {
                    "content": "⚠️ **API Key Missing**: This is a mock response.\n\nTo enable real AI analysis, please add your Perplexity API Key in `backend/services/ai_service.py`.\n\nBased on your request, I would typically analyze the charts for **" + (portfolio_context[0]['symbol'] if portfolio_context else "your stocks") + "** and check for recent news catalysts."
                }
            }]
        }

    # 3. Call Perplexity API
    url = "https://api.perplexity.ai/chat/completions"
    headers = {
        "Authorization": f"Bearer {PERPLEXITY_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "sonar-pro", # or sonar-reasoning-pro
        "messages": messages,
        "temperature": 0.2
    }
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(url, headers=headers, json=payload, timeout=60.0)
            
            if response.status_code == 401:
                error_data = response.json()
                error_msg = error_data.get("error", {}).get("message", "Unauthorized")
                if "quota" in error_msg.lower():
                    return {
                        "choices": [{"message": {"content": f"❌ **Perplexity API Quota Exceeded**: {error_msg}\n\nPlease add credits at https://www.perplexity.ai/settings/api"}}]
                    }
                return {
                    "choices": [{"message": {"content": f"❌ **Perplexity API Unauthorized**: {error_msg}\n\nPlease check if your API key is correct in the .env file."}}]
                }
                
            response.raise_for_status()
            return response.json()
        except Exception as e:
            return {
                "choices": [{
                    "message": {
                        "content": f"Error communicating with Perplexity AI: {str(e)}"
                    }
                }]
            }
