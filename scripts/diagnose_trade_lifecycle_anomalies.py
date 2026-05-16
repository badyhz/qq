from __future__ import annotations

import argparse
import csv
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ANOMALY_FIELDS = [
    "rank",
    "severity",
    "trade_id",
    "candidate_id",
    "symbol",
    "side",
    "outcome",
    "lifecycle_status",
    "execution_quality_score",
    "pnl_estimate_usdt",
    "realized_r_multiple",
    "anomaly_type",
    "reason",
    "recommended_action",
    "source_reports",
]

SEVERITY_PRIORITY = {
    "CRITICAL": 5,
    "HIGH": 4,
    "MEDIUM": 3,
    "LOW": 2,
    "INFO": 1,
}

RECOMMENDED_ACTIONS = {
    "UNCLEAN_ORPHAN": "run safe flatten / orphan cleanup in dry-run first",
    "UNKNOWN_OUTCOME": "inspect trigger outcome report and exchange order history",
    "FAILED_PROTECTION": "inspect algoOrder submit response and reduceOnly settings",
    "LOW_EXECUTION_SCORE": "inspect deductions column in execution_quality_scores.csv",
    "NEGATIVE_R_MULTIPLE": "review entry timing and stop distance",
    "MISSING_PNL": "verify exit_price / entry_price / quantity fields",
    "NOT_CLOSED": "inspect lifecycle state machine and close handling",
    "DUPLICATE_CANDIDATE_ID": "run duplicate candidate id repair and enforce unique id guard",
    "MISSING_SL": "verify stop_loss_plan generation and protective order payload",
    "MISSING_TP": "verify take_profit_plan generation and protective order payload",
}


def _to_float_nan(value: Any) -> float:
    if value is None:
        return float("nan")
    text = str(value).strip()
    if not text:
        return float("nan")
    try:
        return float(text)
    except (TypeError, ValueError):
        return float("nan")


def _to_bool(value: Any) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "y"}


def _read_rows(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    try:
        with path.open("r", encoding="utf-8", newline="") as handle:
            return list(csv.DictReader(handle))
    except OSError:
        return []


def _quality_maps(rows: list[dict[str, Any]]) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    by_trade: dict[str, dict[str, Any]] = {}
    by_candidate: dict[str, dict[str, Any]] = {}
    for row in rows:
        trade_id = str(row.get("trade_id", "")).strip()
        candidate_id = str(row.get("candidate_id", "")).strip()
        if trade_id:
            by_trade[trade_id] = row
        if candidate_id:
            by_candidate[candidate_id] = row
    return by_trade, by_candidate


def _recommended_action(anomaly_type: str) -> str:
    return RECOMMENDED_ACTIONS.get(anomaly_type, "inspect related reports and rerun offline diagnostics")


def _add_anomaly(
    rows: list[dict[str, Any]],
    seen: set[tuple[str, str]],
    *,
    base: dict[str, Any],
    severity: str,
    anomaly_type: str,
    reason: str,
) -> None:
    key = (str(base.get("trade_id", "")).strip(), anomaly_type)
    if key in seen:
        return
    seen.add(key)
    rows.append(
        {
            "rank": 0,
            "severity": severity,
            "trade_id": str(base.get("trade_id", "")).strip(),
            "candidate_id": str(base.get("candidate_id", "")).strip(),
            "symbol": str(base.get("symbol", "")).strip().upper(),
            "side": str(base.get("side", "")).strip().upper(),
            "outcome": str(base.get("outcome", "")).strip().upper(),
            "lifecycle_status": str(base.get("lifecycle_status", "")).strip().upper(),
            "execution_quality_score": base.get("execution_quality_score", ""),
            "pnl_estimate_usdt": base.get("pnl_estimate_usdt", ""),
            "realized_r_multiple": base.get("realized_r_multiple", ""),
            "anomaly_type": anomaly_type,
            "reason": reason,
            "recommended_action": _recommended_action(anomaly_type),
            "source_reports": base.get("source_reports", ""),
        }
    )


def diagnose_trade_lifecycle_anomalies(
    *,
    lifecycle_csv: str = "reports/trade_lifecycle/trade_lifecycle.csv",
    quality_csv: str = "reports/execution_quality/execution_quality_scores.csv",
    output_dir: str = "reports/trade_lifecycle_anomalies",
) -> dict[str, Any]:
    lifecycle_path = Path(lifecycle_csv)
    quality_path = Path(quality_csv)
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    lifecycle_rows = _read_rows(lifecycle_path)
    quality_rows = _read_rows(quality_path)
    quality_by_trade, quality_by_candidate = _quality_maps(quality_rows)

    candidate_counts: dict[str, int] = {}
    for row in lifecycle_rows:
        candidate_id = str(row.get("candidate_id", "")).strip()
        if candidate_id:
            candidate_counts[candidate_id] = candidate_counts.get(candidate_id, 0) + 1

    anomalies: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    orphan_ever_cleaned_count = 0

    for row in lifecycle_rows:
        trade_id = str(row.get("trade_id", "")).strip()
        candidate_id = str(row.get("candidate_id", "")).strip()
        quality = quality_by_trade.get(trade_id) or quality_by_candidate.get(candidate_id) or {}
        score = _to_float_nan(quality.get("execution_quality_score"))
        pnl = _to_float_nan(row.get("pnl_estimate_usdt"))
        realized_r = _to_float_nan(row.get("realized_r_multiple"))
        sl_price = _to_float_nan(row.get("sl_price"))
        tp_price = _to_float_nan(row.get("tp_price"))
        outcome = str(row.get("outcome", "")).strip().upper()
        lifecycle_status = str(row.get("lifecycle_status", "")).strip().upper()
        orphan_after = _to_bool(row.get("orphan_after_close", False))
        orphan_ever = _to_bool(row.get("orphan_ever_detected", False))
        orphan_cleanup = _to_bool(row.get("orphan_cleanup_done", False))
        protection_ok = _to_bool(row.get("protective_order_success", False))

        base = dict(row)
        base["execution_quality_score"] = quality.get("execution_quality_score", "")

        if orphan_ever and orphan_cleanup and not orphan_after:
            orphan_ever_cleaned_count += 1
        if orphan_after:
            _add_anomaly(
                anomalies,
                seen,
                base=base,
                severity="CRITICAL",
                anomaly_type="UNCLEAN_ORPHAN",
                reason="orphan_after_close=true indicates residual protective order after close",
            )

        if outcome in {"UNKNOWN", "EXTERNAL_CLOSED", ""}:
            _add_anomaly(
                anomalies,
                seen,
                base=base,
                severity="HIGH",
                anomaly_type="UNKNOWN_OUTCOME",
                reason=f"outcome={outcome or 'EMPTY'} cannot be deterministically attributed",
            )

        if not protection_ok:
            _add_anomaly(
                anomalies,
                seen,
                base=base,
                severity="HIGH",
                anomaly_type="FAILED_PROTECTION",
                reason="protective_order_success=false",
            )

        if lifecycle_status != "CLOSED":
            _add_anomaly(
                anomalies,
                seen,
                base=base,
                severity="HIGH",
                anomaly_type="NOT_CLOSED",
                reason=f"lifecycle_status={lifecycle_status or 'EMPTY'}",
            )

        if not math.isfinite(pnl):
            _add_anomaly(
                anomalies,
                seen,
                base=base,
                severity="MEDIUM",
                anomaly_type="MISSING_PNL",
                reason="pnl_estimate_usdt missing or invalid",
            )

        if math.isfinite(realized_r) and realized_r < -1.0:
            _add_anomaly(
                anomalies,
                seen,
                base=base,
                severity="MEDIUM",
                anomaly_type="NEGATIVE_R_MULTIPLE",
                reason=f"realized_r_multiple={realized_r:.6f} < -1.0",
            )

        if math.isfinite(score):
            if score < 75:
                _add_anomaly(
                    anomalies,
                    seen,
                    base=base,
                    severity="HIGH",
                    anomaly_type="LOW_EXECUTION_SCORE",
                    reason=f"execution_quality_score={score:.2f} < 75",
                )
            elif score < 85:
                _add_anomaly(
                    anomalies,
                    seen,
                    base=base,
                    severity="MEDIUM",
                    anomaly_type="LOW_EXECUTION_SCORE",
                    reason=f"execution_quality_score={score:.2f} < 85",
                )

        if candidate_id and candidate_counts.get(candidate_id, 0) > 1:
            _add_anomaly(
                anomalies,
                seen,
                base=base,
                severity="HIGH",
                anomaly_type="DUPLICATE_CANDIDATE_ID",
                reason=f"candidate_id duplicated {candidate_counts[candidate_id]} times in lifecycle table",
            )

        if (not math.isfinite(sl_price)) or sl_price <= 0:
            _add_anomaly(
                anomalies,
                seen,
                base=base,
                severity="MEDIUM",
                anomaly_type="MISSING_SL",
                reason="sl_price missing or non-positive",
            )
        if (not math.isfinite(tp_price)) or tp_price <= 0:
            _add_anomaly(
                anomalies,
                seen,
                base=base,
                severity="MEDIUM",
                anomaly_type="MISSING_TP",
                reason="tp_price missing or non-positive",
            )

    anomalies.sort(
        key=lambda row: (
            -SEVERITY_PRIORITY.get(str(row.get("severity", "")).upper(), 0),
            str(row.get("trade_id", "")),
            str(row.get("anomaly_type", "")),
        )
    )
    for idx, row in enumerate(anomalies, start=1):
        row["rank"] = idx

    anomalies_csv = out_dir / "anomalies.csv"
    top_json = out_dir / "top_anomalies.json"
    summary_md = out_dir / "summary.md"

    with anomalies_csv.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=ANOMALY_FIELDS)
        writer.writeheader()
        for row in anomalies:
            writer.writerow({field: row.get(field, "") for field in ANOMALY_FIELDS})

    severity_counts = {key.lower() + "_count": 0 for key in SEVERITY_PRIORITY.keys()}
    type_counts: dict[str, int] = {}
    for row in anomalies:
        severity = str(row.get("severity", "")).strip().upper()
        key = severity.lower() + "_count"
        if key in severity_counts:
            severity_counts[key] += 1
        anomaly_type = str(row.get("anomaly_type", "")).strip().upper()
        type_counts[anomaly_type] = type_counts.get(anomaly_type, 0) + 1

    final_verdict = "PASS"
    if severity_counts["critical_count"] > 0:
        final_verdict = "FAIL"
    elif severity_counts["high_count"] > 0:
        final_verdict = "PARTIAL"

    summary = {
        "ok": True,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "lifecycle_csv": str(lifecycle_path),
        "quality_csv": str(quality_path),
        "total_trades": len(lifecycle_rows),
        "total_anomalies": len(anomalies),
        "final_verdict": final_verdict,
        "severity_counts": severity_counts,
        "type_counts": type_counts,
        "top_n": anomalies[:10],
        "orphan_ever_cleaned_count": orphan_ever_cleaned_count,
        "anomalies_csv": str(anomalies_csv),
        "top_anomalies_json": str(top_json),
        "summary_md": str(summary_md),
    }
    top_json.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = [
        "# Trade Lifecycle Anomaly Summary",
        "",
        f"- total_trades: {summary['total_trades']}",
        f"- total_anomalies: {summary['total_anomalies']}",
        f"- final_verdict: {summary['final_verdict']}",
        f"- critical_count: {severity_counts['critical_count']}",
        f"- high_count: {severity_counts['high_count']}",
        f"- medium_count: {severity_counts['medium_count']}",
        f"- low_count: {severity_counts['low_count']}",
        f"- info_count: {severity_counts['info_count']}",
        f"- orphan_ever_cleaned_count: {summary['orphan_ever_cleaned_count']}",
    ]
    if len(anomalies) == 0:
        lines.extend(["", "- no critical anomalies"])
    summary_md.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return summary


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Diagnose anomalies from trade lifecycle and execution quality")
    parser.add_argument("--lifecycle-csv", default="reports/trade_lifecycle/trade_lifecycle.csv")
    parser.add_argument("--quality-csv", default="reports/execution_quality/execution_quality_scores.csv")
    parser.add_argument("--output-dir", default="reports/trade_lifecycle_anomalies")
    parser.add_argument("--json", action="store_true")
    return parser


def main() -> None:
    args = build_arg_parser().parse_args()
    summary = diagnose_trade_lifecycle_anomalies(
        lifecycle_csv=str(args.lifecycle_csv or "reports/trade_lifecycle/trade_lifecycle.csv"),
        quality_csv=str(args.quality_csv or "reports/execution_quality/execution_quality_scores.csv"),
        output_dir=str(args.output_dir or "reports/trade_lifecycle_anomalies"),
    )
    if bool(args.json):
        print(json.dumps(summary, ensure_ascii=False))
        return
    print(f"total_anomalies={summary.get('total_anomalies', 0)}")
    print(f"final_verdict={summary.get('final_verdict', '')}")
    print(f"top_anomalies_json={summary.get('top_anomalies_json', '')}")


if __name__ == "__main__":
    main()
