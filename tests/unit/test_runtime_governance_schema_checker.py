"""Tests for core.runtime_governance_schema_checker."""
import pytest

from core.runtime_governance_schema_checker import (
    RuntimeGovernanceSchemaCheck,
    check_preflight_packet_dict_schema,
    check_runtime_input_dict_schema,
    schema_check_to_dict,
    schema_check_to_markdown,
)


def _valid_runtime_input() -> dict:
    return {
        "run_id": "r1",
        "adapter_id": "a1",
        "mode": "dry",
        "requested_action": "scan",
        "symbol": "BTCUSDT",
        "environment": "testnet",
        "allow_network": False,
        "allow_submit": False,
        "allow_file_io": False,
        "metadata": {},
    }


def _valid_preflight_packet() -> dict:
    return {
        "input": _valid_runtime_input(),
        "dry_run_result": {},
        "audit_event": {},
        "final_verdict": "pass",
        "proceed": True,
        "notes": [],
    }


class TestCheckRuntimeInputDictSchema:
    def test_valid_input_ok(self):
        result = check_runtime_input_dict_schema(_valid_runtime_input())
        assert result.ok is True
        assert result.missing_fields == []
        assert result.unexpected_fields == []

    def test_missing_field_detected(self):
        data = _valid_runtime_input()
        del data["symbol"]
        result = check_runtime_input_dict_schema(data)
        assert result.ok is False
        assert "symbol" in result.missing_fields

    def test_unexpected_field_detected(self):
        data = _valid_runtime_input()
        data["extra_key"] = 1
        result = check_runtime_input_dict_schema(data)
        assert result.ok is False
        assert "extra_key" in result.unexpected_fields


class TestCheckPreflightPacketDictSchema:
    def test_valid_preflight_ok(self):
        result = check_preflight_packet_dict_schema(_valid_preflight_packet())
        assert result.ok is True
        assert result.missing_fields == []
        assert result.unexpected_fields == []

    def test_preflight_missing_field_detected(self):
        data = _valid_preflight_packet()
        del data["proceed"]
        result = check_preflight_packet_dict_schema(data)
        assert result.ok is False
        assert "proceed" in result.missing_fields


class TestDeterminism:
    def test_dict_deterministic(self):
        check = check_runtime_input_dict_schema(_valid_runtime_input())
        d1 = schema_check_to_dict(check)
        d2 = schema_check_to_dict(check)
        assert d1 == d2

    def test_markdown_deterministic(self):
        data = _valid_runtime_input()
        del data["mode"]
        data["bogus"] = 1
        check = check_runtime_input_dict_schema(data)
        md1 = schema_check_to_markdown(check)
        md2 = schema_check_to_markdown(check)
        assert md1 == md2
        assert "mode" in md1
        assert "bogus" in md1
