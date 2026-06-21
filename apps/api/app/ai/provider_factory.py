from app.ai.base import BaseAIProvider
from app.core.config import settings
import structlog

logger = structlog.get_logger()


class AIProviderFactory:
    """Factory for creating AI providers."""

    @staticmethod
    def create(provider: str | None = None) -> BaseAIProvider:
        provider = provider or settings.DEFAULT_AI_PROVIDER

        if provider == "openai":
            from app.ai.providers.openai_provider import OpenAIProvider
            if not settings.OPENAI_API_KEY:
                raise ValueError("OPENAI_API_KEY is not configured")
            return OpenAIProvider()

        elif provider == "anthropic":
            from app.ai.providers.claude_provider import ClaudeProvider
            if not settings.ANTHROPIC_API_KEY:
                raise ValueError("ANTHROPIC_API_KEY is not configured")
            return ClaudeProvider()

        else:
            raise ValueError(f"Unknown AI provider: {provider}")

    @staticmethod
    def get_available_providers() -> list[str]:
        providers = []
        if settings.OPENAI_API_KEY:
            providers.append("openai")
        if settings.ANTHROPIC_API_KEY:
            providers.append("anthropic")
        return providers


def get_ai_provider(provider: str | None = None) -> BaseAIProvider:
    return AIProviderFactory.create(provider)
