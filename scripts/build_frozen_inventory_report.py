#!/usr/bin/env python3
"""Build frozen inventory report from explicit file list.

Reads file metadata only.  Never imports or executes target files.

Usage:
    python3 scripts/build_frozen_inventory_report.py \
        --output-dir /tmp/frozen_inventory_review \
        --release-hold HOLD \
        --strict
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys

from core.frozen_inventory_audit import (
    RELEASE_HOLD_REQUIRED,
    InventoryResult,
    scan_files,
    write_json,
    write_manifest,
    write_markdown,
)

# ---------------------------------------------------------------------------
# Default inventory: all known pre-existing untracked live/testnet/shadow files
# ---------------------------------------------------------------------------

DEFAULT_FILE_LIST: list[str] = [
    # core
    "core/live_runner.py",
    "core/evidence_recorder.py",
    "core/single_call_recorder.py",
    # scripts - LIVE / TESTNET
    "scripts/live_playbook.py",
    "scripts/run_testnet_order_smoke.py",
    "scripts/run_spot_testnet_acceptance.py",
    "scripts/run_signal_testnet_trial.py",
    "scripts/run_controlled_testnet_shift.py",
    "scripts/run_replay_submit_batch.py",
    "scripts/submit_replayed_testnet_payload.py",
    "scripts/submit_approved_candidates.py",
    "scripts/safe_flatten_testnet_symbol.py",
    # scripts - SHADOW
    "scripts/run_daily_shadow_scan_pipeline.py",
    "scripts/run_next_shadow_experiment_plan.py",
    "scripts/run_shadow_observation_experiments.py",
    "scripts/run_shadow_sample_collection_pipeline.py",
    "scripts/run_shadow_universe_collector.py",
    "scripts/run_remediation_shadow_only_loop.py",
    "scripts/replay_shadow_order_plans_as_testnet_dry.py",
    # scripts - OBSERVATION / RUNTIME
    "scripts/run_observation_shift_runtime.py",
    "scripts/run_right_breakout_param_observation.py",
    "scripts/run_right_breakout_scan_dry.py",
    # scripts - VERIFY
    "scripts/verify_risk_release_flow.py",
    "scripts/verify_testnet_repair_scenarios.py",
    # research
    "research/x_aleabitoreddit_2026-05-21_2026-05-28.md",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build frozen inventory report")
    parser.add_argument("--output-dir", default="/tmp/frozen_inventory_review")
    parser.add_argument("--release-hold", default=RELEASE_HOLD_REQUIRED)
    parser.add_argument("--strict", action="store_true", help="Fail if release_hold != HOLD")
    parser.add_argument("--file-list", default=None, help="Optional JSON file with path list")
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    if args.strict and args.release_hold != RELEASE_HOLD_REQUIRED:
        print(f"FAIL: release_hold={args.release_hold!r} != {RELEASE_HOLD_REQUIRED!r}", file=sys.stderr)
        return 1

    file_list = DEFAULT_FILE_LIST
    if args.file_list:
        p = pathlib.Path(args.file_list)
        if p.exists():
            file_list = json.loads(p.read_text(encoding="utf-8"))

    repo_root = pathlib.Path(__file__).resolve().parent.parent
    result = scan_files(
        file_list,
        repo_root=repo_root,
        release_hold=args.release_hold,
    )

    out_dir = pathlib.Path(args.output_dir)
    write_json(result, out_dir / "frozen_inventory.json")
    write_manifest(result, out_dir / "frozen_inventory_manifest.json")
    write_markdown(result, out_dir / "frozen_inventory.md")

    print(f"OK: {len(result.files)} files scanned")
    print(f"    manifest release_hold={result.manifest['release_hold']}")
    print(f"    output: {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
