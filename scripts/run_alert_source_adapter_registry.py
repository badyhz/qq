#!/usr/bin/env python3
"""T36001 — Generate Alert Source Adapter Registry reports and data."""
from __future__ import annotations

import sys
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core.alert_source_adapter_registry import (
    RELEASE_HOLD_REQUIRED_ASR,
    build_adapter_registry,
    compute_registry_hash,
    render_registry_markdown,
    render_integration_matrix_markdown,
    write_json,
    write_manifest,
    write_markdown,
)

REPORTS_DIR = ROOT / "reports"
DATA_DIR = ROOT / "data" / "alert_source_adapters"


def main() -> None:
    adapters = build_adapter_registry(release_hold=RELEASE_HOLD_REQUIRED_ASR)
    reg_hash = compute_registry_hash(adapters)

    write_json(adapters, DATA_DIR / "registry.jsonl")
    write_manifest(adapters, DATA_DIR / "manifest.json", RELEASE_HOLD_REQUIRED_ASR)
    write_markdown(render_registry_markdown(adapters), REPORTS_DIR / "alert_source_adapter_registry.md")
    write_markdown(render_integration_matrix_markdown(adapters), REPORTS_DIR / "alert_source_integration_matrix.md")

    print(f"Alert source adapters: {len(adapters)} sources, hash={reg_hash[:16]}...")
    print(f"Reports written to {REPORTS_DIR}/")
    print(f"Data written to {DATA_DIR}/")


if __name__ == "__main__":
    main()
