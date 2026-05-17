from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

def _parse_dt(value: Any) -> datetime | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        dt = datetime.fromisoformat(text)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except ValueError:
        return None


def _parse_json_file(path: Path) -> tuple[dict[str, Any] | None, bool]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None, False
    if isinstance(payload, dict):
        return payload, True
    return None, False


def _parse_jsonl_with_invalid(path: Path) -> tuple[list[dict[str, Any]], int]:
    rows: list[dict[str, Any]] = []
    invalid_rows = 0
    if not path.exists():
        return rows, invalid_rows
    for line in path.read_text(encoding="utf-8").splitlines():
        text = line.strip()
        if not text:
            continue
        try:
            payload = json.loads(text)
        except json.JSONDecodeError:
            invalid_rows += 1
            continue
        if isinstance(payload, dict):
            rows.append(payload)
        else:
            invalid_rows += 1
    return rows, invalid_rows


def _first_existing(paths: list[Path]) -> Path | None:
    for path in paths:
        if path.exists():
            return path
    return None


def _latest_summary_dir(root: Path) -> Path | None:
    if not root.exists():
        return None
    summaries = [path.parent for path in root.glob("*/summary.json") if path.exists()]
    if not summaries:
        return None
    return max(summaries, key=lambda path: path.stat().st_mtime)


def _latest_approved_run(root: Path) -> Path | None:
    if not root.exists():
        return None
    dirs = [path for path in root.glob("*") if path.is_dir()]
    if not dirs:
        return None
    return max(dirs, key=lambda path: path.stat().st_mtime)


def classify_validation_verdict(
    *,
    ok: bool,
    missing_files: list[str],
    invalid_json_files: list[str],
    empty_files: list[str],
    warnings: list[str],
) -> str:
    if not bool(ok):
        return "FAIL"
    if missing_files or invalid_json_files or empty_files or warnings:
        return "PARTIAL"
    return "PASS"


def validate_testnet_artifacts(
    *,
    logs_dir: str = "logs",
    date: str = "",
    strict: bool = False,
) -> dict[str, Any]:
    root = Path(logs_dir)
    target_date = str(date or "").strip()
    if not target_date:
        target_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    missing_files: list[str] = []
    optional_missing_files: list[str] = []
    invalid_json_files: list[str] = []
    empty_files: list[str] = []
    warnings: list[str] = []
    recommendations: list[str] = []

    candidates_path = root / "execution_candidates.jsonl"
    risk_path = root / "risk_events.jsonl"
    scoped_risk_path = root / "risk_events_scoped_v3.jsonl"
    daily_md_path = root / f"daily_summary_{target_date}.md"
    approved_root = root / "approved_candidate_runs"
    observation_root = root / "observation_shifts"
    scheduled_root = root / "scheduled_observations"

    candidate_counts = {"total": 0, "pending": 0, "approved": 0, "rejected": 0, "expired": 0, "submitted": 0, "skipped": 0, "submit_failed": 0}
    risk_event_counts = {"total": 0, "invalid_rows": 0}
    scoped_risk_event_counts = {"total": 0, "invalid_rows": 0}
    approved_run_summary: dict[str, Any] = {}
    latest_approved_run_is_noop = False

    for required in [candidates_path, risk_path, scoped_risk_path]:
        if not required.exists():
            missing_files.append(str(required))
            warnings.append(f"missing:{required.name}")

    if not daily_md_path.exists():
        missing_files.append(str(daily_md_path))
        warnings.append("missing:daily_summary_md")
    elif not daily_md_path.read_text(encoding="utf-8").strip():
        empty_files.append(str(daily_md_path))

    candidate_rows, invalid_candidate_rows = _parse_jsonl_with_invalid(candidates_path)
    if invalid_candidate_rows > 0:
        invalid_json_files.append(f"{candidates_path} (invalid_rows={invalid_candidate_rows})")
    candidate_counts["total"] = len(candidate_rows)
    for row in candidate_rows:
        status = str(row.get("status", "")).strip().lower()
        if status in candidate_counts:
            candidate_counts[status] = int(candidate_counts.get(status, 0)) + 1

    risk_rows, invalid_risk_rows = _parse_jsonl_with_invalid(risk_path)
    risk_event_counts["total"] = len(risk_rows)
    risk_event_counts["invalid_rows"] = invalid_risk_rows
    if invalid_risk_rows > 0:
        invalid_json_files.append(f"{risk_path} (invalid_rows={invalid_risk_rows})")

    scoped_rows, invalid_scoped_rows = _parse_jsonl_with_invalid(scoped_risk_path)
    scoped_risk_event_counts["total"] = len(scoped_rows)
    scoped_risk_event_counts["invalid_rows"] = invalid_scoped_rows
    if invalid_scoped_rows > 0:
        invalid_json_files.append(f"{scoped_risk_path} (invalid_rows={invalid_scoped_rows})")

    latest_run = _latest_approved_run(approved_root)
    latest_run_path = str(latest_run) if latest_run is not None else ""
    if latest_run is not None:
        summary_json_path = latest_run / "summary.json"
        if summary_json_path.exists():
            payload, ok_json = _parse_json_file(summary_json_path)
            if not ok_json:
                invalid_json_files.append(str(summary_json_path))
            else:
                approved_run_summary = {
                    "run_id": payload.get("run_id", ""),
                    "overall_status": payload.get("overall_status", ""),
                    "planned_count": int(payload.get("planned_count", 0) or 0),
                    "submitted_count": int(payload.get("submitted_count", 0) or 0),
                    "failed_count": int(payload.get("failed_count", 0) or 0),
                }
                latest_approved_run_is_noop = (
                    str(approved_run_summary.get("overall_status", "")).strip().upper() == "PASS"
                    and int(approved_run_summary.get("planned_count", 0)) == 0
                    and int(approved_run_summary.get("submitted_count", 0)) == 0
                    and int(approved_run_summary.get("failed_count", 0)) == 0
                )
        required_run_files = [
            latest_run / "summary.json",
            latest_run / "summary.md",
            latest_run / "acceptance_report.md",
            latest_run / "approved_payloads.jsonl",
        ]
        optional_noop_files = [
            latest_run / "manifest.json",
            latest_run / "candidate_snapshot.json",
            latest_run / "risk_events_excerpt.jsonl",
            latest_run / "batch" / "summary.json",
            latest_run / "batch" / "summary.md",
        ]
        for path in required_run_files:
            if not path.exists():
                missing_files.append(str(path))
        for path in optional_noop_files:
            if not path.exists():
                if latest_approved_run_is_noop:
                    optional_missing_files.append(str(path))
                else:
                    missing_files.append(str(path))
        manifest_path = latest_run / "manifest.json"
        if manifest_path.exists():
            manifest_payload, ok_json = _parse_json_file(manifest_path)
            if not ok_json:
                invalid_json_files.append(str(manifest_path))
            else:
                for file_ref in list(manifest_payload.get("generated_files", [])):
                    ref_path = Path(str(file_ref))
                    if not ref_path.exists():
                        missing_files.append(str(ref_path))
        elif latest_approved_run_is_noop:
            optional_missing_files.append(str(manifest_path))
    else:
        warnings.append("missing:approved_run_dir")

    latest_observation = _latest_summary_dir(observation_root)
    latest_observation_path = str(latest_observation) if latest_observation is not None else ""
    if latest_observation is not None:
        for path in [latest_observation / "summary.json", latest_observation / "summary.md"]:
            if not path.exists():
                missing_files.append(str(path))
    else:
        warnings.append("missing:observation_shift_dir")

    latest_scheduled = _latest_summary_dir(scheduled_root)
    latest_scheduled_path = str(latest_scheduled) if latest_scheduled is not None else ""
    if latest_scheduled is not None:
        for path in [latest_scheduled / "summary.json", latest_scheduled / "summary.md"]:
            if not path.exists():
                missing_files.append(str(path))
    else:
        warnings.append("missing:scheduled_observation_dir")

    if int(candidate_counts.get("submitted", 0)) > 0:
        any_run_summary = _first_existing(list(approved_root.glob("*/summary.json")))
        if any_run_summary is None:
            warnings.append("submitted_candidates_without_approved_run_summary")
            recommendations.append("check_approved_candidate_runs_integrity")

    if invalid_json_files:
        recommendations.append("fix_invalid_json_files")
    if missing_files:
        recommendations.append("rebuild_missing_artifacts")
    if not latest_run_path:
        recommendations.append("run_submit_approved_candidates_dry_run")
    if not latest_observation_path:
        recommendations.append("run_observation_shift_or_scheduler")

    fail_on_missing = bool(strict)
    ok = True
    if invalid_json_files:
        ok = False
    if fail_on_missing and missing_files:
        ok = False
    if fail_on_missing and empty_files:
        ok = False

    summary = {
        "ok": ok,
        "logs_dir": str(root),
        "date": target_date,
        "missing_files": sorted(set(missing_files)),
        "optional_missing_files": sorted(set(optional_missing_files)),
        "invalid_json_files": sorted(set(invalid_json_files)),
        "empty_files": sorted(set(empty_files)),
        "latest_approved_run": latest_run_path,
        "latest_approved_run_is_noop": latest_approved_run_is_noop,
        "latest_observation_shift": latest_observation_path,
        "latest_scheduled_observation": latest_scheduled_path,
        "candidate_counts": candidate_counts,
        "risk_event_counts": risk_event_counts,
        "scoped_risk_event_counts": scoped_risk_event_counts,
        "approved_run_summary": approved_run_summary,
        "warnings": sorted(set(warnings)),
        "recommendations": sorted(set(recommendations)),
        "strict": bool(strict),
    }
    summary["verdict"] = classify_validation_verdict(
        ok=summary["ok"],
        missing_files=list(summary["missing_files"]),
        invalid_json_files=list(summary["invalid_json_files"]),
        empty_files=list(summary["empty_files"]),
        warnings=list(summary["warnings"]),
    )
    return summary


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate testnet execution artifacts and audit-chain completeness")
    parser.add_argument("--logs-dir", default="logs")
    parser.add_argument("--date", default="")
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--json", action="store_true")
    return parser


def _print_human(summary: dict[str, Any]) -> None:
    print(f"ok={summary.get('ok', False)}")
    print(f"logs_dir={summary.get('logs_dir', '')}")
    print(f"date={summary.get('date', '')}")
    print(f"latest_approved_run={summary.get('latest_approved_run', '')}")
    print(f"missing_files={len(summary.get('missing_files', []))}")
    print(f"optional_missing_files={len(summary.get('optional_missing_files', []))}")
    print(f"invalid_json_files={len(summary.get('invalid_json_files', []))}")
    print(f"empty_files={len(summary.get('empty_files', []))}")
    print(f"recommendations={json.dumps(summary.get('recommendations', []), ensure_ascii=False)}")


def main() -> None:
    args = build_arg_parser().parse_args()
    summary = validate_testnet_artifacts(
        logs_dir=str(args.logs_dir or "logs"),
        date=str(args.date or ""),
        strict=bool(args.strict),
    )
    if bool(args.json):
        print(json.dumps(summary, ensure_ascii=False))
        return
    _print_human(summary)


if __name__ == "__main__":
    main()
