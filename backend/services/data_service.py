import yfinance as yf
import pandas as pd
import numpy as np

def get_current_price(symbol: str) -> float:
    try:
        ticker = yf.Ticker(symbol)
        # fast_info is faster than history
        price = ticker.fast_info.last_price
        return price
    except Exception as e:
        print(f"Error fetching price for {symbol}: {e}")
        return 0.0

def get_stock_info(symbol: str) -> dict:
    try:
        ticker = yf.Ticker(symbol)
        info = ticker.info
        
        # Handle cases where currentPrice is None (common for indices)
        price = info.get("currentPrice")
        if price is None:
            price = get_current_price(symbol)
            
        return {
            "symbol": symbol,
            "name": info.get("shortName", info.get("longName", symbol)),
            "current_price": price,
            "sector": info.get("sector", "Index" if "^" in symbol else "N/A"),
            "pe_ratio": info.get("trailingPE") or 0.0,
            "market_cap": info.get("marketCap") or 0
        }
    except Exception as e:
        print(f"Error fetching info for {symbol}: {e}")
        return {"symbol": symbol, "error": str(e)}

def get_historical_data(symbol: str, period="1mo", interval="1d"):
    try:
        ticker = yf.Ticker(symbol)
        history = ticker.history(period=period, interval=interval)
        # Format for TradingView lightweight charts: time (YYYY-MM-DD) and value/OHLC
        data = []
        for date, row in history.iterrows():
            data.append({
                "time": date.strftime("%Y-%m-%d"),
                "open": row["Open"],
                "high": row["High"],
                "low": row["Low"],
                "close": row["Close"],
                "volume": row["Volume"]
            })
        return data
    except Exception as e:
        print(f"Error fetching history for {symbol}: {e}")
        return []

def calculate_sma(data: pd.DataFrame, period: int) -> pd.Series:
    """Calculate Simple Moving Average"""
    return data['Close'].rolling(window=period).mean()

def calculate_ema(data: pd.DataFrame, period: int) -> pd.Series:
    """Calculate Exponential Moving Average"""
    return data['Close'].ewm(span=period, adjust=False).mean()

def calculate_rsi(data: pd.DataFrame, period: int = 14) -> pd.Series:
    """Calculate Relative Strength Index"""
    delta = data['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

def calculate_macd(data: pd.DataFrame, fast=12, slow=26, signal=9):
    """Calculate MACD (Moving Average Convergence Divergence)"""
    ema_fast = data['Close'].ewm(span=fast, adjust=False).mean()
    ema_slow = data['Close'].ewm(span=slow, adjust=False).mean()
    
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    histogram = macd_line - signal_line
    
    return {
        'macd': macd_line,
        'signal': signal_line,
        'histogram': histogram
    }

def get_trend_classification(data: pd.DataFrame) -> str:
    """Classify trend based on moving averages"""
    if len(data) < 200:
        return "insufficient_data"
    
    sma_50 = calculate_sma(data, 50).iloc[-1]
    sma_200 = calculate_sma(data, 200).iloc[-1]
    current_price = data['Close'].iloc[-1]
    
    # Strong uptrend: price > SMA50 > SMA200
    if current_price > sma_50 > sma_200:
        return "strong_uptrend"
    # Uptrend: price > SMA200
    elif current_price > sma_200:
        return "uptrend"
    # Downtrend: price < SMA200
    elif current_price < sma_200:
        return "downtrend"
    else:
        return "range_bound"

def get_technical_analysis(symbol: str, period="1y") -> dict:
    """Get comprehensive technical analysis for a symbol"""
    try:
        ticker = yf.Ticker(symbol)
        data = ticker.history(period=period)
        
        if len(data) < 50:
            return {"error": "Insufficient data for analysis"}
        
        # Calculate indicators
        current_price = data['Close'].iloc[-1]
        sma_50 = calculate_sma(data, 50).iloc[-1]
        sma_200 = calculate_sma(data, 200).iloc[-1] if len(data) >= 200 else None
        rsi = calculate_rsi(data).iloc[-1]
        macd_data = calculate_macd(data)
        
        # Trend classification
        trend = get_trend_classification(data)
        
        # RSI signals
        rsi_signal = "neutral"
        if rsi > 70:
            rsi_signal = "overbought"
        elif rsi < 30:
            rsi_signal = "oversold"
        
        # MACD signal
        macd_signal = "neutral"
        if macd_data['histogram'].iloc[-1] > 0:
            macd_signal = "bullish"
        elif macd_data['histogram'].iloc[-1] < 0:
            macd_signal = "bearish"
        
        # Support and Resistance (simple calculation)
        recent_data = data.tail(50)
        support = recent_data['Low'].min()
        resistance = recent_data['High'].max()
        
        return {
            "symbol": symbol,
            "current_price": float(current_price),
            "sma_50": float(sma_50),
            "sma_200": float(sma_200) if sma_200 else None,
            "rsi": float(rsi),
            "rsi_signal": rsi_signal,
            "macd": {
                "value": float(macd_data['macd'].iloc[-1]),
                "signal": float(macd_data['signal'].iloc[-1]),
                "histogram": float(macd_data['histogram'].iloc[-1]),
                "trend": macd_signal
            },
            "trend": trend,
            "support": float(support),
            "resistance": float(resistance),
            "volatility": float(data['Close'].pct_change().std() * np.sqrt(252) * 100),  # Annualized volatility
            "analysis_date": data.index[-1].strftime("%Y-%m-%d")
        }
    except Exception as e:
        print(f"Error in technical analysis for {symbol}: {e}")
        return {"error": str(e)}

def get_stock_score(symbol: str) -> dict:
    """Score a stock based on technical and fundamental factors"""
    try:
        tech = get_technical_analysis(symbol)
        info = get_stock_info(symbol)
        
        if "error" in tech:
            return {"symbol": symbol, "score": 0, "error": tech["error"]}
        
        score = 50  # Start neutral
        signals = []
        
        # Trend scoring
        if tech["trend"] == "strong_uptrend":
            score += 20
            signals.append("Strong uptrend")
        elif tech["trend"] == "uptrend":
            score += 10
            signals.append("Uptrend")
        elif tech["trend"] == "downtrend":
            score -= 15
            signals.append("Downtrend")
        
        # RSI scoring
        if tech["rsi_signal"] == "oversold":
            score += 10
            signals.append("RSI oversold (potential buy)")
        elif tech["rsi_signal"] == "overbought":
            score -= 10
            signals.append("RSI overbought (potential sell)")
        
        # MACD scoring
        if tech["macd"]["trend"] == "bullish":
            score += 10
            signals.append("MACD bullish")
        elif tech["macd"]["trend"] == "bearish":
            score -= 10
            signals.append("MACD bearish")
        
        # Price vs MA scoring
        if tech["sma_200"] and tech["current_price"] > tech["sma_200"]:
            score += 10
            signals.append("Above 200-day MA")
        elif tech["sma_200"] and tech["current_price"] < tech["sma_200"]:
            score -= 10
            signals.append("Below 200-day MA")
        
        # Recommendation
        if score >= 70:
            recommendation = "strong_buy"
        elif score >= 55:
            recommendation = "buy"
        elif score >= 45:
            recommendation = "hold"
        elif score >= 30:
            recommendation = "sell"
        else:
            recommendation = "strong_sell"
        
        return {
            "symbol": symbol,
            "score": score,
            "recommendation": recommendation,
            "signals": signals,
            "technical": tech,
            "info": info
        }
    except Exception as e:
        print(f"Error scoring {symbol}: {e}")
        return {"symbol": symbol, "score": 0, "error": str(e)}
