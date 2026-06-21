from typing import AsyncGenerator
import anthropic
from app.ai.base import BaseAIProvider, AIMessage, AIResponse
from app.core.config import settings
import structlog

logger = structlog.get_logger()


class ClaudeProvider(BaseAIProvider):
    def __init__(self):
        self.client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
        self._model = settings.ANTHROPIC_MODEL

    @property
    def provider_name(self) -> str:
        return "anthropic"

    @property
    def model_name(self) -> str:
        return self._model

    def _split_messages(
        self, messages: list[AIMessage]
    ) -> tuple[str, list[dict]]:
        system_prompt = ""
        chat_messages = []

        for msg in messages:
            if msg.role == "system":
                system_prompt = msg.content
            else:
                chat_messages.append({"role": msg.role, "content": msg.content})

        return system_prompt, chat_messages

    async def complete(
        self,
        messages: list[AIMessage],
        max_tokens: int = 2000,
        temperature: float = 0.3,
    ) -> AIResponse:
        try:
            system_prompt, chat_messages = self._split_messages(messages)

            response = await self.client.messages.create(
                model=self._model,
                max_tokens=max_tokens,
                temperature=temperature,
                system=system_prompt,
                messages=chat_messages,
            )

            content = ""
            for block in response.content:
                if hasattr(block, "text"):
                    content += block.text

            return AIResponse(
                content=content,
                model=response.model,
                provider=self.provider_name,
                tokens_used=response.usage.input_tokens + response.usage.output_tokens,
                finish_reason=response.stop_reason or "stop",
            )
        except Exception as e:
            logger.error("Claude completion failed", error=str(e))
            raise

    async def stream(
        self,
        messages: list[AIMessage],
        max_tokens: int = 2000,
        temperature: float = 0.3,
    ) -> AsyncGenerator[str, None]:
        try:
            system_prompt, chat_messages = self._split_messages(messages)

            async with self.client.messages.stream(
                model=self._model,
                max_tokens=max_tokens,
                temperature=temperature,
                system=system_prompt,
                messages=chat_messages,
            ) as stream:
                async for text in stream.text_stream:
                    yield text
        except Exception as e:
            logger.error("Claude stream failed", error=str(e))
            raise
