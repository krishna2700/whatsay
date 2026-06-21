from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import AsyncGenerator, Optional


@dataclass
class AIMessage:
    role: str  # "system" | "user" | "assistant"
    content: str


@dataclass
class AIResponse:
    content: str
    model: str
    provider: str
    tokens_used: int
    finish_reason: str


@dataclass
class RecommendationResult:
    verdict: str
    summary: str
    detailed_analysis: str
    pros: list[str]
    cons: list[str]
    score: int          # 0-100
    confidence: int     # 0-100
    products: list[dict]
    alternatives: list[dict]
    category: str
    intent: str
    amazon_available: bool = True
    unavailable_message: Optional[str] = None


class BaseAIProvider(ABC):
    """Abstract base class for AI providers."""

    @abstractmethod
    async def complete(
        self,
        messages: list[AIMessage],
        max_tokens: int = 2000,
        temperature: float = 0.3,
    ) -> AIResponse:
        """Generate a completion."""
        ...

    @abstractmethod
    async def stream(
        self,
        messages: list[AIMessage],
        max_tokens: int = 2000,
        temperature: float = 0.3,
    ) -> AsyncGenerator[str, None]:
        """Stream a completion."""
        ...

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Return the provider name."""
        ...

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Return the model name."""
        ...
