"""Tests for read-only hook contract — pure pytest, no I/O."""
import pytest

from core.read_only_hook_contract import (
    VALID_OPERATION_KINDS,
    VALID_RESULT_STATUSES,
    ReadOnlyHookInput,
    ReadOnlyHookOutput,
    build_read_only_hook_input,
    build_read_only_hook_output,
    hook_input_to_dict,
    hook_output_to_dict,
)


class TestHookInput:
    def test_build_input(self):
        inp = build_read_only_hook_input(
            hook_id="h1",
            operation_kind="query",
            payload={"key": "val"},
            permission_flags=["read"],
            context={"scope": "test"},
        )
        assert isinstance(inp, ReadOnlyHookInput)
        assert inp.hook_id == "h1"
        assert inp.operation_kind == "query"
        assert inp.payload == {"key": "val"}
        assert inp.permission_flags == ["read"]
        assert inp.context == {"scope": "test"}

    def test_frozen(self):
        inp = build_read_only_hook_input("h1", "query", {}, [], {})
        with pytest.raises(Exception):
            inp.hook_id = "changed"

    def test_to_dict(self):
        inp = build_read_only_hook_input(
            "h1", "inspect", {"a": 1}, ["read"], {"x": 2}
        )
        d = hook_input_to_dict(inp)
        assert d == {
            "hook_id": "h1",
            "operation_kind": "inspect",
            "payload": {"a": 1},
            "permission_flags": ["read"],
            "context": {"x": 2},
        }
        # must be a plain dict copy
        d["hook_id"] = "changed"
        assert inp.hook_id == "h1"


class TestHookOutput:
    def test_build_output(self):
        out = build_read_only_hook_output(
            hook_id="h1",
            result_status="success",
            sanitized_output={"ok": True},
            evidence_record_id="ev_01",
            invariant_results=["no_mutation"],
            side_effects_declared=[],
        )
        assert isinstance(out, ReadOnlyHookOutput)
        assert out.result_status == "success"
        assert out.side_effects_declared == []

    def test_side_effects_must_be_empty(self):
        with pytest.raises(ValueError, match="empty side_effects"):
            build_read_only_hook_output(
                hook_id="h1",
                result_status="success",
                sanitized_output={},
                evidence_record_id="ev_01",
                invariant_results=[],
                side_effects_declared=["write_order"],
            )

    def test_to_dict(self):
        out = build_read_only_hook_output(
            "h1", "denied", {"r": 1}, "ev_02", ["no_network"], []
        )
        d = hook_output_to_dict(out)
        assert d == {
            "hook_id": "h1",
            "result_status": "denied",
            "sanitized_output": {"r": 1},
            "evidence_record_id": "ev_02",
            "invariant_results": ["no_network"],
            "side_effects_declared": [],
        }
        d["hook_id"] = "changed"
        assert out.hook_id == "h1"
