from __future__ import annotations

import pytest

from core.dirty_workspace_governance import DirtyWorkspaceGovernance


class TestDirtyWorkspaceGovernance:
    def test_create(self) -> None:
        g = DirtyWorkspaceGovernance(
            policy_version="1.0",
            file_categories=("A", "B"),
            risk_levels=("HIGH", "LOW"),
            enforcement_mode="STRICT",
        )
        assert g.policy_version == "1.0"

    def test_frozen(self) -> None:
        g = DirtyWorkspaceGovernance(
            policy_version="1.0",
            file_categories=(),
            risk_levels=(),
            enforcement_mode="LENIENT",
        )
        with pytest.raises(AttributeError):
            g.policy_version = "2.0"  # type: ignore[misc]

    def test_policy_version(self) -> None:
        g = DirtyWorkspaceGovernance("2.1", (), (), "WARN")
        assert g.policy_version == "2.1"

    def test_enforcement_mode(self) -> None:
        for mode in ("STRICT", "LENIENT", "WARN", "NONE"):
            g = DirtyWorkspaceGovernance("1", (), (), mode)
            assert g.enforcement_mode == mode

    def test_describe_keys(self) -> None:
        g = DirtyWorkspaceGovernance("1.0", ("X",), ("HIGH",), "STRICT")
        d = g.describe()
        assert set(d.keys()) == {
            "policy_version",
            "file_categories",
            "risk_levels",
            "enforcement_mode",
        }
        assert d["file_categories"] == ("X",)

    def test_file_categories_tuple(self) -> None:
        cats = ("CREDENTIAL", "CONFIG", "SCRIPT")
        g = DirtyWorkspaceGovernance("1", cats, (), "STRICT")
        assert g.file_categories == cats
