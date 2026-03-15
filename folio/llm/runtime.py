"""LLM runtime: shared rate-limiting, retry, and throttle layer.

This module owns:
- Rolling-window RPM limiter
- Best-effort TPM limiter (actual usage, not estimated)
- Exponential backoff with jitter for transient failures
- Retry-After override from provider errors
- Endpoint permission validation
- Max-attempt handling per request

It does NOT own: prompt construction, JSON parsing, fallback policy,
or provider selection.
"""

from __future__ import annotations

import logging
import random
import time
from collections import deque
from dataclasses import dataclass, field

from .types import (
    AnalysisProvider,
    ErrorDisposition,
    ProviderInput,
    ProviderOutput,
    ProviderRuntimeSettings,
    TokenUsage,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Rate limiter
# ---------------------------------------------------------------------------

_WINDOW_SECONDS = 60.0


@dataclass
class RateLimiter:
    """Rolling-window RPM and best-effort TPM tracker.

    Stage-scoped and in-process — not a cross-process coordinator.
    """

    rpm_limit: int = 50
    tpm_limit: int | None = None
    _request_times: deque = field(default_factory=deque)
    _token_records: deque = field(default_factory=deque)  # (timestamp, tokens)

    def wait_for_capacity(self) -> None:
        """Block until RPM and TPM windows have capacity.

        RPM: strict — always waits.
        TPM: best-effort — only blocks when the rolling window is at or
        above the cap. Does NOT reserve estimated tokens before the call.
        """
        now = time.monotonic()

        # Prune expired RPM entries
        while self._request_times and (now - self._request_times[0]) >= _WINDOW_SECONDS:
            self._request_times.popleft()

        # RPM gate
        if len(self._request_times) >= self.rpm_limit:
            oldest = self._request_times[0]
            sleep_time = _WINDOW_SECONDS - (now - oldest) + 0.05
            if sleep_time > 0:
                logger.debug("RPM limit reached (%d/%d), sleeping %.1fs",
                             len(self._request_times), self.rpm_limit, sleep_time)
                time.sleep(sleep_time)
                now = time.monotonic()
                # Re-prune after sleep
                while self._request_times and (now - self._request_times[0]) >= _WINDOW_SECONDS:
                    self._request_times.popleft()

        # TPM gate (best-effort, looping until under cap)
        if self.tpm_limit is not None:
            while True:
                while self._token_records and (now - self._token_records[0][0]) >= _WINDOW_SECONDS:
                    self._token_records.popleft()

                window_tokens = sum(t for _, t in self._token_records)
                if window_tokens < self.tpm_limit:
                    break  # Under cap — proceed

                if not self._token_records:
                    break  # Nothing to wait for

                oldest_ts = self._token_records[0][0]
                sleep_time = _WINDOW_SECONDS - (now - oldest_ts) + 0.05
                if sleep_time <= 0:
                    continue  # Already expired, re-prune on next iteration

                logger.debug("TPM limit reached (%d/%d), sleeping %.1fs",
                             window_tokens, self.tpm_limit, sleep_time)
                time.sleep(sleep_time)
                now = time.monotonic()

    def record_request(self) -> None:
        """Record a request timestamp for RPM tracking."""
        self._request_times.append(time.monotonic())

    def record_usage(self, usage: TokenUsage) -> None:
        """Record actual token usage for TPM tracking."""
        if usage.total_tokens > 0:
            self._token_records.append((time.monotonic(), usage.total_tokens))


# ---------------------------------------------------------------------------
# Retry with backoff
# ---------------------------------------------------------------------------


def _compute_delay(
    attempt: int,
    base_delay: float,
    max_delay: float,
    retry_after: float | None = None,
) -> float:
    """Compute delay with exponential backoff + jitter, or Retry-After override."""
    if retry_after is not None and retry_after > 0:
        return min(retry_after, max_delay)

    # Exponential backoff: base * 2^attempt + jitter
    delay = base_delay * (2 ** attempt)
    delay = min(delay, max_delay)
    # Add jitter: ±25% of computed delay
    jitter = delay * 0.25 * (2 * random.random() - 1)
    return max(0.0, delay + jitter)


# ---------------------------------------------------------------------------
# Endpoint validation
# ---------------------------------------------------------------------------


class EndpointNotAllowedError(Exception):
    """Raised when a provider endpoint is not permitted by configuration."""
    pass


def _validate_endpoint(
    endpoint_name: str,
    settings: ProviderRuntimeSettings,
) -> None:
    """Validate that the endpoint is permitted.

    Fails BEFORE network I/O with a clear configuration error.
    """
    # Check excluded first
    if endpoint_name in settings.excluded_endpoints:
        raise EndpointNotAllowedError(
            f"Endpoint '{endpoint_name}' is excluded by provider configuration"
        )

    # If allowed_endpoints is non-empty, the endpoint must be in the list
    if settings.allowed_endpoints and endpoint_name not in settings.allowed_endpoints:
        raise EndpointNotAllowedError(
            f"Endpoint '{endpoint_name}' is not in the allowed endpoints: "
            f"{settings.allowed_endpoints}"
        )


# ---------------------------------------------------------------------------
# Main execution function
# ---------------------------------------------------------------------------


def execute_with_retry(
    provider: AnalysisProvider,
    client,
    model: str,
    inp: ProviderInput,
    settings: ProviderRuntimeSettings,
    limiter: RateLimiter,
) -> ProviderOutput:
    """Execute a provider call with rate limiting, retry, and backoff.

    Flow:
    1. Validate endpoint permissions
    2. Wait for RPM/TPM capacity
    3. Perform the call
    4. Record usage
    5. On transient failure: retry up to max_attempts with backoff
    6. On permanent failure: raise immediately

    Returns:
        ProviderOutput on success.

    Raises:
        EndpointNotAllowedError: if endpoint is not permitted.
        Exception: the last provider exception after max_attempts exhausted.
    """
    # Step 1: validate endpoint before any network I/O
    _validate_endpoint(provider.endpoint_name, settings)

    last_exc: Exception | None = None

    for attempt in range(settings.max_attempts):
        # Step 2: wait for rate-limit capacity
        limiter.wait_for_capacity()

        try:
            # Step 3: record request timestamp and perform call
            limiter.record_request()
            output = provider.analyze(client, model, inp)

            # Step 4: record actual token usage
            limiter.record_usage(output.usage)

            return output

        except Exception as exc:
            last_exc = exc
            disposition = provider.classify_error(exc)

            if disposition.kind == "permanent":
                logger.warning(
                    "Provider '%s' permanent error on attempt %d: %s",
                    provider.provider_name, attempt + 1, exc,
                )
                raise

            # Transient — retry if attempts remain
            if attempt < settings.max_attempts - 1:
                delay = _compute_delay(
                    attempt,
                    settings.base_delay_seconds,
                    settings.max_delay_seconds,
                    retry_after=disposition.retry_after_seconds,
                )
                logger.warning(
                    "Provider '%s' transient error on attempt %d/%d, "
                    "retrying in %.1fs: %s",
                    provider.provider_name, attempt + 1, settings.max_attempts,
                    delay, exc,
                )
                time.sleep(delay)
            else:
                logger.warning(
                    "Provider '%s' exhausted all %d attempts: %s",
                    provider.provider_name, settings.max_attempts, exc,
                )

    # All attempts exhausted — raise last exception
    assert last_exc is not None
    raise last_exc
