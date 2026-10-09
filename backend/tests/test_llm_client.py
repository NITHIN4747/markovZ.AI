import pytest
from unittest.mock import AsyncMock, MagicMock
from openai import APITimeoutError, RateLimitError, APIError
import httpx

from app.engine.llm_client import LLMRouter, Provider


@pytest.fixture
def mock_providers():
    p1 = Provider("Groq", "https://api.groq.com/openai/v1", "test", "gpt-oss-120b")
    p2 = Provider("NIM", "https://api.nvidia.com/v1", "test", "meta/llama3-70b")
    
    # Mock the internal clients
    p1.client.chat.completions.create = AsyncMock()
    p2.client.chat.completions.create = AsyncMock()
    
    return [p1, p2]


def _make_mock_response(content: str):
    mock_msg = MagicMock()
    mock_msg.message.content = content
    mock_resp = MagicMock()
    mock_resp.choices = [mock_msg]
    return mock_resp


@pytest.mark.asyncio
async def test_router_success_first_provider(mock_providers):
    router = LLMRouter(mock_providers)
    
    mock_providers[0].client.chat.completions.create.return_value = _make_mock_response('{"reasoning": "RSI is strong."}')
    
    reasoning = await router.get_reasoning("test prompt")
    
    assert reasoning == "RSI is strong."
    mock_providers[0].client.chat.completions.create.assert_called_once()
    mock_providers[1].client.chat.completions.create.assert_not_called()


@pytest.mark.asyncio
async def test_router_fallback_on_timeout(mock_providers):
    router = LLMRouter(mock_providers)
    
    # First provider times out
    mock_request = httpx.Request("POST", "https://api.groq.com")
    mock_providers[0].client.chat.completions.create.side_effect = APITimeoutError(request=mock_request)
    
    # Second succeeds
    mock_providers[1].client.chat.completions.create.return_value = _make_mock_response('{"reasoning": "Second provider rules."}')
    
    reasoning = await router.get_reasoning("test prompt")
    
    assert reasoning == "Second provider rules."
    mock_providers[0].client.chat.completions.create.assert_called_once()
    mock_providers[1].client.chat.completions.create.assert_called_once()


@pytest.mark.asyncio
async def test_router_fallback_on_429(mock_providers):
    router = LLMRouter(mock_providers)
    
    # First provider hits rate limit
    mock_response = httpx.Response(status_code=429, request=httpx.Request("POST", "url"))
    mock_providers[0].client.chat.completions.create.side_effect = RateLimitError(
        message="Too Many Requests", response=mock_response, body=None
    )
    
    # Second succeeds
    mock_providers[1].client.chat.completions.create.return_value = _make_mock_response('{"reasoning": "NIM to the rescue."}')
    
    reasoning = await router.get_reasoning("test prompt")
    
    assert reasoning == "NIM to the rescue."
    mock_providers[0].client.chat.completions.create.assert_called_once()
    mock_providers[1].client.chat.completions.create.assert_called_once()


@pytest.mark.asyncio
async def test_router_fallback_on_bad_json(mock_providers):
    router = LLMRouter(mock_providers)
    
    # First provider returns garbage text (not JSON)
    mock_providers[0].client.chat.completions.create.return_value = _make_mock_response('This is just normal text.')
    
    # Second succeeds
    mock_providers[1].client.chat.completions.create.return_value = _make_mock_response('{"reasoning": "Valid JSON here."}')
    
    reasoning = await router.get_reasoning("test prompt")
    
    assert reasoning == "Valid JSON here."
    mock_providers[0].client.chat.completions.create.assert_called_once()
    mock_providers[1].client.chat.completions.create.assert_called_once()


@pytest.mark.asyncio
async def test_router_strips_markdown_code_blocks(mock_providers):
    router = LLMRouter(mock_providers)
    
    # Model returns JSON wrapped in markdown
    mock_providers[0].client.chat.completions.create.return_value = _make_mock_response('```json\n{"reasoning": "Markdown stripped."}\n```')
    
    reasoning = await router.get_reasoning("test prompt")
    
    assert reasoning == "Markdown stripped."
    
    
@pytest.mark.asyncio
async def test_router_all_fail(mock_providers):
    router = LLMRouter(mock_providers)
    
    # All providers fail
    mock_response = httpx.Response(status_code=500, request=httpx.Request("POST", "url"))
    err = APIError(message="Server error", request=mock_response.request, body=None)
    mock_providers[0].client.chat.completions.create.side_effect = err
    mock_providers[1].client.chat.completions.create.side_effect = err
    
    with pytest.raises(Exception, match="All LLM providers failed"):
        await router.get_reasoning("test prompt")
