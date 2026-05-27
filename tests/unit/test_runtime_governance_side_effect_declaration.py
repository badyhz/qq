"""Tests for T830 — side-effect declarations."""

import pytest

from core.runtime_governance_side_effect_declaration import (
    RuntimeGovernanceSideEffectDeclaration,
    build_runtime_governance_side_effect_declarations,
    side_effect_declarations_to_dict,
    side_effect_declarations_to_markdown,
    summarize_side_effect_declarations,
)


class TestBuildDeclarations:
    def test_default_all_pass(self):
        decls = build_runtime_governance_side_effect_declarations()
        for d in decls:
            assert d.verdict == "PASS"
            assert d.places_orders is False
            assert d.mutates_account is False
            assert d.accesses_secrets is False

    def test_four_components(self):
        decls = build_runtime_governance_side_effect_declarations()
        assert len(decls) == 4

    def test_component_names_contain_t826_t829(self):
        decls = build_runtime_governance_side_effect_declarations()
        names = [d.component for d in decls]
        assert any("T826" in n for n in names)
        assert any("T827" in n for n in names)
        assert any("T828" in n for n in names)
        assert any("T829" in n for n in names)

    def test_forced_dangerous_blocked(self):
        dangerous = RuntimeGovernanceSideEffectDeclaration(
            component="DANGER: test",
            reads_memory=True,
            writes_memory=False,
            reads_files=False,
            writes_files=False,
            calls_network=False,
            places_orders=True,
            mutates_account=False,
            accesses_secrets=False,
            verdict="BLOCKED",
        )
        assert dangerous.verdict == "BLOCKED"
        assert dangerous.places_orders is True


class TestSerialization:
    def test_to_dict_returns_list_of_dicts(self):
        decls = build_runtime_governance_side_effect_declarations()
        dicts = side_effect_declarations_to_dict(decls)
        assert len(dicts) == 4
        for d in dicts:
            assert isinstance(d, dict)
            assert "component" in d
            assert "verdict" in d

    def test_to_dict_roundtrip_fields(self):
        decls = build_runtime_governance_side_effect_declarations()
        dicts = side_effect_declarations_to_dict(decls)
        for orig, d in zip(decls, dicts):
            assert d["component"] == orig.component
            assert d["reads_memory"] == orig.reads_memory
            assert d["verdict"] == orig.verdict


class TestMarkdown:
    def test_markdown_contains_header(self):
        decls = build_runtime_governance_side_effect_declarations()
        md = side_effect_declarations_to_markdown(decls)
        assert "Side-Effect Declarations" in md

    def test_markdown_contains_all_components(self):
        decls = build_runtime_governance_side_effect_declarations()
        md = side_effect_declarations_to_markdown(decls)
        for d in decls:
            assert d.component in md

    def test_markdown_deterministic(self):
        decls = build_runtime_governance_side_effect_declarations()
        md1 = side_effect_declarations_to_markdown(decls)
        md2 = side_effect_declarations_to_markdown(decls)
        assert md1 == md2


class TestSummarize:
    def test_all_pass_summary(self):
        decls = build_runtime_governance_side_effect_declarations()
        summary = summarize_side_effect_declarations(decls)
        assert summary["total_components"] == 4
        assert summary["pass_count"] == 4
        assert summary["blocked_count"] == 0
        assert summary["all_pass"] is True

    def test_blocked_summary(self):
        decls = build_runtime_governance_side_effect_declarations()
        blocked = [
            RuntimeGovernanceSideEffectDeclaration(
                component="DANGER",
                reads_memory=True,
                writes_memory=False,
                reads_files=False,
                writes_files=False,
                calls_network=False,
                places_orders=True,
                mutates_account=False,
                accesses_secrets=False,
                verdict="BLOCKED",
            )
        ]
        summary = summarize_side_effect_declarations(decls + blocked)
        assert summary["total_components"] == 5
        assert summary["blocked_count"] == 1
        assert summary["all_pass"] is False


class TestDeterminism:
    def test_build_deterministic(self):
        a = build_runtime_governance_side_effect_declarations()
        b = build_runtime_governance_side_effect_declarations()
        assert a == b

    def test_dataclass_frozen(self):
        decls = build_runtime_governance_side_effect_declarations()
        with pytest.raises(AttributeError):
            decls[0].verdict = "NOPE"
