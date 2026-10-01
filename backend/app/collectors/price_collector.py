import yfinance as yf
import pandas as pd

class PriceCollector:
    """Fetches real-time and historical pricing data using yfinance (Free Tier)."""
    
    def __init__(self):
        # Map our internal symbols to yfinance ticker symbols
        self.symbol_map = {
            "NIFTY": "^NSEI",
            "BANKNIFTY": "^NSEBANK",
            "RELIANCE": "RELIANCE.NS",
            "HDFCBANK": "HDFCBANK.NS"
        }

    async def fetch_latest_price(self, symbol: str) -> dict | None:
        """Fetch the latest live price and volume for a given symbol."""
        yf_ticker = self.symbol_map.get(symbol, f"{symbol}.NS")
        ticker = yf.Ticker(yf_ticker)
        
        try:
            # Fetch 1 day of data at 1 minute interval to get the very latest price
            hist = ticker.history(period="1d", interval="1m")
            if hist.empty:
                return None
                
            latest = hist.iloc[-1]
            return {
                "symbol": symbol,
                "time": latest.name.to_pydatetime(),
                "open": float(latest["Open"]),
                "high": float(latest["High"]),
                "low": float(latest["Low"]),
                "close": float(latest["Close"]),
                "volume": int(latest["Volume"])
            }
        except Exception as e:
            print(f"Error fetching data for {symbol}: {e}")
            return None

    async def fetch_historical_data(self, symbol: str, period: str = "1mo") -> pd.DataFrame:
        """Fetch historical daily data for backfilling the database."""
        yf_ticker = self.symbol_map.get(symbol, f"{symbol}.NS")
        ticker = yf.Ticker(yf_ticker)
        
        hist = ticker.history(period=period)
        return hist
