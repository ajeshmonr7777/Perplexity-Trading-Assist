
import os
import yaml
from pathlib import Path

class SymbolService:
    def __init__(self):
        self._data_path = Path(__file__).parent.parent / "data" / "symbols.yaml"
        self._cache = None
        self._flattened_cache = []

    def _load_data(self):
        """Loads symbol data from YAML. Checks for updates."""
        # Simple reload for now to support hot updates
        if not self._data_path.exists():
            print(f"Warning: Symbol database not found at {self._data_path}")
            self._cache = {"markets": []}
            return

        try:
            with open(self._data_path, "r", encoding="utf-8") as f:
                self._cache = yaml.safe_load(f)
        except Exception as e:
            print(f"Error loading symbols.yaml: {e}")
            self._cache = {"markets": []}
        
        # Build flattened index for fast search
        self._flattened_cache = []
        for market in self._cache.get("markets", []):
            market_name = market.get("name")
            market_code = market.get("code")
            for item in market.get("symbols", []):
                self._flattened_cache.append({
                    "symbol": item.get("symbol"),
                    "name": item.get("name"),
                    "market": market_name,
                    "market_code": market_code,
                    "search_text": f"{item.get('symbol')} {item.get('name')}".lower()
                })

    def search(self, query: str, market_code: str = None, limit: int = 10):
        """
        Search for symbols by query string vs symbol/name.
        Optional market filter.
        """
        self._load_data()
        
        query = query.lower().strip()
        results = []
        
        for item in self._flattened_cache:
            # Market Filter
            if market_code and item["market_code"] != market_code:
                continue
            
            # Simple substring matching
            if query in item["search_text"]:
                # Calculate relevance (exact symbol match > starts with > contains)
                score = 0
                if item["symbol"].lower() == query:
                    score = 100
                elif item["symbol"].lower().startswith(query):
                    score = 80
                elif item["name"].lower().startswith(query):
                    score = 60
                else:
                    score = 40
                
                results.append({**item, "score": score})

        # Sort by score descending
        results.sort(key=lambda x: x["score"], reverse=True)
        
        # Return top N, removing internal fields
        final_results = []
        for res in results[:limit]:
            final_results.append({
                "symbol": res["symbol"],
                "name": res["name"],
                "market": res["market"],
                "market_code": res["market_code"]
            })
            
        return final_results

    def get_all_symbols(self, market_code: str = None):
        """Return all symbols, optionally filtered by market."""
        self._load_data()
        if not market_code:
            # Return categorized structure? or flattened?
            # User wants "choose from all available symbols" -> likely by market.
            return self._cache.get("markets", [])
        
        # Return specific market's symbols
        for m in self._cache.get("markets", []):
            if m.get("code") == market_code:
                return [m]
        return []

    def get_markets_list(self):
        """Return list of available markets."""
        self._load_data()
        return [{"name": m["name"], "code": m["code"]} for m in self._cache.get("markets", [])]

symbol_service = SymbolService()
