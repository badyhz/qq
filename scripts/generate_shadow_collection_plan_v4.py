from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _to_bool(value: Any) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "y"}


def _collect_missing_inputs(
    *,
    blocker_attribution_json: str,
    sample_quality_audit_json: str,
    phase_control_v3_json: str,
) -> list[str]:
    missing: list[str] = []
    for label, p in [
        ("blocker_attribution_json", Path(blocker_attribution_json)),
        ("sample_quality_audit_json", Path(sample_quality_audit_json)),
        ("phase_control_v3_json", Path(phase_control_v3_json)),
    ]:
        if not p.exists():
            missing.append(label)
    return missing


def generate_shadow_collection_plan_v4(
    *,
    blocker_attribution_json: str = "reports/readiness_blocker_attribution/readiness_blocker_attribution.json",
    sample_quality_audit_json: str = "reports/shadow_sample_quality_audit/shadow_sample_quality_audit.json",
    phase_control_v3_json: str = "reports/phase_control_v3/shadow_phase_control_report_v3.json",
    output_dir: str = "reports/shadow_collection_plan_v4",
) -> dict[str, Any]:
    missing_inputs = _collect_missing_inputs(
        blocker_attribution_json=blocker_attribution_json,
        sample_quality_audit_json=sample_quality_audit_json,
        phase_control_v3_json=phase_control_v3_json,
    )

    allowed_mode = "SHADOW_ONLY"
    submit_permission = "NO_SUBMIT"
    testnet_submit_allowed = False
    real_submit_allowed = False
    submit_attempted = False
    cancel_attempted = False
    flatten_attempted = False

    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    blocker_attr = _read_json(Path(blocker_attribution_json))
    sample_quality = _read_json(Path(sample_quality_audit_json))
    phase_ctrl_v3 = _read_json(Path(phase_control_v3_json))

    plan_version = "v4"
    total_target_samples = 0
    minimum_required_new_samples = 0
    plan_ready = False
    still_not_ready = True
    collection_items: list[dict[str, Any]] = []
    quality_requirements = {
        "dedupe_required": True,
        "required_fields_required": True,
        "timestamp_validation_required": True,
    }

    # Extract blockers
    blockers = blocker_attr.get("blockers", []) if isinstance(blocker_attr.get("blockers"), list) else []
    still_not_ready = _to_bool(blocker_attr.get("still_not_ready", True))

    # Build collection plan based on blockers
    sample_gap_remaining = 0
    for b in blockers:
        code = b.get("code", "")
        if "SAMPLE_GAP" in code:
            sample_gap_remaining = 10
            collection_items.append({
                "symbol": "BTCUSDT",
                "timeframe": "1h",
                "setup": "continue_remediation_loops",
                "target_samples": sample_gap_remaining,
                "priority": "HIGH",
                "reason": "close_sample_gap",
            })
        elif "CONVERGENCE" in code:
            collection_items.append({
                "symbol": "ETHUSDT",
                "timeframe": "1h",
                "setup": "convergence_validation",
                "target_samples": 5,
                "priority": "MEDIUM",
                "reason": "confirm_convergence",
            })
        elif "SAMPLE_QUALITY" in code:
            collection_items.append({
                "symbol": "BTCUSDT",
                "timeframe": "4h",
                "setup": "quality_improvement",
                "target_samples": 3,
                "priority": "HIGH",
                "reason": "improve_sample_quality",
            })
        elif "REMEDIATION" in code:
            collection_items.append({
                "symbol": "BTCUSDT",
                "timeframe": "1h",
                "setup": "remediation_focus",
                "target_samples": 8,
                "priority": "HIGH",
                "reason": "improve_remediation_effectiveness",
            })

    if not collection_items:
        # Default plan if no blockers identified
        collection_items.append({
            "symbol": "BTCUSDT",
            "timeframe": "1h",
            "setup": "default_observation",
            "target_samples": 5,
            "priority": "MEDIUM",
            "reason": "continue_shadow_observation",
        })

    # Calculate total target samples
    total_target_samples = sum(item.get("target_samples", 0) for item in collection_items)
    minimum_required_new_samples = min(total_target_samples, max(1, total_target_samples // 2))

    # Determine plan_ready
    plan_ready = True
    if missing_inputs:
        plan_ready = False

    # Determine final verdict
    final_verdict = "PASS"
    if missing_inputs:
        final_verdict = "PARTIAL"

    # Safety overrides
    if testnet_submit_allowed or real_submit_allowed:
        final_verdict = "FAIL"
        plan_ready = False
        still_not_ready = True

    report: dict[str, Any] = {
        "task_id": "T378",
        "phase": "SHADOW_COLLECTION_PLAN_V4",
        "allowed_mode": allowed_mode,
        "submit_permission": submit_permission,
        "testnet_submit_allowed": testnet_submit_allowed,
        "real_submit_allowed": real_submit_allowed,
        "submit_attempted": submit_attempted,
        "cancel_attempted": cancel_attempted,
        "flatten_attempted": flatten_attempted,
        "plan_version": plan_version,
        "total_target_samples": total_target_samples,
        "collection_items": collection_items,
        "minimum_required_new_samples": minimum_required_new_samples,
        "quality_requirements": quality_requirements,
        "plan_ready": plan_ready,
        "still_not_ready": still_not_ready,
        "missing_inputs": missing_inputs,
        "final_verdict": final_verdict,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
    }

    report_json = out_dir / "shadow_collection_plan_v4.json"
    summary_md = out_dir / "summary.md"

    report_json.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    md_lines = [
        "# Shadow Collection Plan V4",
        "",
        f"- task_id: {report['task_id']}",
        f"- phase: {report['phase']}",
        f"- final_verdict: {report['final_verdict']}",
        f"- plan_version: {report['plan_version']}",
        f"- total_target_samples: {report['total_target_samples']}",
        f"- collection_items_count: {len(report['collection_items'])}",
        f"- minimum_required_new_samples: {report['minimum_required_new_samples']}",
        f"- quality_requirements: {json.dumps(report['quality_requirements'])}",
        f"- plan_ready: {report['plan_ready']}",
        f"- still_not_ready: {report['still_not_ready']}",
        f"- missing_inputs: {report['missing_inputs']}",
        "- allowed_mode: SHADOW_ONLY",
        "- submit_permission: NO_SUBMIT",
        "- testnet_submit_allowed: false",
        "- real_submit_allowed: false",
        "- submit_attempted: false",
        "- cancel_attempted: false",
        "- flatten_attempted: false",
    ]
    summary_md.write_text("\n".join(md_lines) + "\n", encoding="utf-8")

    return report


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate shadow collection plan v4")
    parser.add_argument("--blocker-attribution-json", default="reports/readiness_blocker_attribution/readiness_blocker_attribution.json")
    parser.add_argument("--sample-quality-audit-json", default="reports/shadow_sample_quality_audit/shadow_sample_quality_audit.json")
    parser.add_argument("--phase-control-v3-json", default="reports/phase_control_v3/shadow_phase_control_report_v3.json")
    parser.add_argument("--output-dir", default="reports/shadow_collection_plan_v4")
    parser.add_argument("--json", action="store_true")
    return parser


def main() -> None:
    args = build_arg_parser().parse_args()
    result = generate_shadow_collection_plan_v4(
        blocker_attribution_json=str(args.blocker_attribution_json or "reports/readiness_blocker_attribution/readiness_blocker_attribution.json"),
        sample_quality_audit_json=str(args.sample_quality_audit_json or "reports/shadow_sample_quality_audit/shadow_sample_quality_audit.json"),
        phase_control_v3_json=str(args.phase_control_v3_json or "reports/phase_control_v3/shadow_phase_control_report_v3.json"),
        output_dir=str(args.output_dir or "reports/shadow_collection_plan_v4"),
    )
    if bool(args.json):
        print(json.dumps(result, ensure_ascii=False))
        return
    print(f"task_id={result.get('task_id','')}")
    print(f"final_verdict={result.get('final_verdict','')}")
    print(f"plan_ready={result.get('plan_ready',False)}")


if __name__ == "__main__":
    main()
