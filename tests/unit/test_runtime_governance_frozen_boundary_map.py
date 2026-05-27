"""Tests for runtime_governance_frozen_boundary_map."""

import pytest

from core.runtime_governance_frozen_boundary_map import (
    RuntimeGovernanceFrozenBoundary,
    build_runtime_governance_frozen_boundary_map,
    frozen_boundary_map_to_dict,
    frozen_boundary_map_to_markdown,
)


class TestBuildMap:
    def test_returns_six_boundaries(self):
        boundaries = build_runtime_governance_frozen_boundary_map()
        assert len(boundaries) == 6

    def test_all_frozen(self):
        for b in build_runtime_governance_frozen_boundary_map():
            assert b.status == "frozen"

    def test_expected_ids(self):
        ids = {b.boundary_id for b in build_runtime_governance_frozen_boundary_map()}
        assert ids == {
            "live_trading",
            "submit_scripts",
            "secrets",
            "planner",
            "runtime_execution",
            "exchange_client",
        }

    def test_dataclass_is_frozen(self):
        boundaries = build_runtime_governance_frozen_boundary_map()
        with pytest.raises(AttributeError):
            boundaries[0].boundary_id = "mutated"


class TestToDict:
    def test_returns_list_of_dicts(self):
        result = frozen_boundary_map_to_dict(build_runtime_governance_frozen_boundary_map())
        assert isinstance(result, list)
        assert len(result) == 6
        for d in result:
            assert isinstance(d, dict)
            assert set(d.keys()) == {
                "boundary_id",
                "path_pattern",
                "reason",
                "allowed_action",
                "status",
            }

    def test_first_entry_values(self):
        result = frozen_boundary_map_to_dict(build_runtime_governance_frozen_boundary_map())
        assert result[0]["boundary_id"] == "live_trading"
        assert result[0]["path_pattern"] == "scripts/*live*"
        assert result[0]["status"] == "frozen"


class TestToMarkdown:
    def test_contains_header(self):
        md = frozen_boundary_map_to_markdown(build_runtime_governance_frozen_boundary_map())
        assert "boundary_id" in md
        assert "path_pattern" in md

    def test_contains_all_ids(self):
        md = frozen_boundary_map_to_markdown(build_runtime_governance_frozen_boundary_map())
        for bid in ["live_trading", "submit_scripts", "secrets", "planner", "runtime_execution", "exchange_client"]:
            assert bid in md

    def test_row_count(self):
        md = frozen_boundary_map_to_markdown(build_runtime_governance_frozen_boundary_map())
        lines = [l for l in md.strip().splitlines() if l.startswith("|")]
        # header + separator + 6 data rows = 8
        assert len(lines) == 8
