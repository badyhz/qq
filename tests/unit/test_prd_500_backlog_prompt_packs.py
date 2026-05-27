"""Tests for T911 — prd_500_backlog_prompt_packs."""

import pytest

from core.prd_backlog_schema import PrdBacklog, PrdBacklogItem
from core.prd_500_backlog_prompt_packs import (
    DEFAULT_REQUIRED_DOCS,
    SAFETY_WARNINGS,
    build_prd_500_prompt_packs,
    prompt_packs_to_dict,
    prompt_packs_to_markdown,
    summarize_prompt_packs,
)


def _make_item(idx: int) -> PrdBacklogItem:
    return PrdBacklogItem(
        task_id=f"T{idx:04d}",
        title=f"task-{idx}",
        milestone_id="M1",
        wave_id="W1",
        batch_id="B1",
        risk_level="low",
        status="planned",
        dependencies=[],
        allowed_file_patterns=[],
        forbidden_file_patterns=[],
        acceptance_command_ids=[],
        notes=[],
    )


def _make_backlog(n: int) -> PrdBacklog:
    return PrdBacklog(
        backlog_id="BL-TEST",
        items=[_make_item(i) for i in range(1, n + 1)],
        total_expected_tasks=n,
        status="active",
        notes=[],
    )


class TestPromptPacks:
    def test_packs_generated(self):
        backlog = _make_backlog(100)
        packs = build_prd_500_prompt_packs(backlog)
        assert len(packs) == 4  # 100 / 25 = 4
        assert packs[0].task_range == "T0001..T0025"
        assert packs[1].task_range == "T0026..T0050"
        assert packs[2].task_range == "T0051..T0075"
        assert packs[3].task_range == "T0076..T0100"

    def test_every_pack_has_hard_stop(self):
        backlog = _make_backlog(55)
        packs = build_prd_500_prompt_packs(backlog)
        for p in packs:
            assert p.hard_stop_task_id
            assert p.hard_stop_task_id in p.prompt_text
            assert "Hard stop after" in p.prompt_text

    def test_safety_warnings_present(self):
        backlog = _make_backlog(30)
        packs = build_prd_500_prompt_packs(backlog)
        for p in packs:
            assert p.safety_warnings == tuple(SAFETY_WARNINGS)
            for w in SAFETY_WARNINGS:
                assert w in p.safety_warnings
        # Also check summary
        summary = summarize_prompt_packs(packs)
        assert len(summary["safety_warnings"]) == len(SAFETY_WARNINGS)

    def test_deterministic(self):
        backlog = _make_backlog(200)
        run1 = build_prd_500_prompt_packs(backlog)
        run2 = build_prd_500_prompt_packs(backlog)
        assert len(run1) == len(run2)
        for a, b in zip(run1, run2):
            assert a.pack_id == b.pack_id
            assert a.prompt_text == b.prompt_text
            assert a.task_range == b.task_range
            assert a.hard_stop_task_id == b.hard_stop_task_id

    def test_serializers(self):
        backlog = _make_backlog(10)
        packs = build_prd_500_prompt_packs(backlog)
        d = prompt_packs_to_dict(packs[0])
        assert d["pack_id"] == packs[0].pack_id
        md = prompt_packs_to_markdown(packs[0])
        assert packs[0].pack_id in md

    def test_required_docs_default(self):
        backlog = _make_backlog(5)
        packs = build_prd_500_prompt_packs(backlog)
        for p in packs:
            assert p.required_docs == tuple(DEFAULT_REQUIRED_DOCS)
            for d in DEFAULT_REQUIRED_DOCS:
                assert d in p.prompt_text

    def test_custom_required_docs(self):
        backlog = _make_backlog(5)
        custom = ["docs/custom.md"]
        packs = build_prd_500_prompt_packs(backlog, required_docs=custom)
        for p in packs:
            assert p.required_docs == tuple(custom)
            assert "docs/custom.md" in p.prompt_text
