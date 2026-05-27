#!/usr/bin/env python3
"""T1805 - Export Frozen Backlog Review JSON schemas.

CLI that writes schema JSON files to --output-dir. Exit 0 on success.
No network. No live. No submit. No exchange.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Ensure project root is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.frozen_backlog_schema_exporter import (
    export_audit_schema,
    export_diff_schema,
    export_report_schema,
    export_snapshot_schema,
    export_verdict_schema,
)

_SCHEMA_EXPORTS = {
    "report_schema.json": export_report_schema,
    "snapshot_schema.json": export_snapshot_schema,
    "diff_schema.json": export_diff_schema,
    "verdict_schema.json": export_verdict_schema,
    "audit_schema.json": export_audit_schema,
}


def main(argv: list[str] | None = None) -> int:
    """Export all schemas to output-dir. Returns exit code."""
    parser = argparse.ArgumentParser(
        description="Export frozen backlog review JSON schemas."
    )
    parser.add_argument(
        "--output-dir",
        required=True,
        help="Directory to write schema JSON files.",
    )
    args = parser.parse_args(argv)

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    for filename, export_fn in _SCHEMA_EXPORTS.items():
        schema = export_fn()
        out_path = output_dir / filename
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(schema, f, indent=2, sort_keys=True, ensure_ascii=False)
            f.write("\n")
        print(f"Wrote {out_path}")

    print(f"All {len(_SCHEMA_EXPORTS)} schemas exported to {output_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
