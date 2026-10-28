"""
AdaptiveLearnSE Component 3 — Shared HTTP helpers for real LLM/embedding providers.
Retry with exponential backoff on 429/5xx (honouring Retry-After) and a process-wide
requests-per-minute limiter.

Rate limiting semantics
-----------------------
C3_LLM_RPM is the number of requests STARTED per minute, per provider key, shared by every thread of the
process (e.g. 30 -> one request start at most every 2 s). It is NOT a concurrency limit: slow requests may
overlap. Every attempt counts, including each retry after a 429/5xx. 0 or unset disables limiting.
Optional per-provider overrides C3_LLM_RPM_GEMINI / C3_LLM_RPM_OPENAI take precedence for that provider
(and its embedding key) so one provider's quota does not throttle the other; unset or empty they fall back
to C3_LLM_RPM, and an explicit 0 disables limiting for that provider only. Keys are "gemini",
"gemini-embedding", "openai", "openai-embedding", and "<provider>:<model>" (Gemini chat calls use one limiter per model
    because free-tier quotas are per model); each key has its own limiter, so the chat and embedding
endpoints of one provider are limited independently.

STATUS: offline/experiment support. Retry and rate-limit helpers for real LLM and embedding HTTP calls. NOT USED BY
LIVE MARKING: the web service's /c3/assess path never imports or calls this module's functionality.
"""

import os
import re
import threading
import time
from typing import Any

import httpx

RETRY_STATUS = {408, 429, 500, 502, 503, 504}


class RateLimiter:
    """Thread-safe minimum-interval limiter. rpm <= 0 disables limiting."""

    def __init__(self, rpm: float):
        self.min_interval = 60.0 / rpm if rpm and rpm > 0 else 0.0
        self._lock = threading.Lock()
        self._next_allowed = 0.0

    def wait(self) -> None:
        """Block just long enough to respect the provider's requests-per-minute limit."""
        if not self.min_interval:
            return
        with self._lock:
            now = time.monotonic()
            delay = self._next_allowed - now
            self._next_allowed = max(now, self._next_allowed) + self.min_interval
        if delay > 0:
            time.sleep(delay)


_limiters: dict[str, RateLimiter] = {}
_limiters_lock = threading.Lock()


def rpm_for(key: str) -> float:
    """Requests-per-minute for a limiter key: C3_LLM_RPM_<PROVIDER> if set, else C3_LLM_RPM, else 0 (unlimited)."""
    provider = re.split(r"[-:]", key)[0].upper()  # "gemini:model-x" and "gemini-embedding" -> GEMINI
    specific = os.getenv(f"C3_LLM_RPM_{provider}", "").strip()
    return float(specific or os.getenv("C3_LLM_RPM", "0") or 0)


def get_rate_limiter(key: str) -> RateLimiter:
    """One limiter per provider key (thread-safe: concurrent first callers must share the same instance)."""
    with _limiters_lock:
        if key not in _limiters:
            _limiters[key] = RateLimiter(rpm_for(key))
        return _limiters[key]


def _backoff(attempt: int) -> float:
    """Seconds to wait before retry number `attempt` (doubles each time, capped at 30)."""
    return float(min(2**attempt, 30))


def post_json_with_retry(
    url: str,
    *,
    headers: dict[str, str],
    payload: dict[str, Any],
    timeout: float,
    limiter: RateLimiter | None = None,
    max_retries: int | None = None,
    client: httpx.Client | None = None,
) -> tuple[dict[str, Any], int]:
    """POST JSON and return (parsed body, retries used). Raises httpx.HTTPError on final failure."""
    retries = int(os.getenv("C3_LLM_MAX_RETRIES", "5")) if max_retries is None else max_retries
    owns_client = client is None
    client = client or httpx.Client(timeout=timeout)
    try:
        attempt = 0
        while True:
            if limiter:
                limiter.wait()
            try:
                res = client.post(url, headers=headers, json=payload, timeout=timeout)
            except (httpx.TimeoutException, httpx.TransportError):
                if attempt >= retries:
                    raise
                time.sleep(_backoff(attempt))
                attempt += 1
                continue
            if res.status_code in RETRY_STATUS and attempt < retries:
                retry_after = res.headers.get("retry-after")
                try:
                    delay = float(retry_after) if retry_after else _backoff(attempt)
                except ValueError:
                    delay = _backoff(attempt)
                time.sleep(delay)
                attempt += 1
                continue
            res.raise_for_status()
            return res.json(), attempt
    finally:
        if owns_client:
            client.close()


def get_json(
    url: str, *, headers: dict[str, str], timeout: float = 15.0, client: httpx.Client | None = None
) -> dict[str, Any]:
    """GET a URL and return its JSON body (raises on an HTTP error)."""
    if client is not None:
        res = client.get(url, headers=headers, timeout=timeout)
        res.raise_for_status()
        return res.json()
    with httpx.Client(timeout=timeout) as owned:
        res = owned.get(url, headers=headers)
        res.raise_for_status()
        return res.json()
