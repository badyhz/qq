#!/usr/bin/env python3
"""T25001-T25002 — Generate Dangerous Runtime Isolation and Archive Plan reports."""
from __future__ import annotations

import sys
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core.dangerous_runtime_isolator import (
    RELEASE_HOLD_REQUIRED_ISO,
    build_deny_list,
    compute_deny_list_hash,
    render_deny_list_markdown,
    render_isolation_manifest_markdown,
    write_json as write_deny_json,
    write_manifest as write_deny_manifest,
    write_markdown,
)
from core.safe_archive_planner import (
    RELEASE_HOLD_REQUIRED_ARC,
    build_archive_plan,
    compute_archive_hash,
    render_archive_plan_markdown,
    write_json as write_archive_json,
    write_manifest as write_archive_manifest,
    write_markdown as write_archive_markdown,
)

REPORTS_DIR = ROOT / "reports"
DATA_DIR = ROOT / "data"


def main() -> None:
    # Deny list
    entries = build_deny_list(release_hold=RELEASE_HOLD_REQUIRED_ISO)
    deny_hash = compute_deny_list_hash(entries)
    write_deny_json(entries, DATA_DIR / "dangerous_runtime" / "deny_list.jsonl")
    write_deny_manifest(entries, DATA_DIR / "dangerous_runtime" / "manifest.json", RELEASE_HOLD_REQUIRED_ISO)
    write_markdown(render_deny_list_markdown(entries), REPORTS_DIR / "dangerous_runtime_deny_list.md")
    write_markdown(render_isolation_manifest_markdown(entries), REPORTS_DIR / "dangerous_runtime_isolation_manifest.md")
    print(f"Deny list: {len(entries)} files isolated, hash={deny_hash[:16]}...")

    # Archive plan
    actions = build_archive_plan(release_hold=RELEASE_HOLD_REQUIRED_ARC)
    arc_hash = compute_archive_hash(actions)
    write_archive_json(actions, DATA_DIR / "safe_archive" / "archive_plan.jsonl")
    write_archive_manifest(actions, DATA_DIR / "safe_archive" / "manifest.json", RELEASE_HOLD_REQUIRED_ARC)
    write_archive_markdown(render_archive_plan_markdown(actions), REPORTS_DIR / "safe_archive_plan.md")
    print(f"Archive plan: {len(actions)} candidates, hash={arc_hash[:16]}...")

    print(f"Reports written to {REPORTS_DIR}/")
    print(f"Data written to {DATA_DIR}/")


if __name__ == "__main__":
    main()
