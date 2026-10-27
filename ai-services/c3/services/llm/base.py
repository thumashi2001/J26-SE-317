"""
AdaptiveLearnSE Component 3 — Provider-Neutral LLM Service Interface
Defines common data contracts, options, usage metrics, and abstract provider interface.

STATUS: OFFLINE / EXPERIMENT SUPPORT ONLY. These classes describe how the project would talk to a large language model
(LLM) such as Gemini, OpenAI or a local Ollama model. The live student marking path (POST /c3/assess) never creates an
LLM request, so no LLM influences a live mark. They are used by the research experiments (experiments/*.py) and by
the /health report, which only says whether a provider is *configured*.
"""

from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel, Field


class LLMUsage(BaseModel):
    """Token counts and estimated cost of one call (for experiment bookkeeping)."""

    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    estimated_cost_usd: float = 0.0


class LLMRequest(BaseModel):
    """One request to a model. temperature is kept low (0.1) so repeated runs behave similarly."""

    prompt: str
    system_prompt: str = "You are an expert AI examiner assessing university software engineering answers."
    model: str = "default"
    temperature: float = Field(default=0.1, ge=0.0, le=2.0)
    max_tokens: int = Field(default=1024, gt=0)
    response_format: str = "json"  # "json" or "text"
    json_schema: dict[str, Any] | None = None
    timeout_seconds: float = 15.0


class LLMResponse(BaseModel):
    """One reply. is_real_execution is True only for genuine provider calls (there is no simulated LLM in C3)."""

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
    retries: int = 0
    cached: bool = False


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
