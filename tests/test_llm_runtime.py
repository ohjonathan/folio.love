"""Tests for folio.llm.runtime — rate limiting, retry, and endpoint validation."""

import time
from unittest.mock import MagicMock, patch

import pytest

from folio.llm.runtime import (
    RateLimiter,
    EndpointNotAllowedError,
    _compute_delay,
    _validate_endpoint,
    execute_with_retry,
)
from folio.llm.types import (
    ErrorDisposition,
    ProviderInput,
    ProviderOutput,
    ProviderRuntimeSettings,
    TokenUsage,
)


class TestRateLimiter:
    """Test RPM and TPM rate limiting."""

    def test_no_throttle_below_limit(self):
        limiter = RateLimiter(rpm_limit=10)
        start = time.monotonic()
        limiter.wait_for_capacity()
        elapsed = time.monotonic() - start
        assert elapsed < 0.1  # should be instant

    def test_rpm_records_requests(self):
        limiter = RateLimiter(rpm_limit=5)
        for _ in range(3):
            limiter.record_request()
        assert len(limiter._request_times) == 3

    def test_tpm_records_usage(self):
        limiter = RateLimiter(rpm_limit=100, tpm_limit=1000)
        limiter.record_usage(TokenUsage(input_tokens=50, output_tokens=20, total_tokens=70))
        assert len(limiter._token_records) == 1

    def test_tpm_skips_zero_usage(self):
        limiter = RateLimiter(rpm_limit=100, tpm_limit=1000)
        limiter.record_usage(TokenUsage())
        assert len(limiter._token_records) == 0


class TestComputeDelay:
    """Test exponential backoff with jitter."""

    def test_retry_after_overrides_backoff(self):
        delay = _compute_delay(0, 1.0, 60.0, retry_after=30.0)
        assert delay == 30.0

    def test_retry_after_capped_at_max_delay(self):
        delay = _compute_delay(0, 1.0, 10.0, retry_after=30.0)
        assert delay == 10.0

    def test_exponential_growth(self):
        # Without jitter the delay at attempt 0 = 1.0, attempt 1 = 2.0, etc.
        # With ±25% jitter, attempt 2 should be in [2.25, 5.25] range
        delays = []
        for _ in range(100):
            d = _compute_delay(2, 1.0, 60.0)
            delays.append(d)
        avg = sum(delays) / len(delays)
        assert 2.5 < avg < 5.5

    def test_max_delay_cap(self):
        delay = _compute_delay(10, 1.0, 5.0)
        assert delay <= 5.0 * 1.25 + 0.01  # 5.0 + max jitter


class TestEndpointValidation:
    """Test endpoint permission checks."""

    def test_excluded_endpoint_raises(self):
        settings = ProviderRuntimeSettings(
            excluded_endpoints=["messages"],
        )
        with pytest.raises(EndpointNotAllowedError, match="excluded"):
            _validate_endpoint("messages", settings)

    def test_allowed_endpoint_passes(self):
        settings = ProviderRuntimeSettings(
            allowed_endpoints=["messages"],
        )
        _validate_endpoint("messages", settings)  # should not raise

    def test_unlisted_endpoint_with_allowed_raises(self):
        settings = ProviderRuntimeSettings(
            allowed_endpoints=["messages"],
        )
        with pytest.raises(EndpointNotAllowedError, match="not in the allowed"):
            _validate_endpoint("chat_completions", settings)

    def test_empty_lists_passes_everything(self):
        settings = ProviderRuntimeSettings()
        _validate_endpoint("messages", settings)  # should not raise


class TestExecuteWithRetry:
    """Test the main execute_with_retry function."""

    def test_success_returns_output(self):
        provider = MagicMock()
        provider.endpoint_name = "messages"
        provider.provider_name = "anthropic"

        output = ProviderOutput(
            raw_text="success",
            usage=TokenUsage(input_tokens=10, output_tokens=5, total_tokens=15),
        )
        provider.analyze.return_value = output

        settings = ProviderRuntimeSettings(
            max_attempts=3,
            allowed_endpoints=["messages"],
        )
        limiter = RateLimiter(rpm_limit=100)
        inp = ProviderInput(prompt="test", images=())

        result = execute_with_retry(provider, None, "model", inp, settings, limiter)
        assert result.raw_text == "success"
        assert result.usage.total_tokens == 15

    def test_transient_failure_retries(self):
        provider = MagicMock()
        provider.endpoint_name = "messages"
        provider.provider_name = "anthropic"

        # First call fails, second succeeds
        output = ProviderOutput(raw_text="ok", usage=TokenUsage())
        provider.analyze.side_effect = [
            RuntimeError("transient"),
            output,
        ]
        provider.classify_error.return_value = ErrorDisposition.transient()

        settings = ProviderRuntimeSettings(
            max_attempts=3,
            base_delay_seconds=0.01,  # fast for testing
            max_delay_seconds=0.02,
            allowed_endpoints=["messages"],
        )
        limiter = RateLimiter(rpm_limit=100)
        inp = ProviderInput(prompt="test", images=())

        result = execute_with_retry(provider, None, "model", inp, settings, limiter)
        assert result.raw_text == "ok"
        assert provider.analyze.call_count == 2

    def test_permanent_failure_raises_immediately(self):
        provider = MagicMock()
        provider.endpoint_name = "messages"
        provider.provider_name = "anthropic"
        provider.analyze.side_effect = RuntimeError("auth failed")
        provider.classify_error.return_value = ErrorDisposition.permanent()

        settings = ProviderRuntimeSettings(
            max_attempts=3,
            allowed_endpoints=["messages"],
        )
        limiter = RateLimiter(rpm_limit=100)
        inp = ProviderInput(prompt="test", images=())

        with pytest.raises(RuntimeError, match="auth failed"):
            execute_with_retry(provider, None, "model", inp, settings, limiter)
        # Should only attempt once
        assert provider.analyze.call_count == 1

    def test_all_attempts_exhausted_raises(self):
        provider = MagicMock()
        provider.endpoint_name = "messages"
        provider.provider_name = "anthropic"
        provider.analyze.side_effect = RuntimeError("overloaded")
        provider.classify_error.return_value = ErrorDisposition.transient()

        settings = ProviderRuntimeSettings(
            max_attempts=2,
            base_delay_seconds=0.01,
            max_delay_seconds=0.02,
            allowed_endpoints=["messages"],
        )
        limiter = RateLimiter(rpm_limit=100)
        inp = ProviderInput(prompt="test", images=())

        with pytest.raises(RuntimeError, match="overloaded"):
            execute_with_retry(provider, None, "model", inp, settings, limiter)
        assert provider.analyze.call_count == 2

    def test_endpoint_not_allowed_raises_before_call(self):
        provider = MagicMock()
        provider.endpoint_name = "messages"
        provider.provider_name = "anthropic"

        settings = ProviderRuntimeSettings(
            excluded_endpoints=["messages"],
        )
        limiter = RateLimiter(rpm_limit=100)
        inp = ProviderInput(prompt="test", images=())

        with pytest.raises(EndpointNotAllowedError):
            execute_with_retry(provider, None, "model", inp, settings, limiter)
        # Should not have called analyze
        provider.analyze.assert_not_called()

    def test_retry_after_respected(self):
        provider = MagicMock()
        provider.endpoint_name = "messages"
        provider.provider_name = "anthropic"

        output = ProviderOutput(raw_text="ok", usage=TokenUsage())
        provider.analyze.side_effect = [
            RuntimeError("rate limited"),
            output,
        ]
        provider.classify_error.return_value = ErrorDisposition.transient(
            retry_after=0.01
        )

        settings = ProviderRuntimeSettings(
            max_attempts=3,
            base_delay_seconds=100.0,  # would be very long without Retry-After
            max_delay_seconds=200.0,
            allowed_endpoints=["messages"],
        )
        limiter = RateLimiter(rpm_limit=100)
        inp = ProviderInput(prompt="test", images=())

        start = time.monotonic()
        result = execute_with_retry(provider, None, "model", inp, settings, limiter)
        elapsed = time.monotonic() - start

        assert result.raw_text == "ok"
        # Should have used Retry-After (0.01s) not base_delay (100s)
        assert elapsed < 5.0
