#!/usr/bin/env python3
import argparse
import json
import os
import sys
from collections import Counter
from typing import Any, Dict, List, Optional


def load_json(path: str) -> Optional[Dict[str, Any]]:
    if not path or not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else None
    except Exception:
        return None


def write_json(path: str, data: Dict[str, Any]) -> bool:
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, sort_keys=True, indent=2, ensure_ascii=False)
        return True
    except Exception:
        return False


def _to_float(v: Any, default: float = 0.0) -> float:
    try:
        return float(v)
    except Exception:
        return default


def generate_report(selection: Optional[Dict[str, Any]], aggregate: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    blockers: List[str] = []
    warnings: List[str] = []

    if selection is None:
        blockers.append("CANDIDATE_SELECTION_MISSING")
        selection = {}

    if bool(selection.get("submit_allowed") is True):
        blockers.append("SUBMIT_ALLOWED_TRUE_NOT_PERMITTED")

    candidates = selection.get("selected_candidates")
    if not isinstance(candidates, list):
        blockers.append("SELECTED_CANDIDATES_MALFORMED")
        candidates = []

    count = len(candidates)
    if count > 5:
        blockers.append("CANDIDATE_COUNT_EXCEEDS_FIVE")

    symbols: List[str] = []
    sides: List[str] = []
    notionals: List[float] = []

    for c in candidates:
        if not isinstance(c, dict):
            continue
        env = str(c.get("env", "")).lower()
        if env != "testnet":
            blockers.append("CANDIDATE_ENV_NOT_TESTNET")
        symbol = str(c.get("symbol", ""))
        side = str(c.get("side", ""))
        symbols.append(symbol)
        sides.append(side)
        qty = _to_float(c.get("quantity"), 0.0)
        price = _to_float(c.get("reference_price") or c.get("entry_price") or 1.0, 1.0)
        notionals.append(max(0.0, qty * price))

    symbol_counter = Counter(symbols)
    side_counter = Counter(sides)
    duplicates = sorted([s for s, n in symbol_counter.items() if s and n > 1])

    total_notional = sum(notionals)
    max_notional = max(notionals) if notionals else 0.0
    dominance = (max_notional / total_notional) if total_notional > 0 else 0.0

    concentration_status = "LOW"

    if blockers:
        concentration_status = "UNSAFE"
    elif duplicates or (len(side_counter) == 1 and count > 1) or dominance > 0.60:
        concentration_status = "HIGH"
    elif count > 0 and (dominance > 0.40 or len(symbol_counter) <= max(1, count // 2)):
        concentration_status = "MEDIUM"
    else:
        concentration_status = "LOW"

    if aggregate is not None and str(aggregate.get("verdict", "")) == "FAIL":
        warnings.append("DRY_RUN_AGGREGATE_NOT_PASS")

    if blockers:
        verdict = "FAIL"
        ok = False
    elif concentration_status == "HIGH":
        verdict = "PARTIAL"
        ok = True
    elif concentration_status == "MEDIUM":
        verdict = "PARTIAL"
        ok = True
    else:
        verdict = "PASS"
        ok = True

    recommendations = []
    if concentration_status == "HIGH":
        recommendations.append("REDUCE_CONCENTRATION_BEFORE_NEXT_BATCH")
    elif concentration_status == "MEDIUM":
        recommendations.append("CONSIDER_SYMBOL_DIVERSIFICATION")
    elif concentration_status == "LOW":
        recommendations.append("CONTINUE_DRY_RUN_ONLY_WITH_MONITORING")
    else:
        recommendations.append("STOP_AND_REVIEW")

    return {
        "ok": ok,
        "verdict": verdict,
        "concentration_status": concentration_status,
        "symbol_count": len(set([s for s in symbols if s])),
        "side_distribution": dict(side_counter),
        "duplicate_symbols": duplicates,
        "total_notional_estimate": total_notional,
        "max_single_candidate_notional": max_notional,
        "blockers": sorted(set(blockers)),
        "warnings": sorted(set(warnings)),
        "recommendations": recommendations,
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Generate small batch dry-run risk concentration report")
    parser.add_argument("--candidate-selection-json", required=True)
    parser.add_argument("--dry-run-aggregate-json")
    parser.add_argument("--output-json")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args(argv)

    report = generate_report(
        load_json(args.candidate_selection_json),
        load_json(args.dry_run_aggregate_json) if args.dry_run_aggregate_json else None,
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
