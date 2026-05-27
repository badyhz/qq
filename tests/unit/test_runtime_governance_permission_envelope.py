"""T828 — Tests for permission envelope."""

import pytest

from core.runtime_governance_permission_envelope import (
    RuntimeGovernancePermissionEnvelope,
    build_runtime_governance_permission_envelope,
    evaluate_permission_envelope,
    permission_envelope_to_dict,
    permission_envelope_to_markdown,
)


class TestBuildEnvelope:
    def test_readonly_safe_verdict_pass(self):
        env = build_runtime_governance_permission_envelope("readonly_safe")
        assert env.verdict == "PASS"
        assert env.allow_read is True
        assert env.allow_write is False
        assert env.allow_network is False
        assert env.allow_order is False
        assert env.allow_account_mutation is False
        assert env.allow_secret_access is False

    def test_write_blocked_verdict_blocked(self):
        env = build_runtime_governance_permission_envelope("write_blocked")
        assert env.verdict == "BLOCKED"
        assert env.allow_write is True

    def test_network_blocked_verdict_blocked(self):
        env = build_runtime_governance_permission_envelope("network_blocked")
        assert env.verdict == "BLOCKED"
        assert env.allow_network is True

    def test_order_blocked_verdict_blocked(self):
        env = build_runtime_governance_permission_envelope("order_blocked")
        assert env.verdict == "BLOCKED"
        assert env.allow_order is True

    def test_secret_blocked_verdict_blocked(self):
        env = build_runtime_governance_permission_envelope("secret_blocked")
        assert env.verdict == "BLOCKED"
        assert env.allow_secret_access is True

    def test_unknown_kind_raises(self):
        with pytest.raises(ValueError, match="Unknown"):
            build_runtime_governance_permission_envelope("nope")


class TestEvaluateEnvelope:
    def test_evaluate_pass(self):
        env = build_runtime_governance_permission_envelope("readonly_safe")
        assert evaluate_permission_envelope(env) == "PASS"

    def test_evaluate_blocked(self):
        env = build_runtime_governance_permission_envelope("order_blocked")
        assert evaluate_permission_envelope(env) == "BLOCKED"


class TestSerialize:
    def test_to_dict_keys(self):
        env = build_runtime_governance_permission_envelope("readonly_safe")
        d = permission_envelope_to_dict(env)
        assert d["verdict"] == "PASS"
        assert d["allow_read"] is True
        assert d["allow_write"] is False
        assert "reason" in d

    def test_deterministic_markdown(self):
        env = build_runtime_governance_permission_envelope("readonly_safe")
        md = permission_envelope_to_markdown(env)
        assert "# Permission Envelope" in md
        assert "**verdict**: PASS" in md
        assert "| read | True |" in md
        assert "| write | False |" in md

    def test_markdown_blocked(self):
        env = build_runtime_governance_permission_envelope("order_blocked")
        md = permission_envelope_to_markdown(env)
        assert "**verdict**: BLOCKED" in md
        assert "| order | True |" in md
