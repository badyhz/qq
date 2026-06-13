#!/usr/bin/env python3
"""T47001 — Generate Final System Audit reports and data."""
from __future__ import annotations

import sys
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core.final_system_audit import (
    RELEASE_HOLD_REQUIRED_FSA,
    build_module_audit,
    build_system_audit,
    compute_audit_hash,
    render_audit_report_markdown,
    render_conclusions_markdown,
    write_json,
    write_manifest,
    write_markdown,
)

REPORTS_DIR = ROOT / "reports"
DATA_DIR = ROOT / "data" / "final_audit"


def main() -> None:
    entries = build_module_audit()
    audit = build_system_audit(release_hold=RELEASE_HOLD_REQUIRED_FSA)
    audit_hash = compute_audit_hash(audit)

    write_json([e.to_dict() for e in entries], DATA_DIR / "module_audit.jsonl")
    write_json(audit.to_dict(), DATA_DIR / "system_audit.json")
    write_manifest(audit, DATA_DIR / "manifest.json", RELEASE_HOLD_REQUIRED_FSA)
    write_markdown(render_audit_report_markdown(audit, entries), REPORTS_DIR / "final_system_audit.md")
    write_markdown(render_conclusions_markdown(), REPORTS_DIR / "one_month_conclusions.md")

    print(f"Audit: {audit.total_modules} modules, {audit.completed_modules} complete")
    print(f"All complete: {audit.all_complete}")
    print(f"Hash={audit_hash[:16]}...")
    print(f"Reports written to {REPORTS_DIR}/")
    print(f"Data written to {DATA_DIR}/")


if __name__ == "__main__":
    main()
