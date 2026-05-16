#!/usr/bin/env python3
import argparse
import json
import os
import sys
from typing import Any, Dict, List, Optional


def load_json(path: str) -> Optional[Any]:
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def write_json(path: str, data: Dict[str, Any]) -> bool:
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, sort_keys=True, indent=2, ensure_ascii=False)
        return True
    except Exception:
        return False


def _is_testnet_url(url: Any) -> bool:
    if not isinstance(url, str):
        return False
    lower = url.lower()
    if "api.binance.com" in lower or "mainnet" in lower or "live" in lower:
        return False
    return "testnet" in lower or "demo" in lower


def _candidate_list(payload: Any) -> Optional[List[Dict[str, Any]]]:
    if isinstance(payload, list):
        return [x for x in payload if isinstance(x, dict)]
    if isinstance(payload, dict):
        v = payload.get("candidates")
        if isinstance(v, list):
            return [x for x in v if isinstance(x, dict)]
    return None


def generate_selection(phase_control: Optional[Dict[str, Any]], candidates_payload: Any) -> Dict[str, Any]:
    blockers: List[str] = []
    warnings: List[str] = []
    selected: List[Dict[str, Any]] = []
    rejected: List[Dict[str, Any]] = []

    if not isinstance(phase_control, dict):
        blockers.append("SMALL_BATCH_PHASE_CONTROL_MISSING")

    decision = str((phase_control or {}).get("decision", ""))
    phase_submit_allowed = bool((phase_control or {}).get("submit_allowed") is True)
    phase_max = int((phase_control or {}).get("max_dry_run_candidates", 0) or 0)

    if decision != "ALLOW_SMALL_BATCH_DRY_RUN_ONLY":
        blockers.append("PHASE_DECISION_NOT_ALLOW_SMALL_BATCH_DRY_RUN_ONLY")
    if phase_submit_allowed:
        blockers.append("PHASE_SUBMIT_ALLOWED_MUST_BE_FALSE")
    if phase_max <= 0:
        blockers.append("PHASE_MAX_DRY_RUN_CANDIDATES_INVALID")
    if phase_max > 5:
        blockers.append("PHASE_MAX_DRY_RUN_CANDIDATES_EXCEEDS_FIVE")

    candidates = _candidate_list(candidates_payload)
    if candidates is None:
        blockers.append("CANDIDATES_MALFORMED")
        candidates = []

    max_allowed = min(max(phase_max, 0), 5) if phase_max > 0 else 0

    for cand in candidates:
        env = str(cand.get("env", "")).lower()
        symbol = cand.get("symbol")
        side = cand.get("side")
        qty = cand.get("quantity")
        base_url = cand.get("base_url")

        reason = None
        if env != "testnet":
            reason = "ENV_NOT_TESTNET"
        elif not _is_testnet_url(base_url):
            reason = "BASE_URL_NOT_TESTNET"
        elif not symbol or side not in ["BUY", "SELL"] or qty in [None, "", 0, 0.0, "0"]:
            reason = "MISSING_REQUIRED_FIELDS"

        if reason:
            rejected.append({"candidate": cand, "reason": reason})
            continue

        if len(selected) < max_allowed:
            selected.append(cand)
        else:
            rejected.append({"candidate": cand, "reason": "OVER_MAX_DRY_RUN_CANDIDATES"})

    if len(candidates) > 5:
        warnings.append("INPUT_CANDIDATE_COUNT_EXCEEDS_FIVE")

    if len(selected) == 0:
        blockers.append("NO_VALID_CANDIDATE_SELECTED")

    if len(selected) > 5:
        blockers.append("SELECTED_COUNT_EXCEEDS_FIVE")

    submit_allowed = False

    if blockers:
        verdict = "FAIL"
        ok = False
    elif rejected:
        verdict = "PARTIAL"
        ok = True
    else:
        verdict = "PASS"
        ok = True

    return {
        "ok": ok,
        "verdict": verdict,
        "selected_count": len(selected),
        "max_dry_run_candidates": max_allowed,
        "submit_allowed": submit_allowed,
        "selected_candidates": selected,
        "rejected_candidates": rejected,
        "blockers": sorted(set(blockers)),
        "warnings": sorted(set(warnings)),
        "selection_reason": "small_batch_dry_run_only_selection",
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Generate small batch dry-run candidate selection packet")
    parser.add_argument("--small-batch-phase-control-json", required=True)
    parser.add_argument("--candidates-json", required=True)
    parser.add_argument("--output-json")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args(argv)

    report = generate_selection(load_json(args.small_batch_phase_control_json), load_json(args.candidates_json))

    if args.output_json and not write_json(args.output_json, report):
        print("failed_to_write_output", file=sys.stderr)
        return 1
    if args.json:
        if args.pretty:
            print(json.dumps(report, sort_keys=True, indent=2, ensure_ascii=False))
        else:
            print(json.dumps(report, sort_keys=True, ensure_ascii=False))
    return 0 if report.get("ok") else 1


if __name__ == "__main__":
    sys.exit(main())
