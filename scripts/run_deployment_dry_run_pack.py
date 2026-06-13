#!/usr/bin/env python3
"""T42001 — Generate Deployment Dry-run Pack reports and data."""
from __future__ import annotations

import sys
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core.deployment_dry_run_pack import (
    RELEASE_HOLD_REQUIRED_DPK,
    build_deployment_steps,
    compute_pack_hash,
    render_deployment_checklist_markdown,
    render_deployment_manifest_markdown,
    write_json,
    write_manifest,
    write_markdown,
)

REPORTS_DIR = ROOT / "reports"
DATA_DIR = ROOT / "data" / "deployment_dry_run"


def main() -> None:
    steps = build_deployment_steps()
    pack_hash = compute_pack_hash(steps)

    write_json(steps, DATA_DIR / "deployment_steps.jsonl")
    write_manifest(steps, DATA_DIR / "manifest.json", RELEASE_HOLD_REQUIRED_DPK)
    write_markdown(render_deployment_checklist_markdown(steps), REPORTS_DIR / "deployment_checklist.md")
    write_markdown(render_deployment_manifest_markdown(steps), REPORTS_DIR / "deployment_manifest.md")

    print(f"Deployment pack: {len(steps)} steps, hash={pack_hash[:16]}...")
    print(f"Reports written to {REPORTS_DIR}/")
    print(f"Data written to {DATA_DIR}/")


if __name__ == "__main__":
    main()
