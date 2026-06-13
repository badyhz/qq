#!/usr/bin/env python3
"""T50001-T65000 — Actual Dry-run Runtime E2E Runner.

Runs the full integrated pipeline:
  research → shadow → testnet sim → alerts → feishu → operator → dashboard → report
"""
from __future__ import annotations

import sys
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.runtime_integrations.e2e.system_dry_run_e2e import run_e2e


def main() -> None:
    data_dir = ROOT / "data"
    reports_dir = ROOT / "reports"

    result = run_e2e(data_dir, reports_dir)

    print(f"E2E Run: {result['run_id']}")
    print(f"Status: {result['status']}")
    print(f"Steps: {len(result['steps_completed'])}")
    if result["errors"]:
        print(f"Errors: {len(result['errors'])}")
        for e in result["errors"]:
            print(f"  - {e}")
    print(f"Report: {reports_dir}/system_dry_run_e2e_report.md")
    print(f"Dashboard: {reports_dir}/operator_dashboard.html")


if __name__ == "__main__":
    main()
