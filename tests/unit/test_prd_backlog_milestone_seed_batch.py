"""Batch tests for all 7 PRD backlog milestone seed modules.

T888. Pure pytest. No I/O. No network.
"""

from __future__ import annotations

import pytest

from core.prd_backlog_milestone1_seed import (
    build_milestone1_seed,
    milestone1_seed_to_dict,
    milestone1_seed_to_markdown,
)
from core.prd_backlog_milestone2_seed import (
    build_milestone2_seed,
    milestone2_seed_to_dict,
    milestone2_seed_to_markdown,
)
from core.prd_backlog_milestone3_seed import (
    build_milestone3_seed,
    milestone3_seed_to_dict,
    milestone3_seed_to_markdown,
)
from core.prd_backlog_milestone4_seed import (
    build_milestone4_seed,
    milestone4_seed_to_dict,
    milestone4_seed_to_markdown,
)
from core.prd_backlog_milestone5_seed import (
    build_milestone5_seed,
    milestone5_seed_to_dict,
    milestone5_seed_to_markdown,
)
from core.prd_backlog_milestone6_seed import (
    build_milestone6_seed,
    milestone6_seed_to_dict,
    milestone6_seed_to_markdown,
)
from core.prd_backlog_milestone7_seed import (
    build_milestone7_seed,
    milestone7_seed_to_dict,
    milestone7_seed_to_markdown,
)

# Registry of (factory, to_dict, to_markdown, expected_id, expected_count,
#              expected_status, allowed_risks)
_ALL_MILESTONES = [
    (build_milestone1_seed, milestone1_seed_to_dict, milestone1_seed_to_markdown,
     "M1", 23, "COMPLETED", {"LOW", "MEDIUM"}),
    (build_milestone2_seed, milestone2_seed_to_dict, milestone2_seed_to_markdown,
     "M2", 8, "COMPLETED", None),
    (build_milestone3_seed, milestone3_seed_to_dict, milestone3_seed_to_markdown,
     "M3", 8, "COMPLETED", None),
    (build_milestone4_seed, milestone4_seed_to_dict, milestone4_seed_to_markdown,
     "M4", 8, "NOT_STARTED", None),
    (build_milestone5_seed, milestone5_seed_to_dict, milestone5_seed_to_markdown,
     "M5", 8, "NOT_STARTED", {"MEDIUM"}),
    (build_milestone6_seed, milestone6_seed_to_dict, milestone6_seed_to_markdown,
     "M6", 8, "NOT_STARTED", {"HIGH"}),
    (build_milestone7_seed, milestone7_seed_to_dict, milestone7_seed_to_markdown,
     "M7", 8, "NOT_STARTED", {"HIGH"}),
]


# ---------------------------------------------------------------------------
# TestMilestoneSeedImports
# ---------------------------------------------------------------------------

class TestMilestoneSeedImports:
    def test_all_modules_import(self):
        import core.prd_backlog_milestone1_seed  # noqa: F401
        import core.prd_backlog_milestone2_seed  # noqa: F401
        import core.prd_backlog_milestone3_seed  # noqa: F401
        import core.prd_backlog_milestone4_seed  # noqa: F401
        import core.prd_backlog_milestone5_seed  # noqa: F401
        import core.prd_backlog_milestone6_seed  # noqa: F401
        import core.prd_backlog_milestone7_seed  # noqa: F401

    def test_all_factories_callable(self):
        factories = [
            build_milestone1_seed,
            build_milestone2_seed,
            build_milestone3_seed,
            build_milestone4_seed,
            build_milestone5_seed,
            build_milestone6_seed,
            build_milestone7_seed,
        ]
        for factory in factories:
            seed = factory()
            assert hasattr(seed, "milestone_id")
            assert hasattr(seed, "title")
            assert hasattr(seed, "task_items")
            assert hasattr(seed, "notes")


# ---------------------------------------------------------------------------
# TestMilestoneSeedStructure
# ---------------------------------------------------------------------------

class TestMilestoneSeedStructure:
    def test_m1_has_expected_tasks(self):
        seed = build_milestone1_seed()
        assert len(seed.task_items) == 23
        for t in seed.task_items:
            assert t["status"] == "COMPLETED"
            assert t["risk_level"] in {"LOW", "MEDIUM"}

    def test_m2_has_expected_tasks(self):
        seed = build_milestone2_seed()
        assert len(seed.task_items) == 8
        for t in seed.task_items:
            assert t["status"] == "COMPLETED"

    def test_m3_has_expected_tasks(self):
        seed = build_milestone3_seed()
        assert len(seed.task_items) == 8
        for t in seed.task_items:
            assert t["status"] == "COMPLETED"

    def test_m4_has_expected_tasks(self):
        seed = build_milestone4_seed()
        assert len(seed.task_items) == 8
        for t in seed.task_items:
            assert t["status"] == "NOT_STARTED"

    def test_m5_has_expected_tasks(self):
        seed = build_milestone5_seed()
        assert len(seed.task_items) == 8
        for t in seed.task_items:
            assert t["status"] == "NOT_STARTED"
            assert t["risk_level"] in {"MEDIUM"}

    def test_m6_has_expected_tasks(self):
        seed = build_milestone6_seed()
        assert len(seed.task_items) == 8
        for t in seed.task_items:
            assert t["status"] == "NOT_STARTED"
            assert t["risk_level"] in {"HIGH"}

    def test_m7_has_expected_tasks(self):
        seed = build_milestone7_seed()
        assert len(seed.task_items) == 8
        for t in seed.task_items:
            assert t["status"] == "NOT_STARTED"
            assert t["risk_level"] in {"HIGH"}


# ---------------------------------------------------------------------------
# TestMilestoneSeedSerializers
# ---------------------------------------------------------------------------

class TestMilestoneSeedSerializers:
    def test_all_to_dict_callable(self):
        for factory, to_dict, _, _, _, _, _ in _ALL_MILESTONES:
            seed = factory()
            result = to_dict(seed)
            assert isinstance(result, dict)

    def test_all_to_markdown_callable(self):
        for factory, _, to_markdown, mid, _, _, _ in _ALL_MILESTONES:
            seed = factory()
            result = to_markdown(seed)
            assert isinstance(result, str)
            assert "Milestone" in result or mid in result

    def test_dict_has_required_keys(self):
        for factory, to_dict, _, _, _, _, _ in _ALL_MILESTONES:
            seed = factory()
            d = to_dict(seed)
            assert "milestone_id" in d
            assert "title" in d
            assert "task_items" in d
            assert "notes" in d


# ---------------------------------------------------------------------------
# TestMilestoneSeedDeterminism
# ---------------------------------------------------------------------------

class TestMilestoneSeedDeterminism:
    def test_factory_produces_same_result_twice(self):
        for factory, to_dict, _, _, _, _, _ in _ALL_MILESTONES:
            a = to_dict(factory())
            b = to_dict(factory())
            assert a == b

    def test_to_dict_produces_same_result_twice(self):
        for factory, to_dict, _, _, _, _, _ in _ALL_MILESTONES:
            seed = factory()
            a = to_dict(seed)
            b = to_dict(seed)
            assert a == b


# ---------------------------------------------------------------------------
# TestMilestoneSeedNoLiveAuthorization
# ---------------------------------------------------------------------------

class TestMilestoneSeedNoLiveAuthorization:
    def test_no_task_authorizes_live(self):
        banned = {"authorized for live", "authorized for real order"}
        for factory, _, _, _, _, _, _ in _ALL_MILESTONES:
            seed = factory()
            for t in seed.task_items:
                haystack = (
                    (t.get("title", "") + " " + t.get("notes", ""))
                    .lower()
                )
                for phrase in banned:
                    assert phrase not in haystack, (
                        f"{seed.milestone_id}/{t.get('task_id')} "
                        f"contains banned phrase: {phrase!r}"
                    )
