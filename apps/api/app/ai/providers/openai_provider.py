from typing import AsyncGenerator
from openai import AsyncOpenAI
from app.ai.base import BaseAIProvider, AIMessage, AIResponse
from app.core.config import settings
import structlog

logger = structlog.get_logger()


class OpenAIProvider(BaseAIProvider):
    def __init__(self):
        self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        self._model = settings.OPENAI_MODEL  # gpt-4o

    @property
    def provider_name(self) -> str:
        return "openai"

    @property
    def model_name(self) -> str:
        return self._model

    def _format_messages(self, messages: list[AIMessage]) -> list[dict]:
        return [{"role": msg.role, "content": msg.content} for msg in messages]

    async def complete(
        self,
        messages: list[AIMessage],
        max_tokens: int = 2000,
        temperature: float = 0.3,
        force_json: bool = True,
    ) -> AIResponse:
        try:
            kwargs = dict(
                model=self._model,
                messages=self._format_messages(messages),
                max_tokens=max_tokens,
                temperature=temperature,
            )
            # Only use JSON mode if explicitly needed and supported
            if force_json:
                kwargs["response_format"] = {"type": "json_object"}

            response = await self.client.chat.completions.create(**kwargs)

            return AIResponse(
                content=response.choices[0].message.content or "",
                model=response.model,
                provider=self.provider_name,
                tokens_used=response.usage.total_tokens if response.usage else 0,
                finish_reason=response.choices[0].finish_reason or "stop",
            )
        except Exception as e:
            logger.error("OpenAI completion failed", error=str(e))
            raise

    async def stream(
        self,
        messages: list[AIMessage],
        max_tokens: int = 2000,
        temperature: float = 0.3,
    ) -> AsyncGenerator[str, None]:
        try:
            stream = await self.client.chat.completions.create(
                model=self._model,
                messages=self._format_messages(messages),
                max_tokens=max_tokens,
                temperature=temperature,
                stream=True,
            )

            async for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
        except Exception as e:
            logger.error("OpenAI stream failed", error=str(e))
            raise
