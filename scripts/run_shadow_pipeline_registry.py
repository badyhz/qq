#!/usr/bin/env python3
"""T30001 — Generate Shadow Pipeline Registry reports and data."""
from __future__ import annotations

import sys
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core.shadow_pipeline_registry import (
    RELEASE_HOLD_REQUIRED_SPR,
    build_shadow_pipeline_registry,
    compute_registry_hash,
    render_registry_markdown,
    render_pipeline_flow_markdown,
    write_json,
    write_manifest,
    write_markdown,
)

REPORTS_DIR = ROOT / "reports"
DATA_DIR = ROOT / "data" / "shadow_pipeline"


def main() -> None:
    entries = build_shadow_pipeline_registry(release_hold=RELEASE_HOLD_REQUIRED_SPR)
    reg_hash = compute_registry_hash(entries)

    write_json(entries, DATA_DIR / "registry.jsonl")
    write_manifest(entries, DATA_DIR / "manifest.json", RELEASE_HOLD_REQUIRED_SPR)
    write_markdown(render_registry_markdown(entries), REPORTS_DIR / "shadow_pipeline_registry.md")
    write_markdown(render_pipeline_flow_markdown(entries), REPORTS_DIR / "shadow_pipeline_flow.md")

    print(f"Shadow pipeline: {len(entries)} scripts, hash={reg_hash[:16]}...")
    print(f"Reports written to {REPORTS_DIR}/")
    print(f"Data written to {DATA_DIR}/")


if __name__ == "__main__":
    main()
