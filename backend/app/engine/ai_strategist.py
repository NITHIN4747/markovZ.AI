"""
AI Strategist

Orchestrates the prompt generation from technical data and calls the LLMRouter.
"""
import hashlib
import json
import logging
from datetime import datetime
import redis

from app.config import settings
from app.engine.llm_client import LLMRouter, Provider
from app.engine.mock_data import get_data_source
from app.engine.technicals import TechnicalAnalyzer

logger = logging.getLogger(__name__)
redis_client = redis.Redis.from_url(settings.REDIS_URL, decode_responses=True)

# Initialize providers only if keys exist
_providers = []
if settings.GROQ_API_KEY:
    _providers.append(Provider("Groq", "https://api.groq.com/openai/v1", settings.GROQ_API_KEY, "llama-3.1-70b-versatile"))
if settings.NVIDIA_API_KEY:
    _providers.append(Provider("NIM", "https://integrate.api.nvidia.com/v1", settings.NVIDIA_API_KEY, "meta/llama3-70b-instruct"))
if settings.GEMINI_API_KEY:
    # Google's OpenAI compatibility endpoint for Gemini
    _providers.append(Provider("Gemini", "https://generativelanguage.googleapis.com/v1beta/openai", settings.GEMINI_API_KEY, "gemini-1.5-flash"))
if settings.OPENROUTER_API_KEY:
    _providers.append(Provider("OpenRouter", "https://openrouter.ai/api/v1", settings.OPENROUTER_API_KEY, "meta-llama/llama-3-8b-instruct:free"))

router = LLMRouter(_providers)
analyzer = TechnicalAnalyzer()


def _compute_signal(price: float, sma_20: float, sma_50: float, macd: float, macd_signal: float, rsi: float) -> tuple[str, str]:
    bullish_count = sum([
        price > sma_20,
        price > sma_50,
        macd  > macd_signal,
        rsi   < 70,
    ])
    if bullish_count >= 3:
        return "BULLISH", f"{bullish_count}/4"
    if bullish_count <= 1:
        return "BEARISH", f"{bullish_count}/4"
    return "NEUTRAL", f"{bullish_count}/4"


def _generate_state_hash(price: float, sma_20: float, sma_50: float, rsi: float, macd: float) -> str:
    """Generate a hash representing the current technical state."""
    state_str = f"{price:.2f}_{sma_20:.2f}_{sma_50:.2f}_{rsi:.2f}_{macd:.2f}"
    return hashlib.md5(state_str.encode()).hexdigest()


async def update_insight_if_needed(symbol: str) -> dict:
    """
    Check if the current technical state is already cached.
    If not, acquire a lock, call the LLM, and cache it.
    Returns the latest insight (either fresh or cached).
    """
    hist = get_data_source().history(symbol.upper())
    enriched = analyzer.enrich_data(hist.copy())
    last = enriched.iloc[-1]
    
    price = last["close"]
    sma_20 = last["sma_20"]
    sma_50 = last["sma_50"]
    rsi = last["rsi"]
    macd = last["macd"]
    macd_signal = last["macd_signal"]
    
    signal, score = _compute_signal(price, sma_20, sma_50, macd, macd_signal, rsi)
    state_hash = _generate_state_hash(price, sma_20, sma_50, rsi, macd)
    
    cache_key = f"insight:{symbol.upper()}:{state_hash}"
    current_pointer_key = f"insight:current:{symbol.upper()}"
    
    # 1. Check if we already have an insight for this exact mathematical state
    cached_insight = redis_client.get(cache_key)
    if cached_insight:
        insight = json.loads(cached_insight)
        # Refresh the current pointer just in case
        redis_client.set(current_pointer_key, cached_insight)
        return insight
        
    # 2. No cache. Acquire lock so 5 workers don't call LLM simultaneously
    lock_key = f"lock:insight:{symbol.upper()}"
    if not redis_client.set(lock_key, "1", nx=True, ex=30):
        # Someone else is generating it. Return the LAST known insight for now.
        last_known = redis_client.get(current_pointer_key)
        return json.loads(last_known) if last_known else {"signal": signal, "agreement_score": score, "reasoning": "Generating..."}
        
    try:
        # 3. Generate it
        if not _providers:
            reasoning = "No LLM API keys configured. Set GROQ_API_KEY or others in .env to enable AI insights."
        else:
            prompt = f"""
            Symbol: {symbol.upper()}
            Current Price: {price:.2f}
            SMA 20: {sma_20:.2f}
            SMA 50: {sma_50:.2f}
            RSI (14): {rsi:.2f}
            MACD: {macd:.2f}
            MACD Signal: {macd_signal:.2f}
            
            Computed Signal: {signal} ({score} indicators agree)
            """
            try:
                reasoning = await router.get_reasoning(prompt)
            except Exception as e:
                logger.error(f"AI Insight generation failed for {symbol}: {e}")
                reasoning = "AI analysis temporarily unavailable due to API limits or network issues."
                
        insight = {
            "signal": signal,
            "agreement_score": score,
            "reasoning": reasoning,
            "generated_at": datetime.now().isoformat(),
            "state_hash": state_hash
        }
        
        insight_json = json.dumps(insight)
        
        # 4. Cache it permanently for this mathematical state
        redis_client.set(cache_key, insight_json, ex=86400 * 7) # Keep for 7 days
        # 5. Set it as the current active insight
        redis_client.set(current_pointer_key, insight_json)
        
        return insight
        
    finally:
        redis_client.delete(lock_key)
