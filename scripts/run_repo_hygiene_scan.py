#!/usr/bin/env python3
"""T45001 — Generate Repo Hygiene reports and data."""
from __future__ import annotations

import sys
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core.repo_hygiene_scanner import (
    RELEASE_HOLD_REQUIRED_RHS,
    build_pre_commit_config,
    compute_config_hash,
    render_pre_commit_config_markdown,
    render_hygiene_report_markdown,
    write_json,
    write_manifest,
    write_markdown,
)

REPORTS_DIR = ROOT / "reports"
DATA_DIR = ROOT / "data" / "repo_hygiene"


def main() -> None:
    config = build_pre_commit_config()
    config_hash = compute_config_hash(config)

    write_json(config, DATA_DIR / "pre_commit_config.json")
    write_manifest(config, DATA_DIR / "manifest.json", RELEASE_HOLD_REQUIRED_RHS)
    write_markdown(render_pre_commit_config_markdown(config), REPORTS_DIR / "pre_commit_hook_config.md")
    write_markdown(render_hygiene_report_markdown(), REPORTS_DIR / "repo_hygiene_report.md")

    print(f"Hygiene: {len(config.checks)} checks, hash={config_hash[:16]}...")
    print(f"Reports written to {REPORTS_DIR}/")
    print(f"Data written to {DATA_DIR}/")


if __name__ == "__main__":
    main()
