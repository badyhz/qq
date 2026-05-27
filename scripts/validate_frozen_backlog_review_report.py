#!/usr/bin/env python3
"""T1619 - Frozen Backlog Review Report Validator CLI.

Validates a frozen backlog report JSON against expected structure.
Deterministic. No network. No subprocess. No frozen file imports.
Exit 0 for PASS, 1 for FAIL.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from core.frozen_backlog_report_validator import validate_report_data


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate frozen backlog review report JSON."
    )
    parser.add_argument(
        "--input-json",
        type=str,
        required=True,
        help="Path to frozen backlog report JSON.",
    )
    parser.add_argument(
        "--expected-total",
        type=int,
        default=22,
        help="Expected total file count (default 22).",
    )
    parser.add_argument(
        "--expected-high",
        type=int,
        default=9,
        help="Expected high-risk count (default 9).",
    )
    parser.add_argument(
        "--expected-medium",
        type=int,
        default=13,
        help="Expected medium-risk count (default 13).",
    )
    parser.add_argument(
        "--require-hold",
        action="store_true",
        default=True,
        help="Require release_hold == HOLD (default True).",
    )
    return parser.parse_args(argv)


def _load_json(path: str) -> dict:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"File not found: {path}")
    return json.loads(p.read_text(encoding="utf-8"))


def _validate_expected_counts(
    data: dict,
    expected_total: int,
    expected_high: int,
    expected_medium: int,
    require_hold: bool,
) -> list[str]:
    """Additional CLI-level checks beyond core validator."""
    extra_failures: list[str] = []
    summary = data.get("summary", {})

    if summary.get("total_files") != expected_total:
        extra_failures.append(f"cli_total_files:{summary.get('total_files')}!={expected_total}")
    if summary.get("high_risk_count") != expected_high:
        extra_failures.append(f"cli_high_risk:{summary.get('high_risk_count')}!={expected_high}")
    if summary.get("medium_risk_count") != expected_medium:
        extra_failures.append(f"cli_medium_risk:{summary.get('medium_risk_count')}!={expected_medium}")
    if require_hold and summary.get("release_hold") != "HOLD":
        extra_failures.append(f"cli_require_hold:{summary.get('release_hold')}!=HOLD")

    return extra_failures


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)

    try:
        data = _load_json(args.input_json)
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        print(f"FAIL: {exc}")
        return 1

    result = validate_report_data(data)

    extra_failures = _validate_expected_counts(
        data, args.expected_total, args.expected_high, args.expected_medium, args.require_hold
    )

    all_passed = result.is_valid and len(extra_failures) == 0

    # Deterministic summary output
    print(f"Input: {args.input_json}")
    print(f"Expected: total={args.expected_total}, high={args.expected_high}, medium={args.expected_medium}")
    print(f"Checks passed: {len(result.checks_passed)}")
    print(f"Checks failed: {len(result.checks_failed)}")
    if extra_failures:
        print(f"CLI extra failures: {len(extra_failures)}")
        for ef in extra_failures:
            print(f"  - {ef}")
    if result.error_message:
        print(f"Error: {result.error_message}")

    if all_passed:
        print("Result: PASS")
        return 0
    else:
        print("Result: FAIL")
        return 1


if __name__ == "__main__":
    sys.exit(main())
