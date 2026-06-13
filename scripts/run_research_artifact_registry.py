#!/usr/bin/env python3
"""T27001 — Generate Research Artifact Registry reports and data."""
from __future__ import annotations

import sys
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core.research_artifact_registry import (
    RELEASE_HOLD_REQUIRED_REG,
    build_artifact_registry,
    compute_registry_hash,
    render_registry_markdown,
    render_integration_matrix_markdown,
    write_json,
    write_manifest,
    write_markdown,
)

REPORTS_DIR = ROOT / "reports"
DATA_DIR = ROOT / "data" / "research_artifacts"


def main() -> None:
    artifacts = build_artifact_registry(release_hold=RELEASE_HOLD_REQUIRED_REG)
    reg_hash = compute_registry_hash(artifacts)

    write_json(artifacts, DATA_DIR / "registry.jsonl")
    write_manifest(artifacts, DATA_DIR / "manifest.json", RELEASE_HOLD_REQUIRED_REG)
    write_markdown(render_registry_markdown(artifacts), REPORTS_DIR / "research_artifact_registry.md")
    write_markdown(render_integration_matrix_markdown(artifacts), REPORTS_DIR / "research_artifact_integration_matrix.md")

    print(f"Registry: {len(artifacts)} artifacts, hash={reg_hash[:16]}...")
    print(f"Reports written to {REPORTS_DIR}/")
    print(f"Data written to {DATA_DIR}/")


if __name__ == "__main__":
    main()
