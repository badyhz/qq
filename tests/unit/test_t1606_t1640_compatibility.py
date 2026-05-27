"""T1610: Compatibility checks for T1606-T1640 frozen backlog snapshot system."""
from __future__ import annotations

import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


def test_snapshot_models_importable():
    from core.frozen_backlog_snapshot import FrozenBacklogSnapshot
    from core.frozen_backlog_snapshot_manager import create_snapshot, dict_to_snapshot, read_snapshot, snapshot_to_dict, write_snapshot
    from core.frozen_backlog_snapshot_renderer import render_snapshot_md
    assert FrozenBacklogSnapshot is not None
    assert callable(create_snapshot)


def test_22_frozen_files_still_untracked():
    result = subprocess.run(
        ["git", "ls-files", "--others", "--exclude-standard"],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
    )
    untracked = [l for l in result.stdout.strip().splitlines() if l]
    assert len(untracked) >= 22, f"Expected >=22 untracked files, got {len(untracked)}"


def test_release_hold_is_hold():
    """Verify release_hold invariant: hold_active must be True."""
    from core.prd_500_backlog_release_hold import build_prd_500_backlog_release_hold
    hold = build_prd_500_backlog_release_hold()
    assert hold.hold_active is True, "release_hold must be HOLD (hold_active=True)"
    assert hold.final_verdict == "HOLD", f"final_verdict is {hold.final_verdict}"


def test_snapshot_files_not_in_git_index():
    """New snapshot files should not be staged yet."""
    result = subprocess.run(
        ["git", "diff", "--cached", "--name-only"],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
    )
    staged = result.stdout.strip().splitlines()
    for f in [
        "core/frozen_backlog_snapshot.py",
        "core/frozen_backlog_snapshot_manager.py",
        "core/frozen_backlog_snapshot_renderer.py",
    ]:
        assert f not in staged, f"{f} should not be staged before explicit add"
