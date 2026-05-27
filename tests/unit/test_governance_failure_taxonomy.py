"""T786 — Governance failure taxonomy tests."""

import pytest
from core.governance_failure_taxonomy import (
    FailureCategory, FailureSeverity, GovernanceFailure,
    classify_governance_failure, failure_to_dict, summarize_failures,
)


# ── category classification ──────────────────────────────────────────


def test_classify_policy_block_from_message():
    f = classify_governance_failure(message="policy violation: forbidden action")
    assert f.category == FailureCategory.POLICY_BLOCK


def test_classify_sandbox_block_from_status():
    f = classify_governance_failure(status_code=403)
    assert f.category == FailureCategory.SANDBOX_BLOCK


def test_classify_adapter_failure_from_message():
    f = classify_governance_failure(message="adapter returned error")
    assert f.category == FailureCategory.ADAPTER_FAILURE


def test_classify_transport_failure_from_message():
    f = classify_governance_failure(message="transport connection refused")
    assert f.category == FailureCategory.TRANSPORT_FAILURE


def test_classify_validation_failure_from_message():
    f = classify_governance_failure(message="validation error: missing field")
    assert f.category == FailureCategory.VALIDATION_FAILURE


def test_classify_timeout_from_status():
    f = classify_governance_failure(status_code=408)
    assert f.category == FailureCategory.TIMEOUT


def test_classify_timeout_from_504():
    f = classify_governance_failure(status_code=504)
    assert f.category == FailureCategory.TIMEOUT


def test_classify_rate_limit_from_status():
    f = classify_governance_failure(status_code=429)
    assert f.category == FailureCategory.RATE_LIMIT


def test_classify_unknown_fallback():
    f = classify_governance_failure(message="something weird happened")
    assert f.category == FailureCategory.UNKNOWN


def test_classify_explicit_category_overrides():
    f = classify_governance_failure(
        status_code=429,
        category=FailureCategory.POLICY_BLOCK,
    )
    assert f.category == FailureCategory.POLICY_BLOCK


# ── severity classification ──────────────────────────────────────────


def test_severity_from_status_429():
    f = classify_governance_failure(status_code=429)
    assert f.severity == FailureSeverity.WARNING


def test_severity_from_status_403():
    f = classify_governance_failure(status_code=403)
    assert f.severity == FailureSeverity.ERROR


def test_severity_policy_block_default_critical():
    f = classify_governance_failure(category=FailureCategory.POLICY_BLOCK)
    assert f.severity == FailureSeverity.CRITICAL


def test_severity_explicit_override():
    f = classify_governance_failure(
        status_code=403,
        severity=FailureSeverity.CRITICAL,
    )
    assert f.severity == FailureSeverity.CRITICAL


# ── retryable ────────────────────────────────────────────────────────


def test_retryable_rate_limit():
    f = classify_governance_failure(status_code=429)
    assert f.retryable is True


def test_retryable_timeout():
    f = classify_governance_failure(status_code=408)
    assert f.retryable is True


def test_retryable_502():
    f = classify_governance_failure(status_code=502)
    assert f.retryable is True


def test_non_retryable_policy_block():
    f = classify_governance_failure(message="policy blocked")
    assert f.retryable is False


def test_non_retryable_400():
    f = classify_governance_failure(status_code=400)
    assert f.retryable is False


def test_retryable_explicit_override():
    f = classify_governance_failure(
        status_code=400,
        retryable=True,
    )
    assert f.retryable is True


# ── serialization ────────────────────────────────────────────────────


def test_failure_to_dict_roundtrip():
    f = classify_governance_failure(
        status_code=429,
        message="rate limited",
        source="test_adapter",
        metadata={"retry_after": 30},
    )
    d = failure_to_dict(f)
    assert d["category"] == "rate_limit"
    assert d["severity"] == "warning"
    assert d["code"] == "RATE_LIMIT_429"
    assert d["message"] == "rate limited"
    assert d["source"] == "test_adapter"
    assert d["retryable"] is True
    assert d["metadata"] == {"retry_after": 30}


def test_failure_to_dict_no_mutation():
    f = classify_governance_failure(metadata={"key": "value"})
    d1 = failure_to_dict(f)
    d2 = failure_to_dict(f)
    d1["metadata"]["key"] = "changed"
    assert d2["metadata"]["key"] == "value"


# ── summary counts ───────────────────────────────────────────────────


def test_summarize_empty():
    s = summarize_failures([])
    assert s["total"] == 0
    assert s["by_category"] == {}
    assert s["retryable"] == 0


def test_summarize_mixed():
    failures = [
        classify_governance_failure(status_code=429),
        classify_governance_failure(status_code=429),
        classify_governance_failure(status_code=403),
        classify_governance_failure(message="policy blocked"),
    ]
    s = summarize_failures(failures)
    assert s["total"] == 4
    assert s["by_category"]["rate_limit"] == 2
    assert s["by_category"]["sandbox_block"] == 1
    assert s["by_category"]["policy_block"] == 1
    assert s["retryable"] == 2
    assert s["non_retryable"] == 2


def test_summarize_by_severity():
    failures = [
        classify_governance_failure(status_code=429),  # WARNING
        classify_governance_failure(status_code=403),  # ERROR
    ]
    s = summarize_failures(failures)
    assert s["by_severity"]["warning"] == 1
    assert s["by_severity"]["error"] == 1


# ── missing/partial inputs ───────────────────────────────────────────


def test_no_inputs_gives_unknown():
    f = classify_governance_failure()
    assert f.category == FailureCategory.UNKNOWN
    assert f.severity == FailureSeverity.ERROR
    assert f.retryable is False
    assert f.code == "UNKNOWN"
    assert f.message == ""
    assert f.source == ""
    assert f.metadata == {}


def test_empty_message():
    f = classify_governance_failure(message="")
    assert f.category == FailureCategory.UNKNOWN


def test_none_status_code():
    f = classify_governance_failure(status_code=None, message="timeout occurred")
    assert f.category == FailureCategory.TIMEOUT
    assert f.code == "TIMEOUT"


def test_metadata_default_is_empty():
    f = classify_governance_failure()
    assert f.metadata == {}


def test_metadata_not_shared():
    f1 = classify_governance_failure(metadata={"a": 1})
    f2 = classify_governance_failure(metadata={"b": 2})
    assert f1.metadata == {"a": 1}
    assert f2.metadata == {"b": 2}
