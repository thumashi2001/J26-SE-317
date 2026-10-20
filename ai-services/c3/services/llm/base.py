"""
AdaptiveLearnSE Component 3 — Provider-Neutral LLM Service Interface
Defines common data contracts, options, usage metrics, and abstract provider interface.
"""

from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel, Field


class LLMUsage(BaseModel):
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    estimated_cost_usd: float = 0.0


class LLMRequest(BaseModel):
    prompt: str
    system_prompt: str = "You are an expert AI examiner assessing university software engineering answers."
    model: str = "default"
    temperature: float = Field(default=0.1, ge=0.0, le=2.0)
    max_tokens: int = Field(default=1024, gt=0)
    response_format: str = "json"  # "json" or "text"
    json_schema: dict[str, Any] | None = None
    timeout_seconds: float = 15.0


class LLMResponse(BaseModel):
    raw_content: str
    parsed_json: dict[str, Any] | None = None
    model_identifier: str
    provider_name: str
    usage: LLMUsage = Field(default_factory=LLMUsage)
    latency_ms: float = 0.0
    finish_reason: str = "stop"
    is_success: bool = True
    error_message: str | None = None
    is_real_execution: bool = False


class BaseLLMProvider(ABC):
    """Abstract Base Class for LLM providers."""

    def __init__(self, provider_name: str):
        self.provider_name = provider_name

    @abstractmethod
    def is_available(self) -> bool:
        """Return True if provider is operational and credentials are valid."""
        pass

    @abstractmethod
    def health_check(self) -> dict[str, Any]:
        """Return operational health status and diagnostic info."""
        pass

    @abstractmethod
    def generate(self, request: LLMRequest) -> LLMResponse:
        """Execute text/JSON generation under specified parameters."""
        pass
