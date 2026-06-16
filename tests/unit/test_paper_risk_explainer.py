"""Tests for risk explainer."""
from __future__ import annotations

import pytest

from core.paper_trading.risk_explainer import (
    ReasonCode, RiskExplanation, Severity,
    explain, explain_rr_too_low,
)


class TestRiskExplainer:
    def test_all_codes_explainable(self):
        for code in ReasonCode:
            exp = explain(code)
            assert isinstance(exp, RiskExplanation)
            assert exp.reason_code == code
            assert len(exp.human_message) > 0
            assert len(exp.suggested_action) > 0

    def test_rr_too_low(self):
        exp = explain(ReasonCode.RR_TOO_LOW)
        assert exp.severity == Severity.WARNING
        assert "risk/reward" in exp.human_message.lower()
        assert exp.safe_to_retry is True

    def test_max_open_plans(self):
        exp = explain(ReasonCode.MAX_OPEN_PLANS)
        assert exp.severity == Severity.WARNING
        assert exp.safe_to_retry is True

    def test_max_daily_loss_critical(self):
        exp = explain(ReasonCode.MAX_DAILY_LOSS)
        assert exp.severity == Severity.CRITICAL
        assert exp.safe_to_retry is False

    def test_consecutive_loss_cooldown(self):
        exp = explain(ReasonCode.CONSECUTIVE_LOSS_COOLDOWN)
        assert exp.severity == Severity.CRITICAL
        assert exp.safe_to_retry is False

    def test_malformed_fixture(self):
        exp = explain(ReasonCode.MALFORMED_FIXTURE)
        assert "fixture" in exp.human_message.lower()

    def test_no_signal(self):
        exp = explain(ReasonCode.NO_SIGNAL)
        assert exp.severity == Severity.INFO
        assert exp.safe_to_retry is True

    def test_unknown(self):
        exp = explain(ReasonCode.UNKNOWN)
        assert exp.severity == Severity.WARNING

    def test_explain_rr_specific(self):
        exp = explain_rr_too_low(0.8, 1.5)
        assert "0.80" in exp.human_message
        assert "1.50" in exp.human_message
        assert exp.reason_code == ReasonCode.RR_TOO_LOW

    def test_explanation_frozen(self):
        exp = explain(ReasonCode.RR_TOO_LOW)
        with pytest.raises(AttributeError):
            exp.severity = Severity.CRITICAL  # type: ignore

    def test_duplicate_direction(self):
        exp = explain(ReasonCode.DUPLICATE_SYMBOL_DIRECTION)
        assert "same direction" in exp.human_message.lower()

    def test_max_exposure_critical(self):
        exp = explain(ReasonCode.MAX_TOTAL_EXPOSURE)
        assert exp.severity == Severity.CRITICAL
