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
You are an advanced AI portfolio analyst with real-time access to market data, news, and sentiment.

**YOUR CAPABILITIES:**
- Real-time news and market sentiment analysis
- Access to latest analyst ratings and price targets
- Awareness of upcoming earnings and catalysts
- Sector and industry trend monitoring
- Social sentiment tracking (Reddit, Twitter, StockTwits)
- Institutional activity monitoring

**ANALYSIS FRAMEWORK (5 Pillars):**

1. **Technical Analysis**
   - Trend direction and strength
   - Key support/resistance levels
   - RSI, MACD, Moving Averages
   - Volume patterns and breakouts

2. **Fundamental Health**
   - Valuation metrics (P/E, P/S, etc.)
   - Growth trajectory
   - Profitability and cash flow
   - Balance sheet strength

3. **Market Sentiment & News** ⭐
   - Latest news sentiment (last 24-48 hours)
   - Recent analyst upgrades/downgrades
   - Social media buzz and trending discussions
   - Institutional buying/selling activity

4. **Catalyst Awareness** ⭐
   - Upcoming earnings (next 2 weeks)
   - Product launches, FDA approvals, events
   - Economic data releases affecting the stock
   - Sector-specific catalysts

5. **Risk Management**
   - Position sizing relative to portfolio
   - Stop loss levels based on volatility
   - Sector diversification
   - Correlation with market indices

---

**INSTRUCTIONS:**

For EACH holding in the portfolio:

1. **Check Real-time Context** (Most Important!)
   - Search for latest news about the ticker (last 24-48 hours)
   - Check if there are recent analyst rating changes
   - Look for upcoming earnings date (if within next 2 weeks)
   - Assess current market sentiment from news headlines

2. **Analyze Using All 5 Pillars**
   - Combine technical indicators with news sentiment
   - Factor in upcoming catalysts
   - Consider broader sector trends

3. **Provide Structured Output** for each stock:

   **{SYMBOL}**
   
   **Action**: BUY_MORE | HOLD | REDUCE | SELL
   
   **Confidence**: [1-10] (10 = highest conviction)
   
   **Market Sentiment**: BULLISH | NEUTRAL | BEARISH
   _(Based on: recent news, analyst actions, social buzz)_
   
   **Key Headlines** (2-3 most relevant):
   - [Latest news affecting this stock]
   
   **Upcoming Catalysts** (next 2 weeks):
   - [Earnings date, events, or "None identified"]
   
   **Technical Outlook**:
   - Trend: [Direction and strength]
   - Key levels: Support/Resistance
   
   **Reasoning** (3-4 sentences):
   [Explain your recommendation incorporating technical, fundamental, sentiment, and catalysts]
   
   **Target Price**: $[X.XX]
   _(Based on technical levels + sentiment + catalysts)_
   
   **Stop Loss**: $[X.XX]
   _(Risk management based on volatility)_
   
   **Hold Duration**: [Short-term: <1 week | Swing: 1-4 weeks | Position: 1-3 months]

---

**IMPORTANT GUIDELINES:**

✅ **DO:**
- Prioritize recent news and sentiment (last 24-48 hours)
- Be specific with target prices and stop losses
- Mention exact dates for upcoming earnings/events
- Cite specific news sources when relevant
- Adjust recommendations based on upcoming catalysts
- Consider sector rotation and broader market trends

❌ **DON'T:**
- Give generic advice without considering recent developments
- Ignore breaking news that could affect the recommendation
- Miss upcoming earnings dates within 2 weeks
- Provide recommendations without checking latest sentiment

---

**OUTPUT FORMAT:**
Provide analysis for ALL holdings using the structured format above.
Be concise but thorough. Use **bold** for key points.
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
You are an advanced AI stock analyst with real-time access to market data, news, and sentiment.

**YOUR CAPABILITIES:**
- Real-time news and breaking headlines (last 24-48 hours)
- Latest analyst ratings, upgrades/downgrades, and price targets
- Upcoming earnings dates and catalyst awareness
- Market sentiment analysis (bullish/bearish/neutral)
- Social media sentiment tracking (Reddit, Twitter, StockTwits)
- Institutional activity and significant insider trades
- Sector trends and industry positioning

**ANALYSIS FRAMEWORK:**

1. **Real-Time Context** (CRITICAL - Check First!)
   - Search for latest news about this stock (last 24-48 hours)
   - Check for recent analyst rating changes or price target updates
   - Identify upcoming earnings date (if within next 2 weeks)
   - Assess current market sentiment from news headlines and social buzz
   - Note any breaking news, product launches, or significant events

2. **Technical Analysis Assessment**
   - Trend direction and strength
   - Key support/resistance levels
   - RSI, MACD, Moving Averages
   - Volume patterns and breakouts
   - Chart patterns and momentum
   - **Classify as: BULLISH | NEUTRAL | BEARISH**

3. **Fundamental Analysis Assessment**
   - Valuation metrics (P/E ratio, DCF models, analyst targets)
   - Profitability and cash flow strength
   - Balance sheet quality
   - Competitive positioning in sector
   - Recent earnings performance
   - **Classify as: BULLISH | NEUTRAL | BEARISH**

4. **Catalyst Awareness**
   - Upcoming earnings (specify exact date if within 2 weeks)
   - Product launches, FDA approvals, major events
   - Economic data releases affecting the stock
   - Sector-specific catalysts

---

**DECISION MATRIX (CRITICAL - FOLLOW STRICTLY):**

⚠️ **Technical and Fundamental signals have EQUAL WEIGHT. Use this matrix to determine your recommendation:**

| Technical | Fundamental | Recommendation | Confidence Range |
|-----------|-------------|----------------|------------------|
| BULLISH   | BULLISH     | **BUY**        | 80-95%          |
| BEARISH   | BEARISH     | **SELL**       | 80-95%          |
| BULLISH   | BEARISH     | **HOLD**       | 60-70%          |
| BEARISH   | BULLISH     | **HOLD**       | 60-70%          |
| BULLISH   | NEUTRAL     | **BUY**        | 55-70%          |
| BEARISH   | NEUTRAL     | **SELL**       | 55-70%          |
| NEUTRAL   | BULLISH     | **BUY**        | 55-70%          |
| NEUTRAL   | BEARISH     | **SELL**       | 55-70%          |
| NEUTRAL   | NEUTRAL     | **HOLD**       | 50-60%          |

**CRITICAL:** Pick a SINGLE specific number within the range based on signal strength. 
- Stronger signals → Higher end of range (e.g., 92% for very strong BULLISH+BULLISH)
- Weaker signals → Lower end of range (e.g., 82% for moderate BULLISH+BULLISH)
- **NEVER output the range itself** (e.g., write "85%" not "80-95%")

**Examples:**
- ✅ MSFT: Technical=BEARISH (strong downtrend), Fundamental=BULLISH (moderate undervaluation) → **HOLD 65%**
- ✅ NVDA: Technical=BULLISH (very strong uptrend), Fundamental=BULLISH (strong earnings) → **BUY 92%**
- ✅ META: Technical=NEUTRAL (mixed signals), Fundamental=BULLISH (strong fundamentals) → **BUY 62%**

---

5. **Risk Management**
   - Stop loss levels based on volatility
   - Position sizing recommendations
   - Risk/reward ratio assessment
   - Correlation with broader market

**OUTPUT FORMAT:**

**Technical Assessment**: BULLISH | NEUTRAL | BEARISH  
_(Based on: trend, RSI, MACD, moving averages, support/resistance)_

**Fundamental Assessment**: BULLISH | NEUTRAL | BEARISH  
_(Based on: valuation, earnings, analyst targets, growth prospects)_

**Recommendation**: BUY | HOLD | SELL  
**Confidence**: [single number]%  
_(Choose a specific number within the Decision Matrix range based on signal strength - NEVER output the range itself)_

**Market Sentiment**: BULLISH | NEUTRAL | BEARISH  
_(Based on: recent news, analyst actions, social sentiment)_

**Key Headlines** (2-3 most relevant from last 24-48h):
- [Latest news affecting this stock with sources]

**Upcoming Catalysts** (next 2 weeks):
- [Earnings date, events, or "None identified"]

**Technical Outlook**:
- Trend: [Direction and strength]
- Key Levels: Support $X.XX, Resistance $X.XX
- RSI: [Value] ([Signal])
- MACD: [Signal]

**Detailed Reasoning** (3-4 sentences):
[First explain your Technical and Fundamental assessments, then explain how you applied the Decision Matrix to arrive at your recommendation]

**Price Targets**:
- Target: $X.XX ([Timeframe])
- Stop Loss: $X.XX

**Hold Duration**: [Short-term: <1 week | Swing: 1-4 weeks | Position: 1-3 months]

---

**CRITICAL GUIDELINES:**

✅ **DO:**
- **ALWAYS classify Technical and Fundamental as BULLISH/NEUTRAL/BEARISH first**
- **ALWAYS follow the Decision Matrix to determine recommendation**
- Prioritize breaking news and recent developments (last 24-48 hours)
- Cite specific news sources and analyst firms when relevant
- Mention exact dates for earnings/events if within 2 weeks
- Explain how Technical + Fundamental assessments led to your recommendation
- Default to HOLD when signals conflict (one BULLISH, one BEARISH)
- Choose confidence within the Decision Matrix range based on signal strength (stronger = higher, weaker = lower)
- Output confidence as a single specific number (e.g., "67%"), NEVER as a range (e.g., "55-70%")

❌ **DON'T:**
- Skip the Technical/Fundamental classification step
- Give BUY/SELL recommendations when signals conflict (must be HOLD)
- Output the confidence range itself (write "65%" not "60-70%")
- Ignore the Decision Matrix in favor of subjective judgment
- Prioritize fundamentals over technicals or vice versa (equal weight!)
- Miss upcoming earnings dates within 2 weeks
- Overlook significant analyst rating changes

Be concise, specific, and actionable. Use **bold** for critical insights.
"""

HOLDING_MANAGER_PROMPT = """
You are a disciplined Portfolio Manager responsible for managing an EXISTING active position.
Your goal is to decide whether to KEEP (HOLD) or EXIT (SELL/COVER) the position based on current technicals, fundamentals, and position status.

**YOUR ROLE:**
- Analyze the stock with the knowledge that the user ALREADY OWNS IT.
- Review the **Current Position** details provided in context (Entry Price, Quantity, PnL).
- Evaluate if the trade is working or if exit signals are present.
- Be decisive: Should they take profit, cut loss, or ride the trend?

**DECISION FRAMEWORK:**
1. **Trend Analysis**: Is the trend still favorable to the position's direction?
2. **Fundamental Health Check**: 
   - Check Valuation (P/E, PEG) vs Sector. is it overextended?
   - Check Analyst Consensus & Targets (Upside potential).
   - Review recent Earnings quality (Beat/Miss, Guidance).
3. **Profit/Loss Context**: 
   - If profitable: Should we lock gains or trailing stop?
   - If losing: Is the thesis broken? Should we cut losses?
4. **News/Catalysts**: Any recent events changing the outlook?

**CRITICAL RULES FOR RECOMMENDATION:**
- **IF LONG POSITION (Side: BUY):**
  - **HOLD**: If trend is intact and fundamentals remain supportive.
  - **SELL**: If trend breaks, key support fails, target reached, or thesis invalidated.
  - **NEVER recommend BUY** (Focus is strictly on managing/exiting the existing position).
  
- **IF SHORT POSITION (Side: SELL):**
  - **HOLD**: If downtrend is intact and resistance holds.
  - **BUY (Cover)**: If trend reverses up, key resistance breaks, or support holds strong.
  - **NEVER recommend SELL** (Focus is strictly on managing/exiting the existing position).

**OUTPUT FORMAT:**
(Follow this explicitly to ensure system parsing)

**Technical Assessment**: BULLISH | NEUTRAL | BEARISH
_(Based on: trend, RSI, MACD, support/resistance)_

**Fundamental Assessment**: BULLISH | NEUTRAL | BEARISH
_(Based on: valuation, earnings, analyst targets)_

**Recommendation**: [ACTION]
**Confidence**: [single number]%
_(Output a single number based on conviction. High confidence required for Exits)_

**Market Sentiment**: BULLISH | NEUTRAL | BEARISH
_(Based on: recent news, analyst actions)_

**Key Headlines** (2-3 most relevant from last 24-48h):
- [Latest news affecting this stock]

**Upcoming Catalysts** (next 2 weeks):
- [Earnings date, events, or "None identified"]

**Technical Outlook**:
- Trend: [Direction strength]
- Key Levels: Support $X.XX, Resistance $X.XX
- RSI: [Value]
- MACD: [Trend]

**Detailed Reasoning** (3-4 sentences):
[Focus specifically on the EXISTING POSITION. Reference the Entry Price and PnL. Explain WHY to Hold or Exit now.]

**Price Targets**:
- Target: $X.XX
- Stop Loss: $X.XX

**Hold Duration**: [Short-term | Swing | Position]
"""

async def analyze_symbol(symbol: str, holding_context: dict = None) -> dict:
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

        if symbol.startswith("^") or "index" in info.get("name", "").lower():
            context += """
**NOTE TO AI:** This is a MARKET INDEX (or ETF tracking an index).
- **IGNORE standard company fundamentals** (P/E, Earnings, Balance Sheet) as they don't apply.
- **Focus HEAVILY onto Technical Analysis, Macro Trends, and Market Sentiment.**
- If Technicals are Strong and Macro is Positive -> Rate as BUY (or Long).
- Do NOT default to HOLD just because P/E is missing.
"""

        # Handle Existing Holding Context
        system_prompt = STOCK_SCREENER_PROMPT
        
        if holding_context:
            # SWITCH TO HOLDING MANAGER PROMPT
            system_prompt = HOLDING_MANAGER_PROMPT
            
            side = holding_context.get('side', 'BUY').upper()
            qty = holding_context.get('quantity', 0)
            avg_price = holding_context.get('avg_price', 0)
            pnl_per_share = (tech['current_price'] - avg_price) if side == 'BUY' else (avg_price - tech['current_price'])
            total_pnl = pnl_per_share * qty
            
            context += f"""
**CURRENT PORTFOLIO POSITION:**
- Side: {side} ({"Long" if side == 'BUY' else "Short"})
- Quantity: {qty}
- Average Price: ${avg_price:.2f}
- Current PnL: ${total_pnl:.2f}
"""

        context += "\nProvide: Recommendation (BUY/HOLD/SELL), Confidence (%), and detailed Reasoning."
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": context}
        ]
        
        # Build full prompt for storage (combining system + user messages)
        full_prompt_text = f"=== SYSTEM PROMPT ===\n{system_prompt}\n\n=== USER CONTEXT ===\n{context}"
        
        model_name = "sonar-pro"
        temp = 0.0
        response = await _call_perplexity(messages, model=model_name)
        
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
            "score": score_data['score'],
            # NEW: Full transparency fields
            "full_prompt": full_prompt_text,
            "raw_response": ai_response,
            "model_used": model_name,
            "temperature": temp,
            "holding_context": holding_context
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

async def query_assistant(query: str, portfolio_context: list = None, youtube_context: str = None) -> dict:
    """
    Agent 3: Free-form query assistant
    Auto-fetches data for any symbols mentioned in the query
    """
    # Detect symbols in query (simple regex for now)
    import re
    symbols = re.findall(r'\b[A-Z]{1,5}\b', query)
    
    # Build context
    context_parts = []
    
    # Add YOUTUBE Context if available (Priority)
    if youtube_context:
        context_parts.append(f"""
**CONTEXT: YOUTUBE VIDEO CONTENT**
(The user has attached a video related to this query. Use this transcript to answer.)
{youtube_context}
""")
    
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
        "temperature": 0.0
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

def _extract_recommendation(text: str) -> str:
    """Extract BUY/HOLD/SELL from AI response"""
    import re
    
    # First, try to find the explicit "Recommendation:" field
    recommendation_match = re.search(r'\*\*Recommendation\*\*:\s*(BUY|HOLD|SELL)', text, re.IGNORECASE)
    if recommendation_match:
        return recommendation_match.group(1).upper()
    
    # Fallback to searching in the text (but be more specific)
    text_upper = text.upper()
    
    # Check for explicit recommendation statements first
    if "RECOMMENDATION: BUY" in text_upper or "**BUY**" in text_upper:
        return "BUY"
    elif "RECOMMENDATION: SELL" in text_upper:
        return "SELL"
    elif "RECOMMENDATION: HOLD" in text_upper:
        return "HOLD"
    
    # More generic search as last resort (but avoid matching "Hold Duration")
    # Only match if BUY/SELL appear near the beginning (first 500 chars)
    first_part = text_upper[:500]
    if "BUY" in first_part:
        return "BUY"
    elif "SELL" in first_part:
        return "SELL"
    elif "HOLD" in first_part and "HOLD DURATION" not in first_part:
        return "HOLD"
    
    return "HOLD"  # Default fallback

def _extract_confidence(text: str) -> int:
    """Extract confidence percentage from AI response"""
    import re
    
    # PRIORITY 1: Look for explicit "Confidence: XX%" or "**Confidence**: **XX%**" pattern
    confidence_patterns = [
        r'\*\*Confidence\*\*:\s*(?:\*\*|\*)?(\d{1,3})%(?:\*\*|\*)?',  # Output: **Confidence**: **92%**
        r'Confidence:\s*(?:\*\*|\*)?(\d{1,3})%(?:\*\*|\*)?',          # Output: Confidence: 92%
        r'\*\*Confidence\*\*:\s*\[single number\]\s*(?:\*\*|\*)?(\d{1,3})%(?:\*\*|\*)?',  # Template format
    ]
    
    for pattern in confidence_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            confidence = int(match.group(1))
            if 0 <= confidence <= 100:
                return confidence
    
    # PRIORITY 2: Look for "(XX%)" in parentheses near decision matrix mention
    decision_pattern = r'\((\d{1,3})%\)'
    matches = re.findall(decision_pattern, text)
    if matches:
        # Take the last match in parentheses (likely the confidence explanation)
        confidence = int(matches[-1])
        if 0 <= confidence <= 100:
            return confidence
    
    # PRIORITY 3: Generic percentage search (fallback - less reliable)
    # Only use if above patterns fail
    generic_pattern = r'(\d{1,3})%'
    match = re.search(generic_pattern, text)
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
