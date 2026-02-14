
import asyncio
from dotenv import load_dotenv
import os
import json

# Load environment variables
load_dotenv()

# Import AFTER loading env
from backend.services import ai_agents
from backend.services import data_service

async def test_analysis():
    symbol = "^GSPC"
    print(f"Analyzing {symbol}...")
    
    # Pre-check Data Service
    print("\n--- DATA SERVICE CHECK ---")
    try:
        tech = data_service.get_technical_analysis(symbol)
        if "error" in tech:
            print(f"Technical Analysis ERROR: {tech['error']}")
        else:
            print(f"Technical Analysis OK: Price=${tech.get('current_price')}")
            
        score = data_service.get_stock_score(symbol)
        if "error" in score:
            print(f"Score ERROR: {score['error']}")
        else:
            print(f"Score OK: {score.get('score')}")
            
        info = data_service.get_stock_info(symbol)
        print(f"Info Name: {info.get('name')}")
        
    except Exception as e:
        print(f"Data Service Exception: {e}")

    # Run AI Analysis
    print("\n--- AI AGENT CHECK ---")
    try:
        result = await ai_agents.analyze_symbol(symbol)
        print("Result Keys:", result.keys())
        
        if "error" in result:
            print(f"AI ANALYSIS ERROR: {result['error']}")
        else:
            print(f"Recommendation: {result.get('recommendation')}")
            print(f"Confidence: {result.get('confidence')}")
            print(f"Raw Response: {result.get('raw_response')[:200]}...")
        
    except Exception as e:
        print(f"\nCRITICAL ERROR: {e}")

if __name__ == "__main__":
    asyncio.run(test_analysis())
