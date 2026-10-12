import { useEffect, useState, useCallback } from 'react';
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

interface AIInsight {
  signal: 'BULLISH' | 'BEARISH' | 'NEUTRAL';
  agreement_score: string;
  reasoning: string;
  generated_at: string | null;
  state_hash: string | null;
}

const AVAILABLE_SYMBOLS = ['NIFTY', 'BANKNIFTY', 'RELIANCE', 'HDFCBANK'];

export default function Dashboard() {
  const [selectedSymbol, setSelectedSymbol] = useState<string>('NIFTY');
  const [data, setData] = useState<MarketData | null>(null);
  const [technicals, setTechnicals] = useState<TechnicalData | null>(null);
  const [codeSignal, setCodeSignal] = useState<string | null>(null);
  const [agreementScore, setAgreementScore] = useState<string | null>(null);
  const [insight, setInsight] = useState<AIInsight | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [clock, setClock] = useState(new Date());

  const fetchDashboardData = useCallback(async (isManual = false) => {
    if (isManual) setRefreshing(true);
    try {
      const [stateRes, techRes, insightRes] = await Promise.all([
        fetch(`http://localhost:8000/api/v1/market/state/${selectedSymbol}`),
        fetch(`http://localhost:8000/api/v1/market/technicals/${selectedSymbol}`),
        fetch(`http://localhost:8000/api/v1/market/insights/${selectedSymbol}`)
      ]);

      if (!stateRes.ok || !techRes.ok) {
        throw new Error('Market API error');
      }

      const stateJson = await stateRes.json();
      const techJson = await techRes.json();

      setData(stateJson.data);
      setTechnicals(techJson.technicals);
      setCodeSignal(techJson.signal || null);
      setAgreementScore(techJson.agreement_score || null);

      if (insightRes.ok) {
        const insightJson = await insightRes.json();
        setInsight(insightJson.insight || null);
      }

      setError(null);
    } catch (err) {
      console.error(err);
      setError('Unable to sync live market data. Verify the backend service is running on port 8000.');
    } finally {
      setLoading(false);
      if (isManual) setRefreshing(false);
    }
  }, [selectedSymbol]);

  useEffect(() => {
    setLoading(true);
    fetchDashboardData();
    const dataInterval = setInterval(() => fetchDashboardData(), 60000);
    return () => clearInterval(dataInterval);
  }, [fetchDashboardData]);

  useEffect(() => {
    const clockInterval = setInterval(() => setClock(new Date()), 1000);
    return () => clearInterval(clockInterval);
  }, []);

  const isPositive = data && data.close >= data.open;
  const currentSignal = insight?.signal || codeSignal || 'NEUTRAL';
  const currentScore = insight?.agreement_score || agreementScore || '0/4';

  const parseScoreNumerator = (scoreStr: string) => {
    const num = parseInt(scoreStr.split('/')[0], 10);
    return isNaN(num) ? 0 : num;
  };
  const agreeingCount = parseScoreNumerator(currentScore);

  return (
    <div className="dashboard-container">
      {/* Top Header */}
      <header className="dashboard-header">
        <div className="brand-group">
          <div className="brand-logo">
            <span className="logo-icon">▲</span>
            <h1>NITHIN-MARKET AI</h1>
          </div>
          <span className="version-pill">v0.1.0 · Multi-LLM</span>
        </div>

        <div className="header-actions">
          <div className="symbol-selector" role="tablist" aria-label="Select symbol">
            {AVAILABLE_SYMBOLS.map((sym) => (
              <button
                key={sym}
                className={`symbol-btn ${selectedSymbol === sym ? 'active' : ''}`}
                onClick={() => setSelectedSymbol(sym)}
              >
                {sym}
              </button>
            ))}
          </div>

          <div className="status-indicator">
            <span className="pulse-dot"></span>
            <span className="status-label">Demo Mode</span>
            <span className="divider">·</span>
            <span className="clock-text">{clock.toLocaleTimeString('en-IN')}</span>
          </div>

          <button 
            className={`refresh-btn ${refreshing ? 'spinning' : ''}`} 
            onClick={() => fetchDashboardData(true)}
            title="Refresh Market Intelligence"
          >
            ↻
          </button>
        </div>
      </header>

      {/* Main Layout Grid */}
      <main className="dashboard-main">
        {loading ? (
          <div className="loading-state glass-panel">
            <div className="spinner"></div>
            <p>Syncing market data & executing AI strategy engine...</p>
          </div>
        ) : error ? (
          <div className="error-state glass-panel">
            <div className="error-icon">⚠️</div>
            <p>{error}</p>
            <button className="retry-btn" onClick={() => fetchDashboardData(true)}>
              Retry Connection
            </button>
          </div>
        ) : data ? (
          <div className="dashboard-grid">
            {/* Left Card: Market Data & Indicators */}
            <div className="market-card glass-panel">
              <div className="card-header">
                <div>
                  <span className="asset-type">NSE Cash Equity</span>
                  <h2>{data.symbol}</h2>
                </div>
                <span className="time-stamp">
                  {new Date(data.time).toLocaleDateString('en-IN', {
                    day: 'numeric',
                    month: 'short',
                    year: 'numeric'
                  })}
                </span>
              </div>

              <div className="price-display">
                <span className={`current-price ${isPositive ? 'text-green' : 'text-red'}`}>
                  ₹{data.close.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                </span>
                <span className={`price-change-tag ${isPositive ? 'badge-green' : 'badge-red'}`}>
                  {isPositive ? '▲ INTRADAY GAIN' : '▼ INTRADAY LOSS'}
                </span>
              </div>

              <div className="stats-grid">
                <div className="stat-box">
                  <span className="stat-label">Open</span>
                  <span className="stat-value">
                    ₹{data.open.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                  </span>
                </div>
                <div className="stat-box">
                  <span className="stat-label">Day High</span>
                  <span className="stat-value text-green">
                    ₹{data.high.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                  </span>
                </div>
                <div className="stat-box">
                  <span className="stat-label">Day Low</span>
                  <span className="stat-value text-red">
                    ₹{data.low.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                  </span>
                </div>
                <div className="stat-box">
                  <span className="stat-label">Volume</span>
                  <span className="stat-value">
                    {data.volume.toLocaleString('en-IN')}
                  </span>
                </div>
              </div>

              {technicals && (
                <div className="technicals-section">
                  <div className="section-title-row">
                    <h3 className="section-title">Technical Matrix</h3>
                    <span className="matrix-badge">Wilder & EWM Smoothed</span>
                  </div>

                  <div className="stats-grid">
                    <div className="stat-box">
                      <span className="stat-label">RSI (14)</span>
                      <span
                        className={`stat-value ${
                          technicals.rsi > 70
                            ? 'text-red'
                            : technicals.rsi < 30
                            ? 'text-green'
                            : 'text-neutral'
                        }`}
                      >
                        {technicals.rsi.toFixed(2)}
                      </span>
                      <span className="indicator-sub">
                        {technicals.rsi > 70 ? 'Overbought' : technicals.rsi < 30 ? 'Oversold' : 'Neutral Range'}
                      </span>
                    </div>

                    <div className="stat-box">
                      <span className="stat-label">MACD (12, 26, 9)</span>
                      <span
                        className={`stat-value ${
                          technicals.macd > technicals.macd_signal ? 'text-green' : 'text-red'
                        }`}
                      >
                        {technicals.macd.toFixed(2)}
                      </span>
                      <span className="indicator-sub">
                        Signal: {technicals.macd_signal.toFixed(2)}
                      </span>
                    </div>

                    <div className="stat-box">
                      <span className="stat-label">SMA 20</span>
                      <span className="stat-value">
                        ₹{technicals.sma_20.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                      </span>
                      <span className="indicator-sub">
                        {data.close > technicals.sma_20 ? 'Above 20 SMA' : 'Below 20 SMA'}
                      </span>
                    </div>

                    <div className="stat-box">
                      <span className="stat-label">SMA 50</span>
                      <span className="stat-value">
                        ₹{technicals.sma_50.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                      </span>
                      <span className="indicator-sub">
                        {data.close > technicals.sma_50 ? 'Above 50 SMA' : 'Below 50 SMA'}
                      </span>
                    </div>
                  </div>
                </div>
              )}
            </div>

            {/* Right Card: AI Strategic Insights Panel */}
            <div className="ai-panel glass-panel">
              <div className="card-header">
                <div className="ai-header-left">
                  <div className="ai-icon-chip">
                    <span className="ai-sparkle">✦</span>
                  </div>
                  <div>
                    <span className="asset-type">Autonomous Strategy Engine</span>
                    <h2>AI Market Intelligence</h2>
                  </div>
                </div>
                <div className="ai-router-tag">
                  <span className="router-dot"></span>
                  Groq · NIM · Gemini
                </div>
              </div>

              {/* Signal Badge & Consensus */}
              <div className="ai-signal-card">
                <div className="signal-top-row">
                  <div className="signal-badge-container">
                    <span className="signal-caption">Algorithmic Signal</span>
                    <div className={`signal-badge badge-${currentSignal.toLowerCase()}`}>
                      <span className="signal-bullet">●</span>
                      <span className="signal-text">{currentSignal}</span>
                    </div>
                  </div>

                  <div className="consensus-container">
                    <span className="signal-caption">Indicator Agreement</span>
                    <div className="consensus-value">
                      <span className="score-number">{currentScore}</span>
                      <span className="score-label">Indicators Align</span>
                    </div>
                  </div>
                </div>

                {/* Consensus Progress Bar */}
                <div className="consensus-progress-track">
                  {[1, 2, 3, 4].map((step) => (
                    <div
                      key={step}
                      className={`progress-step ${step <= agreeingCount ? `step-active-${currentSignal.toLowerCase()}` : ''}`}
                    ></div>
                  ))}
                </div>
              </div>

              {/* AI Reasoning Section */}
              <div className="reasoning-container">
                <div className="reasoning-header">
                  <span className="reasoning-title">Synthesis & Market Context</span>
                  {insight?.state_hash && (
                    <span className="state-hash-pill" title={`State Hash: ${insight.state_hash}`}>
                      Hash: {insight.state_hash.slice(0, 8)}
                    </span>
                  )}
                </div>

                <div className="reasoning-body">
                  <p className="reasoning-text">
                    {insight?.reasoning || 'Synthesizing technical indicators via active LLM provider...'}
                  </p>
                </div>
              </div>

              {/* Metadata Footer */}
              <div className="ai-meta-footer">
                <div className="meta-item">
                  <span className="meta-label">Cache Strategy:</span>
                  <span className="meta-value">State-Hashed (7d TTL)</span>
                </div>
                <div className="meta-item">
                  <span className="meta-label">Generated:</span>
                  <span className="meta-value">
                    {insight?.generated_at
                      ? new Date(insight.generated_at).toLocaleTimeString('en-IN')
                      : 'Real-time'}
                  </span>
                </div>
              </div>

              {/* Mandatory Compliance Disclaimer */}
              <div className="disclaimer-banner">
                <span className="disclaimer-icon">ℹ</span>
                <p className="disclaimer-text">
                  <strong>Not Financial Advice:</strong> AI analysis is generated algorithmically for educational
                  and research purposes only. Technical indicators can produce false signals in volatile regimes.
                </p>
              </div>
            </div>
          </div>
        ) : null}
      </main>
    </div>
  );
}
