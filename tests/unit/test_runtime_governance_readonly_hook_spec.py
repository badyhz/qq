import pytest
from core.runtime_governance_readonly_hook_spec import (
    build_runtime_governance_readonly_hook_spec,
    readonly_hook_spec_to_dict,
    readonly_hook_spec_to_markdown,
    FORBIDDEN_SIDE_EFFECTS,
)

EXPECTED_FORBIDDEN = [
    "order placement",
    "account mutation",
    "credential access",
    "network call",
    "file write",
    "planner action",
]

LIVE_ACTION_WORDS = [
    "submit", "execute", "place order", "send order",
    "buy", "sell", "cancel", "modify", "transfer",
]


class TestForbiddenSideEffectsPresent:
    def test_all_six_forbidden_effects(self):
        spec = build_runtime_governance_readonly_hook_spec()
        assert spec.forbidden_side_effects == EXPECTED_FORBIDDEN

    def test_module_constant_matches(self):
        assert FORBIDDEN_SIDE_EFFECTS == EXPECTED_FORBIDDEN

    def test_count(self):
        spec = build_runtime_governance_readonly_hook_spec()
        assert len(spec.forbidden_side_effects) == 6


class TestNoLiveActionLanguage:
    def test_allowed_outputs_clean(self):
        spec = build_runtime_governance_readonly_hook_spec()
        for output in spec.allowed_outputs:
            lower = output.lower()
            for word in LIVE_ACTION_WORDS:
                assert word not in lower, (
                    f"Live/action word '{word}' found in allowed output: {output}"
                )

    def test_allowed_outputs_read_only(self):
        spec = build_runtime_governance_readonly_hook_spec()
        d = readonly_hook_spec_to_dict(spec)
        for output in d["allowed_outputs"]:
            lower = output.lower()
            for word in LIVE_ACTION_WORDS:
                assert word not in lower


class TestDeterministicDict:
    def test_deterministic(self):
        spec = build_runtime_governance_readonly_hook_spec()
        d1 = readonly_hook_spec_to_dict(spec)
        d2 = readonly_hook_spec_to_dict(spec)
        assert d1 == d2

    def test_keys(self):
        spec = build_runtime_governance_readonly_hook_spec()
        d = readonly_hook_spec_to_dict(spec)
        expected_keys = {
            "hook_id", "allowed_inputs", "forbidden_inputs",
            "allowed_outputs", "forbidden_side_effects",
            "required_guards", "status", "notes",
        }
        assert set(d.keys()) == expected_keys


class TestDeterministicMarkdown:
    def test_deterministic(self):
        spec = build_runtime_governance_readonly_hook_spec()
        m1 = readonly_hook_spec_to_markdown(spec)
        m2 = readonly_hook_spec_to_markdown(spec)
        assert m1 == m2

    def test_contains_hook_id(self):
        spec = build_runtime_governance_readonly_hook_spec()
        md = readonly_hook_spec_to_markdown(spec)
        assert spec.hook_id in md

    def test_contains_forbidden_effects(self):
        spec = build_runtime_governance_readonly_hook_spec()
        md = readonly_hook_spec_to_markdown(spec)
        for effect in EXPECTED_FORBIDDEN:
            assert effect in md


class TestRepeatedCallsIdentical:
    def test_builder_deterministic(self):
        s1 = build_runtime_governance_readonly_hook_spec()
        s2 = build_runtime_governance_readonly_hook_spec()
        assert s1 == s2

    def test_frozen(self):
        spec = build_runtime_governance_readonly_hook_spec()
        with pytest.raises(AttributeError):
            spec.hook_id = "mutated"

    def test_dict_roundtrip_stable(self):
        spec = build_runtime_governance_readonly_hook_spec()
        d1 = readonly_hook_spec_to_dict(spec)
        d2 = readonly_hook_spec_to_dict(spec)
        assert d1 == d2
        assert d1["hook_id"] == "runtime_governance_readonly_v1"
        assert d1["status"] == "defined"
