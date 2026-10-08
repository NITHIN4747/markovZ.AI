import { useEffect, useState } from 'react';
import './Dashboard.css';

interface TechnicalData {
  rsi: number;
  macd: number;
  macd_signal: number;
  sma_20: number;
  sma_50: number;
}

interface MarketData {
  symbol: string;
  time: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

export default function Dashboard() {
  const [data, setData] = useState<MarketData | null>(null);
  const [technicals, setTechnicals] = useState<TechnicalData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchMarketData = async () => {
    try {
      const [stateResponse, techResponse] = await Promise.all([
        fetch('http://localhost:8000/api/v1/market/state/NIFTY'),
        fetch('http://localhost:8000/api/v1/market/technicals/NIFTY')
      ]);
      
      if (!stateResponse.ok || !techResponse.ok) throw new Error('Network response was not ok');
      
      const stateResult = await stateResponse.json();
      const techResult = await techResponse.json();
      
      setData(stateResult.data);
      setTechnicals(techResult.technicals);
      setError(null);
    } catch (err) {
      setError('Failed to fetch live data. Ensure backend is running.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchMarketData();
    const interval = setInterval(fetchMarketData, 60000); // Poll every minute
    return () => clearInterval(interval);
  }, []);

  const isPositive = data && data.close >= data.open;

  return (
    <div className="dashboard-container">
      <header className="dashboard-header">
        <h1>NITHIN-MARKET AI</h1>
        <div className="status-indicator">
          <span className="pulse-dot"></span> Live Market Intelligence
        </div>
      </header>

      <main className="dashboard-main">
        {loading ? (
          <div className="loading-state">Syncing with market data...</div>
        ) : error ? (
          <div className="error-state">{error}</div>
        ) : data ? (
          <div className="market-card glass-panel">
            <div className="card-header">
              <h2>{data.symbol}</h2>
              <span className="time-stamp">{new Date(data.time).toLocaleTimeString()}</span>
            </div>
            
            <div className="price-display">
              <span className={`current-price ${isPositive ? 'text-green' : 'text-red'}`}>
                ₹{data.close.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
              </span>
            </div>

            <div className="stats-grid">
              <div className="stat-box">
                <span className="stat-label">Open</span>
                <span className="stat-value">₹{data.open.toLocaleString('en-IN')}</span>
              </div>
              <div className="stat-box">
                <span className="stat-label">High</span>
                <span className="stat-value">₹{data.high.toLocaleString('en-IN')}</span>
              </div>
              <div className="stat-box">
                <span className="stat-label">Low</span>
                <span className="stat-value">₹{data.low.toLocaleString('en-IN')}</span>
              </div>
              <div className="stat-box">
                <span className="stat-label">Volume</span>
                <span className="stat-value">{data.volume.toLocaleString('en-IN')}</span>
              </div>
            </div>

            {technicals && (
              <div className="technicals-section">
                <h3 className="section-title">Technical Indicators</h3>
                <div className="stats-grid">
                  <div className="stat-box">
                    <span className="stat-label">RSI (14)</span>
                    <span className={`stat-value ${technicals.rsi > 70 ? 'text-red' : technicals.rsi < 30 ? 'text-green' : ''}`}>
                      {technicals.rsi.toFixed(2)}
                    </span>
                  </div>
                  <div className="stat-box">
                    <span className="stat-label">MACD</span>
                    <span className={`stat-value ${technicals.macd > technicals.macd_signal ? 'text-green' : 'text-red'}`}>
                      {technicals.macd.toFixed(2)}
                    </span>
                  </div>
                  <div className="stat-box">
                    <span className="stat-label">SMA 20</span>
                    <span className="stat-value">₹{technicals.sma_20.toFixed(2)}</span>
                  </div>
                  <div className="stat-box">
                    <span className="stat-label">SMA 50</span>
                    <span className="stat-value">₹{technicals.sma_50.toFixed(2)}</span>
                  </div>
                </div>
              </div>
            )}
          </div>
        ) : null}
      </main>
    </div>
  );
}
