
import yfinance as yf

symbols = ["^GSPC", "^DJI", "^FTSE", "AAPL"]

for sym in symbols:
    print(f"--- Testing {sym} ---")
    try:
        ticker = yf.Ticker(sym)
        
        # Test 1: History
        hist = ticker.history(period="1d")
        if not hist.empty:
            print(f"History: OK, Last Close: {hist['Close'].iloc[-1]}")
        else:
            print("History: EMPTY")
            
        # Test 2: Info
        try:
            info = ticker.info
            print(f"Info: OK, Name: {info.get('shortName')}, Price: {info.get('currentPrice')}")
        except Exception as e:
            print(f"Info: FAILED ({e})")

        # Test 3: Fast Info
        try:
            fast = ticker.fast_info
            print(f"Fast Info: OK, Price: {fast.last_price}")
        except Exception as e:
            print(f"Fast Info: FAILED ({e})")
            
    except Exception as e:
        print(f"Ticker Init FAILED: {e}")
