"""Tests for read-only hook sanitizer — pure pytest, no I/O."""
from core.read_only_hook_sanitizer import (
    SanitizedPayload,
    sanitize_payload,
    sanitized_payload_to_dict,
)


class TestSanitizer:
    def test_redacts_secrets(self):
        payload = {"api_key": "sk-123", "name": "test", "password": "hunter2"}
        result = sanitize_payload(payload)
        assert isinstance(result, SanitizedPayload)
        assert result.payload["api_key"] == "[REDACTED]"
        assert result.payload["password"] == "[REDACTED]"
        assert result.payload["name"] == "test"
        assert "api_key" in result.redacted_fields
        assert "password" in result.redacted_fields

    def test_clean_payload_unchanged(self):
        payload = {"symbol": "BTCUSDT", "side": "buy"}
        result = sanitize_payload(payload)
        assert result.payload == payload
        assert result.redacted_fields == []

    def test_deterministic(self):
        payload = {"api_key": "x", "token": "y", "val": 1}
        r1 = sanitized_payload_to_dict(sanitize_payload(payload))
        r2 = sanitized_payload_to_dict(sanitize_payload(payload))
        assert r1 == r2
