#!/usr/bin/env python3
"""T23001 — Generate Untracked Runtime Inventory reports and data."""
from __future__ import annotations

import sys
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core.untracked_runtime_inventory import (
    RELEASE_HOLD_REQUIRED,
    build_inventory,
    compute_inventory_hash,
    write_json,
    write_manifest,
    write_markdown,
    render_inventory_markdown,
    render_risk_matrix_markdown,
    render_human_review_queue_markdown,
    render_archive_candidates_markdown,
)

REPORTS_DIR = ROOT / "reports"
DATA_DIR = ROOT / "data" / "untracked_runtime"


def main() -> None:
    records = build_inventory(release_hold=RELEASE_HOLD_REQUIRED)
    inv_hash = compute_inventory_hash(records)

    # Reports
    write_markdown(render_inventory_markdown(records), REPORTS_DIR / "untracked_runtime_inventory.md")
    write_markdown(render_risk_matrix_markdown(records), REPORTS_DIR / "untracked_runtime_risk_matrix.md")
    write_markdown(render_human_review_queue_markdown(records), REPORTS_DIR / "untracked_runtime_human_review_queue.md")
    write_markdown(render_archive_candidates_markdown(records), REPORTS_DIR / "untracked_runtime_archive_candidates.md")

    # Data
    write_json(records, DATA_DIR / "inventory.jsonl")
    write_manifest(records, DATA_DIR / "manifest.json", RELEASE_HOLD_REQUIRED)

    print(f"Inventory: {len(records)} files, hash={inv_hash[:16]}...")
    print(f"Reports written to {REPORTS_DIR}/")
    print(f"Data written to {DATA_DIR}/")


if __name__ == "__main__":
    main()
