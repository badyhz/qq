"""Acceptance tests for PRD backlog renderers.

T890-T894. Pure pytest. No I/O. No network.
"""

import json

import pytest

from core.prd_backlog_schema import PrdBacklog, build_backlog_item


# --- Shared fixtures ---


@pytest.fixture
def items():
    return [
        build_backlog_item(
            "T1", "Task 1", "M1", "W0", "B0", "LOW", "COMPLETED",
            [], ["core/*.py"], [], ["pytest"], ["note1"],
        ),
        build_backlog_item(
            "T2", "Task 2", "M1", "W0", "B0", "MEDIUM", "NOT_STARTED",
            ["T1"], ["core/*.py"], [], ["pytest"], ["note2"],
        ),
        build_backlog_item(
            "T3", "Task 3", "M2", "W0", "B0", "HIGH", "NOT_STARTED",
            ["T1"], ["core/*.py"], [], ["pytest"], ["note3"],
        ),
    ]


@pytest.fixture
def backlog(items):
    return PrdBacklog(
        backlog_id="TEST",
        items=items,
        total_expected_tasks=3,
        status="NOT_STARTED",
        notes=[],
    )


# --- Markdown Renderer ---


class TestMarkdownRenderer:
    def test_import(self):
        from core.prd_backlog_markdown_renderer import (  # noqa: F401
            render_backlog_full_markdown,
            render_backlog_summary_markdown,
        )

    def test_full_render_deterministic(self, backlog):
        from core.prd_backlog_markdown_renderer import render_backlog_full_markdown
        a = render_backlog_full_markdown(backlog)
        b = render_backlog_full_markdown(backlog)
        assert a == b

    def test_full_render_contains_sections(self, backlog):
        from core.prd_backlog_markdown_renderer import render_backlog_full_markdown
        md = render_backlog_full_markdown(backlog)
        assert "Backlog" in md
        assert "TEST" in md
        assert "T1" in md
        assert "T2" in md
        assert "T3" in md

    def test_summary_render_shorter_than_full(self, backlog):
        from core.prd_backlog_markdown_renderer import (
            render_backlog_full_markdown,
            render_backlog_summary_markdown,
        )
        full = render_backlog_full_markdown(backlog)
        summary = render_backlog_summary_markdown(backlog)
        assert len(summary) < len(full)


# --- JSON Serializer ---


class TestJsonSerializer:
    def test_import(self):
        from core.prd_backlog_json_serializer import (  # noqa: F401
            serialize_backlog_to_stable_dict,
            serialize_backlog_item_to_stable_dict,
            validate_serialization_roundtrip,
        )

    def test_stable_dict_deterministic(self, backlog):
        from core.prd_backlog_json_serializer import serialize_backlog_to_stable_dict
        a = serialize_backlog_to_stable_dict(backlog)
        b = serialize_backlog_to_stable_dict(backlog)
        assert a == b

    def test_roundtrip_valid(self, backlog):
        from core.prd_backlog_json_serializer import validate_serialization_roundtrip
        assert validate_serialization_roundtrip(backlog) is True

    def test_stable_dict_json_compatible(self, backlog):
        from core.prd_backlog_json_serializer import serialize_backlog_to_stable_dict
        d = serialize_backlog_to_stable_dict(backlog)
        s = json.dumps(d)
        assert isinstance(s, str)
        assert len(s) > 0

    def test_item_dict_has_sorted_keys(self, items):
        from core.prd_backlog_json_serializer import serialize_backlog_item_to_stable_dict
        for item in items:
            d = serialize_backlog_item_to_stable_dict(item)
            keys = list(d.keys())
            assert keys == sorted(keys)


# --- Risk Heatmap ---


class TestRiskHeatmap:
    def test_import(self):
        from core.prd_backlog_risk_heatmap_packet import (  # noqa: F401
            generate_risk_heatmap,
            risk_heatmap_to_dict,
            risk_heatmap_to_markdown,
        )

    def test_heatmap_deterministic(self, items):
        from core.prd_backlog_risk_heatmap_packet import (
            generate_risk_heatmap,
            risk_heatmap_to_dict,
        )
        a = risk_heatmap_to_dict(generate_risk_heatmap(items))
        b = risk_heatmap_to_dict(generate_risk_heatmap(items))
        assert a == b

    def test_heatmap_has_cells(self, items):
        from core.prd_backlog_risk_heatmap_packet import generate_risk_heatmap
        packet = generate_risk_heatmap(items)
        assert len(packet.cells) > 0

    def test_heatmap_markdown(self, items):
        from core.prd_backlog_risk_heatmap_packet import (
            generate_risk_heatmap,
            risk_heatmap_to_markdown,
        )
        md = risk_heatmap_to_markdown(generate_risk_heatmap(items))
        assert "LOW" in md
        assert "MEDIUM" in md
        assert "HIGH" in md


# --- Execution Prompt Pack ---


class TestExecutionPromptPack:
    def test_import(self):
        from core.prd_execution_prompt_pack_generator import (  # noqa: F401
            generate_all_prompt_packs,
            prompt_pack_to_dict,
            prompt_pack_to_markdown,
        )

    def test_packs_generated(self, items):
        from core.prd_execution_prompt_pack_generator import generate_all_prompt_packs
        packs = generate_all_prompt_packs(items)
        assert len(packs) > 0

    def test_pack_deterministic(self, items):
        from core.prd_execution_prompt_pack_generator import (
            generate_all_prompt_packs,
            prompt_pack_to_dict,
        )
        a = [prompt_pack_to_dict(p) for p in generate_all_prompt_packs(items)]
        b = [prompt_pack_to_dict(p) for p in generate_all_prompt_packs(items)]
        assert a == b

    def test_prompt_contains_task_info(self, items):
        from core.prd_execution_prompt_pack_generator import (
            generate_all_prompt_packs,
            prompt_pack_to_markdown,
        )
        for pack in generate_all_prompt_packs(items):
            md = prompt_pack_to_markdown(pack)
            for prompt in pack.prompts:
                assert prompt.task_id in md


# --- Cross-cutting determinism ---


class TestDeterminism:
    def test_all_outputs_deterministic(self, backlog, items):
        from core.prd_backlog_markdown_renderer import render_backlog_full_markdown
        from core.prd_backlog_json_serializer import serialize_backlog_to_stable_dict
        from core.prd_backlog_risk_heatmap_packet import (
            generate_risk_heatmap,
            risk_heatmap_to_dict,
        )
        from core.prd_execution_prompt_pack_generator import (
            generate_all_prompt_packs,
            prompt_pack_to_dict,
        )

        # Markdown
        assert render_backlog_full_markdown(backlog) == render_backlog_full_markdown(backlog)
        # JSON
        assert serialize_backlog_to_stable_dict(backlog) == serialize_backlog_to_stable_dict(backlog)
        # Heatmap
        assert risk_heatmap_to_dict(generate_risk_heatmap(items)) == risk_heatmap_to_dict(generate_risk_heatmap(items))
        # Prompt packs
        packs1 = [prompt_pack_to_dict(p) for p in generate_all_prompt_packs(items)]
        packs2 = [prompt_pack_to_dict(p) for p in generate_all_prompt_packs(items)]
        assert packs1 == packs2
