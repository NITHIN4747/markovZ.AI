import { useEffect, useState } from 'react';
import './Dashboard.css';

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
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchMarketData = async () => {
    try {
      const response = await fetch('http://localhost:8000/api/v1/market/state/NIFTY');
      if (!response.ok) throw new Error('Network response was not ok');
      const result = await response.json();
      setData(result.data);
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
          </div>
        ) : null}
      </main>
    </div>
  );
}
