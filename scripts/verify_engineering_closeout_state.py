#!/usr/bin/env python3
"""Verify engineering closeout state for a git repository.

Readonly checks:
- Inside git repo
- Current HEAD
- Tag target
- Dirty tree summary
- Frozen files not staged
- Closure tag points to HEAD
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys

from core.execution_guards import assert_dry_run_required, normalize_execution_mode

FROZEN_PATTERNS = [
    "live_runner",
    "live_playbook",
    "submit_approved",
    "submit_replayed",
    "run_replay_submit",
    "safe_flatten",
    "run_spot_testnet",
    "run_testnet_order",
    "verify_testnet_repair",
    "replay_shadow",
    "run_controlled",
    "run_daily_shadow",
    "run_next_shadow",
    "run_observation",
    "run_remediation",
    "run_right_breakout",
    "run_shadow_observation",
    "run_shadow_sample",
    "run_shadow_universe",
    "run_signal_testnet",
]


def run_cmd(args: list[str]) -> tuple[int, str]:
    result = subprocess.run(args, capture_output=True, text=True)
    return result.returncode, result.stdout.strip()


def verify_git_repo() -> tuple[bool, str]:
    code, out = run_cmd(["git", "rev-parse", "--is-inside-work-tree"])
    return code == 0 and out == "true", out


def verify_head() -> tuple[bool, str]:
    code, out = run_cmd(["git", "log", "--oneline", "-1"])
    return code == 0, out


def verify_tag(tag_name: str) -> tuple[bool, str]:
    code, out = run_cmd(["git", "rev-parse", tag_name])
    return code == 0, out


def verify_tag_points_to_head(tag_name: str) -> tuple[bool, str]:
    tag_code, tag_hash = run_cmd(["git", "rev-parse", tag_name])
    head_code, head_hash = run_cmd(["git", "rev-parse", "HEAD"])
    if tag_code != 0 or head_code != 0:
        return False, "could not resolve tag or HEAD"
    match = tag_hash == head_hash
    return match, f"tag={tag_hash[:8]} head={head_hash[:8]} match={match}"


def verify_dirty_tree() -> tuple[bool, str]:
    code, out = run_cmd(["git", "status", "--short"])
    if code != 0:
        return False, "could not get status"
    lines = [l for l in out.splitlines() if l.strip()]
    untracked = [l for l in lines if l.startswith("??")]
    modified = [l for l in lines if l.startswith(" M") or l.startswith("M ")]
    staged = [l for l in lines if l.startswith("M ") or l.startswith("A ")]
    return True, f"total={len(lines)} untracked={len(untracked)} modified={len(modified)} staged={len(staged)}"


def verify_no_frozen_staged() -> tuple[bool, str]:
    code, out = run_cmd(["git", "diff", "--cached", "--name-only"])
    if code != 0:
        return False, "could not get staged files"
    staged_files = out.splitlines() if out else []
    frozen_staged = []
    for f in staged_files:
        for pattern in FROZEN_PATTERNS:
            if pattern in f:
                frozen_staged.append(f)
                break
    match = len(frozen_staged) == 0
    return match, f"frozen_staged={frozen_staged if frozen_staged else 'none'}"


def verify_frozen_not_committed(tag_name: str) -> tuple[bool, str]:
    code, out = run_cmd(["git", "show", "--stat", tag_name])
    if code != 0:
        return False, "could not show tag commit"
    frozen_committed = []
    for pattern in FROZEN_PATTERNS:
        if pattern in out:
            frozen_committed.append(pattern)
    match = len(frozen_committed) == 0
    return match, f"frozen_in_commit={frozen_committed if frozen_committed else 'none'}"


def verify_engineering_closeout(tag_name: str) -> dict:
    results = {}

    ok, msg = verify_git_repo()
    results["git_repo"] = {"pass": ok, "detail": msg}

    ok, msg = verify_head()
    results["head"] = {"pass": ok, "detail": msg}

    ok, msg = verify_tag(tag_name)
    results["tag_exists"] = {"pass": ok, "detail": msg}

    ok, msg = verify_tag_points_to_head(tag_name)
    results["tag_points_to_head"] = {"pass": ok, "detail": msg}

    ok, msg = verify_dirty_tree()
    results["dirty_tree"] = {"pass": ok, "detail": msg}

    ok, msg = verify_no_frozen_staged()
    results["no_frozen_staged"] = {"pass": ok, "detail": msg}

    ok, msg = verify_frozen_not_committed(tag_name)
    results["no_frozen_committed"] = {"pass": ok, "detail": msg}

    all_pass = all(r["pass"] for r in results.values())
    results["_summary"] = {"pass": all_pass, "checks": len(results) - 1}

    return results


def main():
    mode = normalize_execution_mode(os.environ.get("QQ_RUNTIME_MODE"))
    assert_dry_run_required(mode)

    parser = argparse.ArgumentParser(description="Verify engineering closeout state")
    parser.add_argument("--tag", default="phase2-complete", help="Closure tag name")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    args = parser.parse_args()

    results = verify_engineering_closeout(args.tag)

    if args.json:
        import json
        print(json.dumps(results, indent=2))
    else:
        for key, val in results.items():
            if key.startswith("_"):
                continue
            status = "PASS" if val["pass"] else "FAIL"
            print(f"  [{status}] {key}: {val['detail']}")
        summary = results["_summary"]
        print(f"\n{'PASS' if summary['pass'] else 'FAIL'} ({summary['checks']} checks)")

    sys.exit(0 if results["_summary"]["pass"] else 1)


if __name__ == "__main__":
    main()
