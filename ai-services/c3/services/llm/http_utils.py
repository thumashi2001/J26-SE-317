"""
AdaptiveLearnSE Component 3 — Shared HTTP helpers for real LLM/embedding providers.
Retry with exponential backoff on 429/5xx (honouring Retry-After) and a process-wide
requests-per-minute limiter configured through C3_LLM_RPM.
"""

import os
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
        if not self.min_interval:
            return
        with self._lock:
            now = time.monotonic()
            delay = self._next_allowed - now
            self._next_allowed = max(now, self._next_allowed) + self.min_interval
        if delay > 0:
            time.sleep(delay)


_limiters: dict[str, RateLimiter] = {}


def get_rate_limiter(key: str) -> RateLimiter:
    """One limiter per provider key, sized from C3_LLM_RPM (default 0 = unlimited)."""
    if key not in _limiters:
        _limiters[key] = RateLimiter(float(os.getenv("C3_LLM_RPM", "0") or 0))
    return _limiters[key]


def _backoff(attempt: int) -> float:
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


def get_json(url: str, *, headers: dict[str, str], timeout: float = 15.0) -> dict[str, Any]:
    with httpx.Client(timeout=timeout) as client:
        res = client.get(url, headers=headers)
        res.raise_for_status()
        return res.json()
