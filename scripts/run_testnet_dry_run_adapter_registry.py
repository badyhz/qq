#!/usr/bin/env python3
"""T33001 — Generate Testnet Dry-run Adapter Registry reports and data."""
from __future__ import annotations

import sys
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core.testnet_dry_run_adapter_registry import (
    RELEASE_HOLD_REQUIRED_TDR,
    build_adapter_registry,
    compute_registry_hash,
    render_registry_markdown,
    write_json,
    write_manifest,
    write_markdown,
)

REPORTS_DIR = ROOT / "reports"
DATA_DIR = ROOT / "data" / "testnet_dry_run_adapters"


def main() -> None:
    entries = build_adapter_registry(release_hold=RELEASE_HOLD_REQUIRED_TDR)
    reg_hash = compute_registry_hash(entries)

    write_json(entries, DATA_DIR / "registry.jsonl")
    write_manifest(entries, DATA_DIR / "manifest.json", RELEASE_HOLD_REQUIRED_TDR)
    write_markdown(render_registry_markdown(entries), REPORTS_DIR / "testnet_dry_run_adapter_registry.md")

    print(f"Dry-run adapters: {len(entries)} scripts, hash={reg_hash[:16]}...")
    print(f"Reports written to {REPORTS_DIR}/")
    print(f"Data written to {DATA_DIR}/")


if __name__ == "__main__":
    main()
