"""Integration test: credential policy stub."""
from __future__ import annotations
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent.parent))

from src.runtime_integrations.testnet_readonly_discovery.credential_policy_stub import (
    create_policy, validate_policy, VALID_CLASSES
)


def test_create_policy():
    policy = create_policy()
    assert policy.policy_id.startswith("CRP_")
    assert policy.credential_class == "PLACEHOLDER_ONLY"
    assert policy.human_review_required is True


def test_validate_policy_valid():
    policy = create_policy()
    result = validate_policy(policy)
    assert result[0]["valid"] is True


def test_credential_class_valid():
    policy = create_policy()
    assert policy.credential_class in VALID_CLASSES


def test_no_forbidden_classes():
    policy = create_policy()
    forbidden = ("RAW_API_KEY", "RAW_SECRET", "LIVE_TRADING_KEY", "WITHDRAWAL_KEY", "PRODUCTION_KEY")
    for f in forbidden:
        assert f not in policy.credential_class


def test_render_report():
    from src.runtime_integrations.testnet_readonly_discovery.credential_policy_stub import render_report
    policy = create_policy()
    report = render_report(policy)
    assert "CREDENTIAL_POLICY_STUB_READY" in report
    assert "REAL_CREDENTIALS_NOT_ALLOWED" in report
