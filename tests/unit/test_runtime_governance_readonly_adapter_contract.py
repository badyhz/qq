import pytest

from core.runtime_governance_readonly_adapter_contract import (
    RuntimeGovernanceReadOnlyAdapterInput,
    RuntimeGovernanceReadOnlyAdapterOutput,
    build_readonly_adapter_input_sample,
    readonly_adapter_input_to_dict,
    readonly_adapter_output_to_dict,
    validate_readonly_adapter_input,
)


class TestBuildSample:
    def test_valid_summary(self):
        inp = build_readonly_adapter_input_sample("valid_summary")
        assert inp.adapter_id == "adapter-001"
        assert inp.mode == "dry-run"
        assert len(inp.symbols) == 2

    def test_missing_adapter(self):
        inp = build_readonly_adapter_input_sample("missing_adapter")
        assert inp.adapter_id == ""

    def test_invalid_mode(self):
        inp = build_readonly_adapter_input_sample("invalid_mode")
        assert inp.mode == "forbidden-mode"

    def test_empty_symbols(self):
        inp = build_readonly_adapter_input_sample("empty_symbols")
        assert inp.symbols == []

    def test_unknown_kind_raises(self):
        with pytest.raises(ValueError, match="Unknown sample kind"):
            build_readonly_adapter_input_sample("nope")


class TestValidate:
    def test_valid_input_ok(self):
        inp = build_readonly_adapter_input_sample("valid_summary")
        assert validate_readonly_adapter_input(inp) is True

    def test_missing_adapter_fails(self):
        inp = build_readonly_adapter_input_sample("missing_adapter")
        assert validate_readonly_adapter_input(inp) is False

    def test_invalid_mode_fails(self):
        inp = build_readonly_adapter_input_sample("invalid_mode")
        assert validate_readonly_adapter_input(inp) is False

    def test_empty_symbols_fails(self):
        inp = build_readonly_adapter_input_sample("empty_symbols")
        assert validate_readonly_adapter_input(inp) is False


class TestSerialize:
    def test_input_to_dict_roundtrip(self):
        inp = build_readonly_adapter_input_sample("valid_summary")
        d = readonly_adapter_input_to_dict(inp)
        assert d["adapter_id"] == "adapter-001"
        assert d["symbols"] == ["BTCUSDT", "ETHUSDT"]
        assert isinstance(d["metadata"], dict)

    def test_output_to_dict(self):
        out = RuntimeGovernanceReadOnlyAdapterOutput(
            ok=True,
            view_name="summary",
            sanitized_payload={"net_exposure": 0.0},
            failure_codes=[],
        )
        d = readonly_adapter_output_to_dict(out)
        assert d["ok"] is True
        assert d["failure_codes"] == []
        assert d["notes"] == []


class TestDeterminism:
    def test_output_deterministic(self):
        out = RuntimeGovernanceReadOnlyAdapterOutput(
            ok=True,
            view_name="summary",
            sanitized_payload={"x": 1},
            failure_codes=[],
            notes=["n1"],
        )
        a = readonly_adapter_output_to_dict(out)
        b = readonly_adapter_output_to_dict(out)
        assert a == b

    def test_input_deterministic(self):
        inp = build_readonly_adapter_input_sample("valid_summary")
        a = readonly_adapter_input_to_dict(inp)
        b = readonly_adapter_input_to_dict(inp)
        assert a == b


class TestNoIO:
    """Contract tests are pure — no network, no filesystem."""

    def test_validate_is_pure(self):
        inp = build_readonly_adapter_input_sample("valid_summary")
        r1 = validate_readonly_adapter_input(inp)
        r2 = validate_readonly_adapter_input(inp)
        assert r1 == r2 is True

    def test_frozen_input(self):
        inp = build_readonly_adapter_input_sample("valid_summary")
        with pytest.raises(AttributeError):
            inp.adapter_id = "changed"

    def test_frozen_output(self):
        out = RuntimeGovernanceReadOnlyAdapterOutput(
            ok=True,
            view_name="summary",
            sanitized_payload={},
            failure_codes=[],
        )
        with pytest.raises(AttributeError):
            out.ok = False
