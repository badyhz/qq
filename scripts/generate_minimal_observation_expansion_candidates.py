from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from scripts.strategy_edge_common import read_csv_rows


FIELDS = [
    "candidate_rank",
    "symbol",
    "side",
    "timeframe",
    "strategy_key",
    "expansion_type",
    "source_reason",
    "priority_bucket",
    "required_cache_status",
    "allowed_mode",
    "submit_permission",
    "expansion_allowed_now",
    "risk_level",
    "reason",
]


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def generate_minimal_observation_expansion_candidates(
    *,
    observation_universe_expansion_review_json: str = "reports/observation_universe_expansion/observation_universe_expansion_review.json",
    experiment_priority_rank_csv: str = "reports/shadow_experiment_priorities/experiment_priority_rank.csv",
    shadow_scan_universe_csv: str = "reports/shadow_scan_universe/shadow_scan_universe.csv",
    adjusted_shadow_scan_universe_csv: str = "reports/shadow_universe_adjustment/adjusted_shadow_scan_universe.csv",
    kline_backfill_summary_json: str = "reports/kline_cache_backfill/summary.json",
    output_dir: str = "reports/minimal_observation_expansion",
) -> dict[str, Any]:
    review = _read_json(Path(observation_universe_expansion_review_json))
    priority_rows = read_csv_rows(Path(experiment_priority_rank_csv))
    base_universe = read_csv_rows(Path(shadow_scan_universe_csv))
    adjusted_universe = read_csv_rows(Path(adjusted_shadow_scan_universe_csv))
    backfill = _read_json(Path(kline_backfill_summary_json))

    allow_expand = bool(review.get("allow_expand_observation_universe", False))
    base_keys = {str(row.get("strategy_key", "")).strip() for row in base_universe if str(row.get("strategy_key", "")).strip()}
    adjusted_by_key = {
        str(row.get("strategy_key", "")).strip(): row
        for row in adjusted_universe
        if str(row.get("strategy_key", "")).strip()
    }
    cache_ready = str(backfill.get("final_verdict", "")).strip().upper() == "PASS"
    cache_status_default = "OK" if cache_ready else "PARTIAL"

    out_rows: list[dict[str, Any]] = []
    for idx, item in enumerate(priority_rows, start=1):
        strategy_key = str(item.get("strategy_key", "")).strip()
        if not strategy_key:
            continue
        in_base = strategy_key in base_keys
        adjusted = adjusted_by_key.get(strategy_key, {})
        expansion_type = "KEEP_EXISTING" if in_base else "ADD_SYMBOL"
        if not allow_expand:
            expansion_type = "KEEP_EXISTING" if in_base else "NO_EXPANSION"
        required_cache_status = str(adjusted.get("cache_status", cache_status_default)).strip().upper() or cache_status_default
        source_reason = "priority_rank_input"
        reasons: list[str] = []
        if not allow_expand:
            reasons.append("expansion_not_allowed_yet")
            reasons.append("insufficient_experiment_samples")
        if required_cache_status not in {"OK", "PARTIAL", "STALE", "MISSING"}:
            required_cache_status = cache_status_default
        if required_cache_status in {"MISSING", "PARTIAL"}:
            reasons.append("backfill_recommended")
            if not allow_expand and expansion_type != "KEEP_EXISTING":
                expansion_type = "BACKFILL_ONLY"

        out_rows.append(
            {
                "candidate_rank": idx,
                "symbol": str(item.get("symbol", "")).strip().upper(),
                "side": str(item.get("side", "")).strip().upper(),
                "timeframe": str(item.get("timeframe", "5m")).strip() or "5m",
                "strategy_key": strategy_key,
                "expansion_type": expansion_type,
                "source_reason": source_reason,
                "priority_bucket": str(item.get("priority_bucket", "P2")).strip().upper() or "P2",
                "required_cache_status": required_cache_status,
                "allowed_mode": "SHADOW_ONLY",
                "submit_permission": "NO_SUBMIT",
                "expansion_allowed_now": bool(allow_expand),
                "risk_level": "LOW_CONFIDENCE" if not allow_expand else "CONTROLLED",
                "reason": ";".join(sorted(set(reasons))) if reasons else "ready_for_shadow_only_review",
            }
        )

    if not out_rows:
        out_rows.append(
            {
                "candidate_rank": 1,
                "symbol": "",
                "side": "",
                "timeframe": "5m",
                "strategy_key": "",
                "expansion_type": "NO_EXPANSION",
                "source_reason": "no_priority_rows",
                "priority_bucket": "P2",
                "required_cache_status": cache_status_default,
                "allowed_mode": "SHADOW_ONLY",
                "submit_permission": "NO_SUBMIT",
                "expansion_allowed_now": False,
                "risk_level": "LOW_CONFIDENCE",
                "reason": "insufficient_experiment_samples;no_priority_rows",
            }
        )

    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    csv_path = out_dir / "expansion_candidates.csv"
    summary_json = out_dir / "summary.json"
    summary_md = out_dir / "summary.md"
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        for row in out_rows:
            writer.writerow({field: row.get(field, "") for field in FIELDS})

    expansion_allowed_count = sum(
        1 for row in out_rows if str(row.get("expansion_allowed_now", "")).strip().lower() in {"true", "1"}
    )
    summary = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "final_verdict": "PARTIAL" if not allow_expand else "PASS",
        "candidate_count": len(out_rows),
        "expansion_allowed_count": expansion_allowed_count,
        "allowed_mode": "SHADOW_ONLY",
        "submit_permission": "NO_SUBMIT",
        "allow_expand_observation_universe": bool(allow_expand),
        "csv_path": str(csv_path),
        "summary_json": str(summary_json),
        "summary_md": str(summary_md),
    }
    summary_json.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    lines = [
        "# Minimal Observation Expansion Candidates",
        "",
        f"- final_verdict: {summary['final_verdict']}",
        f"- candidate_count: {summary['candidate_count']}",
        f"- expansion_allowed_count: {summary['expansion_allowed_count']}",
        "- allowed_mode: SHADOW_ONLY",
        "- submit_permission: NO_SUBMIT",
    ]
    summary_md.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return summary


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate minimal observation universe expansion candidates")
    parser.add_argument(
        "--observation-universe-expansion-review-json",
        default="reports/observation_universe_expansion/observation_universe_expansion_review.json",
    )
    parser.add_argument("--experiment-priority-rank-csv", default="reports/shadow_experiment_priorities/experiment_priority_rank.csv")
    parser.add_argument("--shadow-scan-universe-csv", default="reports/shadow_scan_universe/shadow_scan_universe.csv")
    parser.add_argument(
        "--adjusted-shadow-scan-universe-csv",
        default="reports/shadow_universe_adjustment/adjusted_shadow_scan_universe.csv",
    )
    parser.add_argument("--kline-backfill-summary-json", default="reports/kline_cache_backfill/summary.json")
    parser.add_argument("--output-dir", default="reports/minimal_observation_expansion")
    parser.add_argument("--json", action="store_true")
    return parser


def main() -> None:
    args = build_arg_parser().parse_args()
    result = generate_minimal_observation_expansion_candidates(
        observation_universe_expansion_review_json=str(
            args.observation_universe_expansion_review_json
            or "reports/observation_universe_expansion/observation_universe_expansion_review.json"
        ),
        experiment_priority_rank_csv=str(
            args.experiment_priority_rank_csv or "reports/shadow_experiment_priorities/experiment_priority_rank.csv"
        ),
        shadow_scan_universe_csv=str(args.shadow_scan_universe_csv or "reports/shadow_scan_universe/shadow_scan_universe.csv"),
        adjusted_shadow_scan_universe_csv=str(
            args.adjusted_shadow_scan_universe_csv or "reports/shadow_universe_adjustment/adjusted_shadow_scan_universe.csv"
        ),
        kline_backfill_summary_json=str(args.kline_backfill_summary_json or "reports/kline_cache_backfill/summary.json"),
        output_dir=str(args.output_dir or "reports/minimal_observation_expansion"),
    )
    if bool(args.json):
        print(json.dumps(result, ensure_ascii=False))
        return
    print(f"final_verdict={result.get('final_verdict', '')}")
    print(f"candidate_count={result.get('candidate_count', 0)}")


if __name__ == "__main__":
    main()
