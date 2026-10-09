"""
LLM Fallback Client.

Providers:
1. Groq (primary, fastest)
2. NVIDIA NIM (backup, 40 RPM limit)
3. Gemini Flash (via OpenAI compat layer)
4. OpenRouter (last resort)

Computes nothing, only asks the LLM for a reasoning blurb based on passed facts.
"""
import json
import logging
from typing import Optional

from openai import AsyncOpenAI, APIError, APITimeoutError, RateLimitError
from pydantic import BaseModel, Field, ValidationError

logger = logging.getLogger(__name__)


class AnalysisResult(BaseModel):
    reasoning: str = Field(
        description="A concise 2-sentence explanation of the technical indicators. Do not invent levels."
    )


class Provider:
    def __init__(self, name: str, base_url: str, api_key: str, model: str):
        self.name = name
        self.client = AsyncOpenAI(api_key=api_key, base_url=base_url)
        self.model = model


class LLMRouter:
    def __init__(self, providers: list[Provider]):
        self.providers = providers
        # Extremely simple circuit breaker: if a provider fails, we don't mark it dead forever,
        # but in a real system we'd track error rates here.
        
    async def get_reasoning(self, prompt: str, timeout_sec: float = 5.0) -> str:
        """
        Attempt to get reasoning from the provider chain in order.
        Raises APIError if all providers fail.
        """
        last_error = None

        for provider in self.providers:
            try:
                # We do not use response_format={"type": "json_object"} because
                # some open-source models/hosts ignore it or crash. We just ask for JSON
                # and validate it with Pydantic.
                system_prompt = (
                    "You are a technical analyst. You receive computed market data and indicators. "
                    "Write a 1-2 sentence explanation of what these indicators mean. "
                    "Do NOT compute signals, do NOT invent price targets or stop losses. "
                    "Return ONLY valid JSON matching this schema: {\"reasoning\": \"string\"}"
                )

                response = await provider.client.chat.completions.create(
                    model=provider.model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": prompt}
                    ],
                    timeout=timeout_sec,
                    temperature=0.2, # low reasoning effort/hallucination
                )
                
                content = response.choices[0].message.content
                
                # Strip markdown code blocks if the LLM added them
                if content.startswith("```"):
                    content = "\n".join(content.split("\n")[1:-1])

                parsed = AnalysisResult.model_validate_json(content)
                return parsed.reasoning

            except (APITimeoutError, RateLimitError, APIError) as e:
                logger.warning(f"Provider {provider.name} failed: {type(e).__name__} - {str(e)}")
                last_error = e
                continue
            except ValidationError as e:
                logger.warning(f"Provider {provider.name} returned invalid JSON: {str(e)}")
                last_error = e
                continue
            except Exception as e:
                logger.warning(f"Provider {provider.name} unexpected error: {str(e)}")
                last_error = e
                continue

        raise Exception(f"All LLM providers failed. Last error: {str(last_error)}")
