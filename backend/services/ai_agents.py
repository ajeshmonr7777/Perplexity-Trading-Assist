import httpx
import json
import os
from datetime import datetime
from backend.services import data_service, macro_service

# Load API Key from environment
PERPLEXITY_API_KEY = os.getenv("PERPLEXITY_API_KEY", "")
FRED_API_KEY = os.getenv("FRED_API_KEY", "")

def is_macro_enabled():
    """Check if macro economic features should be included in prompts"""
    return FRED_API_KEY and FRED_API_KEY.strip() != "" and FRED_API_KEY != "demo"


# ============================================================================
# AGENT 1: PORTFOLIO ANALYZER (Auto-running)
# ============================================================================

PORTFOLIO_ANALYZER_PROMPT = """
You are an automated portfolio monitoring system for swing traders.
Your job is to analyze each holding and provide clear BUY/HOLD/SELL recommendations.

Analysis Framework:
1. **Technical Analysis**: Trend, RSI, MACD, Moving Averages, Support/Resistance
2. **Macro Economic Factors**: Fed policy, interest rates, yield curve, inflation
3. **Risk Management**: Position sizing, stop losses, sector diversification
4. **Market Regime**: Adjust recommendations based on current market conditions

For EACH holding, provide:
- **Action**: BUY_MORE / HOLD / REDUCE / SELL
- **Confidence**: 1-10 (10 = highest conviction)
- **Reasoning**: 2-3 sentences explaining why
- **Target Price**: If applicable
- **Stop Loss**: Recommended exit point

Format your response as structured data for each stock.
"""

async def analyze_portfolio_auto(portfolio_items: list) -> dict:
    """
    Agent 1: Automatically analyze entire portfolio
    Returns structured recommendations for each holding
    """
    if not portfolio_items:
        return {"error": "No portfolio items to analyze"}
    
    # Build context with technical + macro data
    context_parts = []
    context_parts.append("**PORTFOLIO ANALYSIS REQUEST**\n")
    
    # Initialize macro with a default structure to prevent KeyError if not enabled
    macro = {
        'fed_funds_rate': {'rate': 'N/A'},
        'market_regime': {'regime': 'N/A', 'risk_level': 'N/A', 'yield_curve': 'N/A'},
        'economic_indicators': {'cpi': {'value': 'N/A'}}
    }

    # Add macro context ONLY if FRED API is configured
    if is_macro_enabled():
        macro = macro_service.get_macro_summary()
        context_parts.append(f"""
**Market Conditions:**
- Fed Funds Rate: {macro['fed_funds_rate']['rate']}%
- Market Regime: {macro['market_regime']['regime']}
- Risk Level: {macro['market_regime']['risk_level']}
- Yield Curve: {macro['market_regime']['yield_curve']}
- Inflation: {macro['economic_indicators']['cpi']['value']}%
""")
    
    # Add each holding with technical analysis
    context_parts.append("\n**HOLDINGS TO ANALYZE:**\n")
    for item in portfolio_items:
        symbol = item['symbol']
        tech = data_service.get_technical_analysis(symbol)
        score = data_service.get_stock_score(symbol)
        
        context_parts.append(f"""
**{symbol}**
- Quantity: {item['quantity']} shares @ ${item['avg_price']:.2f}
- Current Price: ${item['current_price']:.2f}
- P/L: ${item['pnl']:.2f} ({item['pnl_percent']:.2f}%)
- Trend: {tech.get('trend', 'N/A')}
- RSI: {tech.get('rsi', 'N/A')} ({tech.get('rsi_signal', 'N/A')})
- MACD: {tech.get('macd', {}).get('trend', 'N/A')}
- Score: {score.get('score', 'N/A')}/100
- Recommendation: {score.get('recommendation', 'N/A')}
""")
    
    context_parts.append("\nProvide analysis for EACH stock with Action, Confidence, Reasoning, Target, Stop Loss.")
    
    full_context = "\n".join(context_parts)
    
    # Call Perplexity
    messages = [
        {"role": "system", "content": PORTFOLIO_ANALYZER_PROMPT},
        {"role": "user", "content": full_context}
    ]
    
    response = await _call_perplexity(messages, model="sonar-pro")
    
    result = {
        "agent": "portfolio_analyzer",
        "timestamp": datetime.now().isoformat(),
        "analysis": response["choices"][0]["message"]["content"],
        "portfolio_count": len(portfolio_items)
    }
    
    # Only include market_regime if macro is enabled
    if is_macro_enabled():
        result["market_regime"] = macro['market_regime']['regime']
    
    return result


# ============================================================================
# AGENT 2: STOCK SCREENER (On-demand symbol analysis)
# ============================================================================

STOCK_SCREENER_PROMPT = """
You are a stock screening AI that analyzes individual stocks for swing trading opportunities.

When given a stock symbol, provide a structured analysis:

1. **Recommendation**: BUY / HOLD / SELL
2. **Confidence**: Percentage (0-100%)
3. **Reasoning**: Detailed explanation covering:
   - Technical signals (trend, RSI, MACD)
   - Macro factors (how current Fed policy affects this stock)
   - Risk/reward assessment
   - Entry/exit points

Be specific, data-driven, and actionable. Use **bold** for key points.
"""

async def analyze_symbol(symbol: str) -> dict:
    """
    Agent 2: Analyze a single symbol on-demand
    Returns structured recommendation with confidence and reasoning
    """
    try:
        # Get all data for the symbol
        tech = data_service.get_technical_analysis(symbol)
        score_data = data_service.get_stock_score(symbol)
        info = data_service.get_stock_info(symbol)
        
        if "error" in tech:
            return {"error": f"Could not analyze {symbol}: {tech['error']}"}
        
        # Build context - start with stock and technical data
        context = f"""
**SYMBOL ANALYSIS REQUEST: {symbol}**

**Stock Information:**
- Name: {info.get('name', symbol)}
- Current Price: ${tech['current_price']:.2f}
- Sector: {info.get('sector', 'N/A')}
- Market Cap: ${info.get('market_cap', 0):,.0f}

**Technical Analysis:**
- Trend: {tech['trend']}
- SMA 50: ${tech['sma_50']:.2f}
- SMA 200: ${tech.get('sma_200', 'N/A')}
- RSI: {tech['rsi']:.2f} ({tech['rsi_signal']})
- MACD: {tech['macd']['trend']}
- Support: ${tech['support']:.2f}
- Resistance: ${tech['resistance']:.2f}
- Volatility: {tech['volatility']:.2f}%

**Our Score:**
- Score: {score_data['score']}/100
- Recommendation: {score_data['recommendation']}
- Signals: {', '.join(score_data['signals'])}
"""
        
        # Add macro context ONLY if FRED API is configured
        if is_macro_enabled():
            macro = macro_service.get_macro_summary()
            context += f"""
**Market Conditions:**
- Fed Funds Rate: {macro['fed_funds_rate']['rate']}%
- Market Regime: {macro['market_regime']['regime']}
- Risk Level: {macro['market_regime']['risk_level']}
"""
        
        
        context += "\nProvide: Recommendation (BUY/HOLD/SELL), Confidence (%), and detailed Reasoning."
        
        messages = [
            {"role": "system", "content": STOCK_SCREENER_PROMPT},
            {"role": "user", "content": context}
        ]
        
        response = await _call_perplexity(messages, model="sonar-pro")
        
        # Parse response to extract structured data
        ai_response = response["choices"][0]["message"]["content"]
        
        result = {
            "agent": "stock_screener",
            "symbol": symbol,
            "timestamp": datetime.now().isoformat(),
            "recommendation": _extract_recommendation(ai_response),
            "confidence": _extract_confidence(ai_response),
            "reasoning": ai_response,
            "technical_data": tech,
            "score": score_data['score']
        }
        
        # Only include market_regime if macro is enabled
        if is_macro_enabled():
            macro = macro_service.get_macro_summary()
            result["market_regime"] = macro['market_regime']['regime']
        
        return result
        
    except Exception as e:
        return {"error": str(e)}


# ============================================================================
# AGENT 3: QUERY ASSISTANT (Free-form chat)
# ============================================================================

QUERY_ASSISTANT_PROMPT = """
You are a knowledgeable trading assistant helping users with market questions.

Your capabilities:
- Answer general market questions
- Explain trading concepts
- Provide insights on specific stocks (when mentioned)
- Discuss macro economic trends
- Help with portfolio strategy

When a user mentions a stock symbol, automatically incorporate:
- Current technical analysis
- Recent price action
- Relevant macro factors

Keep answers concise, educational, and actionable. Use **bold** for key points.
"""

async def query_assistant(query: str, portfolio_context: list = None) -> dict:
    """
    Agent 3: Free-form query assistant
    Auto-fetches data for any symbols mentioned in the query
    """
    # Detect symbols in query (simple regex for now)
    import re
    symbols = re.findall(r'\b[A-Z]{1,5}\b', query)
    
    # Build context
    context_parts = []
    
    # Add portfolio context if available
    if portfolio_context:
        context_parts.append("**User's Portfolio:**")
        for item in portfolio_context:
            pnl_str = "PROFIT" if item['pnl'] > 0 else "LOSS"
            context_parts.append(f"- {item['symbol']}: {item['quantity']} shares @ ${item['avg_price']:.2f} (Current: ${item['current_price']:.2f}). Status: {pnl_str}")
        context_parts.append("")
    
    # Add macro context ONLY if FRED API is configured
    if is_macro_enabled():
        macro = macro_service.get_macro_summary()
        context_parts.append(f"""
**Current Market Conditions:**
- Fed Funds Rate: {macro['fed_funds_rate']['rate']}%
- Market Regime: {macro['market_regime']['regime']}
- Risk Level: {macro['market_regime']['risk_level']}
- Yield Curve: {macro['market_regime']['yield_curve']}
""")
    
    # Auto-fetch data for mentioned symbols
    if symbols:
        context_parts.append("\n**Mentioned Stocks:**")
        for symbol in symbols[:3]:  # Limit to 3 symbols
            try:
                tech = data_service.get_technical_analysis(symbol)
                if "error" not in tech:
                    context_parts.append(f"""
**{symbol}:**
- Price: ${tech['current_price']:.2f}
- Trend: {tech['trend']}
- RSI: {tech['rsi']:.2f} ({tech['rsi_signal']})
- MACD: {tech['macd']['trend']}
""")
            except:
                pass
    
    context_parts.append(f"\n**User Question:** {query}")
    
    full_context = "\n".join(context_parts)
    
    messages = [
        {"role": "system", "content": QUERY_ASSISTANT_PROMPT},
        {"role": "user", "content": full_context}
    ]
    
    response = await _call_perplexity(messages, model="sonar-pro")
    
    result = {
        "agent": "query_assistant",
        "timestamp": datetime.now().isoformat(),
        "query": query,
        "response": response["choices"][0]["message"]["content"],
        "symbols_detected": symbols
    }
    
    # Only include market_regime if macro is enabled
    if is_macro_enabled():
        macro = macro_service.get_macro_summary()
        result["market_regime"] = macro['market_regime']['regime']
    
    return result


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

async def _call_perplexity(messages: list, model: str = "sonar-pro") -> dict:
    """Internal function to call Perplexity API"""
    if not PERPLEXITY_API_KEY:
        return {
            "choices": [{
                "message": {
                    "content": "⚠️ **API Key Missing**: Please add PERPLEXITY_API_KEY to .env file"
                }
            }]
        }
    
    url = "https://api.perplexity.ai/chat/completions"
    headers = {
        "Authorization": f"Bearer {PERPLEXITY_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": model,
        "messages": messages,
        "temperature": 0.2
    }
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(url, headers=headers, json=payload, timeout=60.0)
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

def _extract_recommendation(text: str) -> str:
    """Extract BUY/HOLD/SELL from AI response"""
    text_upper = text.upper()
    if "STRONG BUY" in text_upper or "**BUY**" in text_upper:
        return "BUY"
    elif "SELL" in text_upper:
        return "SELL"
    elif "HOLD" in text_upper:
        return "HOLD"
    return "HOLD"

def _extract_confidence(text: str) -> int:
    """Extract confidence percentage from AI response"""
    import re
    # Look for patterns like "85%", "Confidence: 85", etc.
    patterns = [
        r'(\d{1,3})%',
        r'[Cc]onfidence[:\s]+(\d{1,3})',
        r'(\d{1,3})/100'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            confidence = int(match.group(1))
            if 0 <= confidence <= 100:
                return confidence
    
    # Default based on recommendation
    if "STRONG" in text.upper():
        return 85
    elif "BUY" in text.upper() or "SELL" in text.upper():
        return 70
    return 50
