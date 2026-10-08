import pandas as pd

class TechnicalAnalyzer:
    """Computes technical indicators using Pandas on raw OHLCV data."""

    @staticmethod
    def calculate_rsi(data: pd.DataFrame, window: int = 14) -> pd.DataFrame:
        """Calculate Relative Strength Index (RSI)."""
        delta = data['close'].diff()
        gain = (delta.where(delta > 0, 0)).fillna(0)
        loss = (-delta.where(delta < 0, 0)).fillna(0)
        
        avg_gain = gain.rolling(window=window, min_periods=1).mean()
        avg_loss = loss.rolling(window=window, min_periods=1).mean()
        
        rs = avg_gain / avg_loss
        data['rsi'] = 100 - (100 / (1 + rs))
        
        # Handle edge case where loss is 0
        data.loc[avg_loss == 0, 'rsi'] = 100
        return data

    @staticmethod
    def calculate_macd(data: pd.DataFrame, fast: int = 12, slow: int = 26, signal: int = 9) -> pd.DataFrame:
        """Calculate Moving Average Convergence Divergence (MACD)."""
        ema_fast = data['close'].ewm(span=fast, adjust=False).mean()
        ema_slow = data['close'].ewm(span=slow, adjust=False).mean()
        
        data['macd'] = ema_fast - ema_slow
        data['macd_signal'] = data['macd'].ewm(span=signal, adjust=False).mean()
        data['macd_hist'] = data['macd'] - data['macd_signal']
        return data

    @staticmethod
    def calculate_sma(data: pd.DataFrame, window: int = 20) -> pd.DataFrame:
        """Calculate Simple Moving Average."""
        data[f'sma_{window}'] = data['close'].rolling(window=window).mean()
        return data

    def enrich_data(self, data: pd.DataFrame) -> pd.DataFrame:
        """Run all technical calculations on a dataframe."""
        if data.empty or len(data) < 26:
            # Not enough data to calculate technicals reliably
            return data
            
        data = self.calculate_rsi(data)
        data = self.calculate_macd(data)
        data = self.calculate_sma(data, window=20)
        data = self.calculate_sma(data, window=50)
        
        # Drop rows with NaN values resulting from rolling windows
        return data.fillna(0)
