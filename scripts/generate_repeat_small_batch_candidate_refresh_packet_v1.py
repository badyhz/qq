#!/usr/bin/env python3
import argparse
import json
import os
import sys
from typing import Any, Dict, List, Optional

from core.execution_guards import assert_dry_run_required, normalize_execution_mode


def load_json(path: str) -> Optional[Any]:
    if not path or not os.path.exists(path):
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


def _candidates(payload: Any) -> Optional[List[Dict[str, Any]]]:
    if isinstance(payload, list):
        return [x for x in payload if isinstance(x, dict)]
    if isinstance(payload, dict) and isinstance(payload.get("candidates"), list):
        return [x for x in payload["candidates"] if isinstance(x, dict)]
    return None


def generate_refresh(
    repeat_eligibility: Optional[Dict[str, Any]],
    new_candidates: Any,
    previous_selection: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    blockers = []
    warnings = []
    selected: List[Dict[str, Any]] = []
    rejected: List[Dict[str, Any]] = []
    drift_items: List[Dict[str, Any]] = []

    if not isinstance(repeat_eligibility, dict):
        blockers.append("REPEAT_ELIGIBILITY_MISSING")
        repeat_eligibility = {}

    e_verdict = str(repeat_eligibility.get("verdict", ""))
    if e_verdict not in ["PASS", "PARTIAL"]:
        blockers.append("REPEAT_ELIGIBILITY_NOT_PASS_OR_PARTIAL")

    max_allowed = int(repeat_eligibility.get("max_dry_run_candidates", 0) or 0)
    if max_allowed <= 0:
        blockers.append("REPEAT_ELIGIBILITY_MAX_DRY_RUN_INVALID")
    if max_allowed > 5:
        max_allowed = 5

    cands = _candidates(new_candidates)
    if cands is None:
        blockers.append("NEW_CANDIDATES_MALFORMED")
        cands = []

    unsafe_marker_found = False
    for c in cands:
        env = str(c.get("env", "")).lower()
        symbol = c.get("symbol")
        side = c.get("side")
        qty = c.get("quantity")
        base_url = c.get("base_url")

        reason = None
        if env != "testnet":
            reason = "ENV_NOT_TESTNET"
            unsafe_marker_found = True
        elif not _is_testnet_url(base_url):
            reason = "BASE_URL_NOT_TESTNET"
            unsafe_marker_found = True
        elif not symbol or side not in ["BUY", "SELL"] or qty in [None, "", 0, 0.0, "0"]:
            reason = "MISSING_REQUIRED_FIELDS"

        if reason:
            rejected.append({"candidate": c, "reason": reason})
            continue

        if len(selected) < max_allowed:
            selected.append(c)
        else:
            rejected.append({"candidate": c, "reason": "OVER_MAX_DRY_RUN_CANDIDATES"})

    if len(selected) > 5:
        selected = selected[:5]
        warnings.append("SELECTED_COUNT_CAPPED_AT_FIVE")

    prev_selected = []
    if isinstance(previous_selection, dict) and isinstance(previous_selection.get("selected_candidates"), list):
        prev_selected = [x for x in previous_selection["selected_candidates"] if isinstance(x, dict)]

    prev_keys = {(x.get("symbol"), x.get("side"), str(x.get("quantity"))) for x in prev_selected}
    new_keys = {(x.get("symbol"), x.get("side"), str(x.get("quantity"))) for x in selected}

    added = sorted(list(new_keys - prev_keys))
    removed = sorted(list(prev_keys - new_keys))

    if added:
        drift_items.append({"type": "added", "items": [list(x) for x in added]})
    if removed:
        drift_items.append({"type": "removed", "items": [list(x) for x in removed]})

    drift_from_previous = bool(added or removed)

    if unsafe_marker_found:
        blockers.append("UNSAFE_CANDIDATE_MARKER_DETECTED")
    if not selected:
        blockers.append("NO_SAFE_CANDIDATE_SELECTED")

    if blockers:
        verdict = "FAIL"
        ok = False
    elif e_verdict == "PARTIAL":
        verdict = "PARTIAL"
        ok = True
    else:
        verdict = "PASS"
        ok = True

    return {
        "ok": ok,
        "verdict": verdict,
        "selected_count": len(selected),
        "max_dry_run_candidates": min(max(max_allowed, 0), 5),
        "submit_allowed": False,
        "selected_candidates": selected,
        "rejected_candidates": rejected,
        "drift_from_previous": drift_from_previous,
        "drift_items": drift_items,
        "blockers": sorted(set(blockers)),
        "warnings": sorted(set(warnings)),
    }


def main(argv=None) -> int:
    mode = normalize_execution_mode(os.environ.get("QQ_RUNTIME_MODE"))
    assert_dry_run_required(mode)
    parser = argparse.ArgumentParser(description="Generate repeat small batch candidate refresh packet")
    parser.add_argument("--repeat-eligibility-json", required=True)
    parser.add_argument("--new-candidates-json", required=True)
    parser.add_argument("--previous-selection-json")
    parser.add_argument("--output-json")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args(argv)

    report = generate_refresh(
        load_json(args.repeat_eligibility_json),
        load_json(args.new_candidates_json),
        load_json(args.previous_selection_json) if args.previous_selection_json else None,
    )

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
