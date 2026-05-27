#!/usr/bin/env python3
"""T1620 - Frozen Backlog Snapshot CLI.

Reads a report JSON, creates a snapshot, writes snapshot JSON.
Deterministic. No network. No subprocess.
Exit 0 on success.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from core.frozen_backlog_snapshot_manager import (
    create_snapshot,
    snapshot_to_dict,
    write_snapshot,
)


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create a frozen backlog snapshot from report JSON."
    )
    parser.add_argument(
        "--input-json",
        type=str,
        required=True,
        help="Path to frozen backlog report JSON.",
    )
    parser.add_argument(
        "--output-snapshot",
        type=str,
        required=True,
        help="Path to write snapshot JSON.",
    )
    return parser.parse_args(argv)


def _load_json(path: str) -> dict:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"File not found: {path}")
    return json.loads(p.read_text(encoding="utf-8"))


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)

    try:
        data = _load_json(args.input_json)
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    created_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    snapshot = create_snapshot(
        report_data=data,
        version="1.0.0",
        created_at_iso=created_at,
        snapshot_id=f"snap-{Path(args.input_json).stem}",
    )

    out_path = Path(args.output_snapshot)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    write_snapshot(snapshot, str(out_path))

    print(f"Snapshot written to {args.output_snapshot}")
    print(f"Snapshot ID: {snapshot.snapshot_id}")
    print(f"Version: {snapshot.version}")
    print(f"Created: {snapshot.created_at_iso}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
