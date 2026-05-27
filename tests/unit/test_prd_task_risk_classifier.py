"""Tests for prd_task_risk_classifier. Deterministic, no I/O."""

import pytest

from core.prd_task_risk_classifier import (
    PrdTaskRiskClassification,
    classify_backlog_item_risk,
    classify_prd_task_risk,
    risk_classification_to_dict,
    risk_classification_to_markdown,
)


class TestClassifyPrdTaskRisk:
    def test_docs_task_is_low(self):
        r = classify_prd_task_risk("T001", "Write API docs", ["documentation"], [])
        assert r.risk_level == "LOW"
        assert r.allowed_for_agent is True

    def test_parser_task_is_medium(self):
        r = classify_prd_task_risk("T002", "Build YAML parser", [], [])
        assert r.risk_level == "MEDIUM"
        assert r.allowed_for_agent is True

    def test_runtime_integration_is_high(self):
        r = classify_prd_task_risk("T003", "Add runtime integration", [], [])
        assert r.risk_level == "HIGH"
        assert r.allowed_for_agent is True

    def test_live_trading_is_frozen(self):
        r = classify_prd_task_risk("T004", "Enable live trading", [], [])
        assert r.risk_level == "FROZEN"
        assert r.allowed_for_agent is False
        assert any("live trading" in reason for reason in r.reasons)

    def test_secrets_is_frozen(self):
        r = classify_prd_task_risk("T005", "Store API secrets", [], [])
        assert r.risk_level == "FROZEN"
        assert r.allowed_for_agent is False

    def test_deterministic_output(self):
        args = ("T006", "Build parser validator", ["needs network"], ["src/parse.py"])
        r1 = classify_prd_task_risk(*args)
        r2 = classify_prd_task_risk(*args)
        assert r1 == r2
        assert r1 is not r2


class TestClassifyBacklogItemRisk:
    def test_dict_input(self):
        item = {"task_id": "T10", "title": "Write docs", "notes": [], "allowed_files": []}
        r = classify_backlog_item_risk(item)
        assert r.task_id == "T10"
        assert r.risk_level == "LOW"

    def test_object_input(self):
        class Item:
            task_id = "T11"
            title = "Enable live trading"
            notes = []
            allowed_files = []
        r = classify_backlog_item_risk(Item())
        assert r.risk_level == "FROZEN"

    def test_dict_with_id_fallback(self):
        item = {"id": "T12", "title": "Parser work"}
        r = classify_backlog_item_risk(item)
        assert r.task_id == "T12"
        assert r.risk_level == "MEDIUM"


class TestSerialization:
    def test_to_dict(self):
        c = classify_prd_task_risk("T20", "Docs update", [], [])
        d = risk_classification_to_dict(c)
        assert d["task_id"] == "T20"
        assert d["risk_level"] == "LOW"
        assert isinstance(d["reasons"], list)

    def test_to_markdown(self):
        c = classify_prd_task_risk("T21", "Enable live trading", [], [])
        md = risk_classification_to_markdown(c)
        assert "FROZEN" in md
        assert "T21" in md
        assert "no" in md
