import requests
from datetime import datetime, timedelta
import pandas as pd

def get_fed_funds_rate():
    """Get current Federal Funds Rate from FRED API (Federal Reserve Economic Data)"""
    import os
    
    # Get API key from environment (or use 'demo' for testing)
    api_key = os.getenv("FRED_API_KEY", "demo")
    
    try:
        url = "https://api.stlouisfed.org/fred/series/observations"
        params = {
            "series_id": "DFF",  # Daily Federal Funds Rate
            "api_key": api_key,
            "file_type": "json",
            "sort_order": "desc",
            "limit": 1
        }
        
        # Actually make the API call
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        # Parse the response
        if "observations" in data and len(data["observations"]) > 0:
            latest = data["observations"][0]
            return {
                "rate": float(latest["value"]),
                "date": latest["date"],
                "source": "FRED API (Real Data)" if api_key != "demo" else "FRED API (Demo)"
            }
        else:
            raise ValueError("No data returned from FRED API")
            
    except Exception as e:
        print(f"⚠️ Error fetching Fed Funds Rate from FRED: {e}")
        print("📊 Falling back to mock data")
        # Fallback to mock data only if API fails
        return {
            "rate": 5.33,
            "date": datetime.now().strftime("%Y-%m-%d"),
            "source": "Mock Data (FRED API failed)"
        }

def get_treasury_yields():
    """Get Treasury Yield Curve data"""
    import os
    
    api_key = os.getenv("FRED_API_KEY", "demo")
    
    try:
        # Fetch 2-year, 10-year, and 30-year Treasury yields from FRED
        yields = {}
        series_map = {
            "2_year": "DGS2",   # 2-Year Treasury Constant Maturity Rate
            "10_year": "DGS10", # 10-Year Treasury Constant Maturity Rate
            "30_year": "DGS30"  # 30-Year Treasury Constant Maturity Rate
        }
        
        for key, series_id in series_map.items():
            url = "https://api.stlouisfed.org/fred/series/observations"
            params = {
                "series_id": series_id,
                "api_key": api_key,
                "file_type": "json",
                "sort_order": "desc",
                "limit": 1
            }
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if "observations" in data and len(data["observations"]) > 0:
                latest = data["observations"][0]
                # Handle missing data (represented as ".")
                if latest["value"] != ".":
                    yields[key] = float(latest["value"])
                    if key == "10_year":
                        date = latest["date"]
        
        # Calculate spread (inverted yield curve indicator)
        spread = yields.get("10_year", 0) - yields.get("2_year", 0)
        
        return {
            "2_year": yields.get("2_year", 4.25),
            "10_year": yields.get("10_year", 4.15),
            "30_year": yields.get("30_year", 4.35),
            "date": date if 'date' in locals() else datetime.now().strftime("%Y-%m-%d"),
            "spread_10y_2y": round(spread, 2),
            "source": "FRED API (Real Data)" if api_key != "demo" else "FRED API (Demo)"
        }
        
    except Exception as e:
        print(f"⚠️ Error fetching Treasury Yields from FRED: {e}")
        print("📊 Falling back to mock data")
        # Fallback to mock data
        return {
            "2_year": 4.25,
            "10_year": 4.15,
            "30_year": 4.35,
            "date": datetime.now().strftime("%Y-%m-%d"),
            "spread_10y_2y": -0.10,
            "source": "Mock Data (FRED API failed)"
        }

def get_economic_indicators():
    """Get key economic indicators (CPI, Unemployment, etc.)"""
    import os
    
    api_key = os.getenv("FRED_API_KEY", "demo")
    
    try:
        indicators = {}
        
        # Fetch CPI (Consumer Price Index - Inflation)
        url = "https://api.stlouisfed.org/fred/series/observations"
        cpi_params = {
            "series_id": "CPIAUCSL",  # Consumer Price Index for All Urban Consumers
            "api_key": api_key,
            "file_type": "json",
            "sort_order": "desc",
            "limit": 2  # Get last 2 to calculate YoY change
        }
        
        response = requests.get(url, params=cpi_params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        if "observations" in data and len(data["observations"]) >= 2:
            latest_cpi = data["observations"][0]
            prev_cpi = data["observations"][1]
            
            if latest_cpi["value"] != "." and prev_cpi["value"] != ".":
                current_val = float(latest_cpi["value"])
                prev_val = float(prev_cpi["value"])
                yoy_change = ((current_val - prev_val) / prev_val) * 100
                
                indicators["cpi"] = {
                    "value": round(yoy_change, 2),
                    "date": latest_cpi["date"],
                    "yoy_change": round(yoy_change, 2),
                    "description": "Consumer Price Index (Inflation)"
                }
        
        # Fetch Unemployment Rate
        unemp_params = {
            "series_id": "UNRATE",  # Unemployment Rate
            "api_key": api_key,
            "file_type": "json",
            "sort_order": "desc",
            "limit": 1
        }
        
        response = requests.get(url, params=unemp_params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        if "observations" in data and len(data["observations"]) > 0:
            latest = data["observations"][0]
            if latest["value"] != ".":
                indicators["unemployment"] = {
                    "value": float(latest["value"]),
                    "date": latest["date"],
                    "description": "Unemployment Rate"
                }
        
        # Add GDP (mock for now as it's quarterly and complex to calculate)
        indicators["gdp_growth"] = {
            "value": 2.5,
            "date": "2025-Q4",
            "description": "GDP Growth Rate (Annual) - Mock"
        }
        
        indicators["source"] = "FRED API (Real Data)" if api_key != "demo" else "FRED API (Demo)"
        
        return indicators
        
    except Exception as e:
        print(f"⚠️ Error fetching economic indicators from FRED: {e}")
        print("📊 Falling back to mock data")
        # Fallback to mock data
        return {
            "cpi": {
                "value": 3.4,
                "date": "2026-01-01",
                "yoy_change": 3.4,
                "description": "Consumer Price Index (Inflation)"
            },
            "unemployment": {
                "value": 3.7,
                "date": "2026-01-01",
                "description": "Unemployment Rate"
            },
            "gdp_growth": {
                "value": 2.5,
                "date": "2025-Q4",
                "description": "GDP Growth Rate (Annual)"
            },
            "source": "Mock Data (FRED API failed)"
        }

def get_fed_meeting_dates():
    """Get upcoming Federal Reserve FOMC meeting dates"""
    # 2026 FOMC Meeting Schedule (approximate)
    meetings = [
        {"date": "2026-01-28", "status": "completed"},
        {"date": "2026-03-18", "status": "upcoming"},
        {"date": "2026-05-06", "status": "upcoming"},
        {"date": "2026-06-17", "status": "upcoming"},
        {"date": "2026-07-29", "status": "upcoming"},
        {"date": "2026-09-16", "status": "upcoming"},
        {"date": "2026-11-04", "status": "upcoming"},
        {"date": "2026-12-16", "status": "upcoming"},
    ]
    
    today = datetime.now()
    upcoming = [m for m in meetings if datetime.strptime(m["date"], "%Y-%m-%d") > today]
    
    return {
        "next_meeting": upcoming[0] if upcoming else None,
        "all_meetings": meetings,
        "source": "Federal Reserve Schedule"
    }

def get_market_regime():
    """Analyze current market regime based on macro data"""
    fed_rate = get_fed_funds_rate()
    yields = get_treasury_yields()
    indicators = get_economic_indicators()
    
    # Simple regime classification
    regime = "neutral"
    risk_level = "moderate"
    
    # Check for inverted yield curve (recession signal)
    if yields.get("spread_10y_2y", 0) < 0:
        regime = "risk_off"
        risk_level = "high"
    
    # High inflation + high rates = restrictive
    if indicators.get("cpi", {}).get("value", 0) > 3.0 and fed_rate.get("rate", 0) > 5.0:
        regime = "restrictive"
        risk_level = "elevated"
    
    # Low rates + low inflation = accommodative
    if fed_rate.get("rate", 0) < 2.0 and indicators.get("cpi", {}).get("value", 0) < 2.0:
        regime = "accommodative"
        risk_level = "low"
    
    return {
        "regime": regime,
        "risk_level": risk_level,
        "fed_rate": fed_rate.get("rate"),
        "inflation": indicators.get("cpi", {}).get("value"),
        "yield_curve": "inverted" if yields.get("spread_10y_2y", 0) < 0 else "normal",
        "recommendation": get_regime_recommendation(regime)
    }

def get_regime_recommendation(regime):
    """Get trading recommendations based on market regime"""
    recommendations = {
        "accommodative": "Favorable for risk assets. Consider increasing equity exposure.",
        "neutral": "Balanced approach. Maintain diversified portfolio.",
        "restrictive": "Cautious stance. Focus on quality stocks and defensive sectors.",
        "risk_off": "Defensive positioning. Reduce risk, increase cash allocation."
    }
    return recommendations.get(regime, "Monitor conditions closely.")

def get_macro_summary():
    """Get comprehensive macro summary for AI analysis"""
    fed_rate = get_fed_funds_rate()
    yields = get_treasury_yields()
    indicators = get_economic_indicators()
    meetings = get_fed_meeting_dates()
    regime = get_market_regime()
    
    return {
        "fed_funds_rate": fed_rate,
        "treasury_yields": yields,
        "economic_indicators": indicators,
        "fed_meetings": meetings,
        "market_regime": regime,
        "last_updated": datetime.now().isoformat()
    }
