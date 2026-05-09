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
    shadow_collection_plan_v4_json: str,
    sample_quality_audit_json: str,
) -> list[str]:
    missing: list[str] = []
    for label, p in [
        ("blocker_attribution_json", Path(blocker_attribution_json)),
        ("shadow_collection_plan_v4_json", Path(shadow_collection_plan_v4_json)),
        ("sample_quality_audit_json", Path(sample_quality_audit_json)),
    ]:
        if not p.exists():
            missing.append(label)
    return missing


def prioritize_shadow_only_backlog(
    *,
    blocker_attribution_json: str = "reports/readiness_blocker_attribution/readiness_blocker_attribution.json",
    shadow_collection_plan_v4_json: str = "reports/shadow_collection_plan_v4/shadow_collection_plan_v4.json",
    sample_quality_audit_json: str = "reports/shadow_sample_quality_audit/shadow_sample_quality_audit.json",
    output_dir: str = "reports/shadow_only_backlog_prioritization",
) -> dict[str, Any]:
    missing_inputs = _collect_missing_inputs(
        blocker_attribution_json=blocker_attribution_json,
        shadow_collection_plan_v4_json=shadow_collection_plan_v4_json,
        sample_quality_audit_json=sample_quality_audit_json,
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
    collection_plan = _read_json(Path(shadow_collection_plan_v4_json))
    sample_quality = _read_json(Path(sample_quality_audit_json))

    backlog_items: list[dict[str, Any]] = []
    top_priority = "UNKNOWN"
    still_not_ready = True
    backlog_count = 0
    high_priority_count = 0

    # Extract information
    blockers = blocker_attr.get("blockers", []) if isinstance(blocker_attr.get("blockers"), list) else []
    primary_blocker = str(blocker_attr.get("primary_blocker", "UNKNOWN")).strip().upper()
    still_not_ready = _to_bool(blocker_attr.get("still_not_ready", True))
    sample_quality_ready = _to_bool(sample_quality.get("sample_quality_ready", False))

    # Build backlog from blockers
    for i, b in enumerate(blockers):
        code = b.get("code", "")
        severity = b.get("severity", "MEDIUM")
        recommended_action = b.get("recommended_action", "")

        category = "READINESS"
        if "SAFETY" in code:
            category = "SAFETY"
        elif "SAMPLE" in code and "QUALITY" in code:
            category = "DATA_QUALITY"
        elif "SAMPLE" in code or "COLLECTION" in code:
            category = "SAMPLE_COLLECTION"
        elif "CONVERGENCE" in code:
            category = "CONVERGENCE"

        priority = "MEDIUM"
        if severity == "CRITICAL":
            priority = "HIGH"
        elif severity == "HIGH":
            priority = "HIGH"
        elif severity == "LOW":
            priority = "LOW"

        blocks_readiness = priority in {"HIGH", "CRITICAL"}

        backlog_items.append({
            "id": f"BACKLOG-{i+1:03d}",
            "title": f"{code}: {recommended_action}",
            "category": category,
            "priority": priority,
            "blocks_readiness": blocks_readiness,
            "recommended_task_range": "T381-T385",
            "acceptance_hint": f"resolve_{code.lower()}",
        })

    # Add collection plan items as backlog items if no blockers
    if not backlog_items:
        collection_items = collection_plan.get("collection_items", []) if isinstance(collection_plan.get("collection_items"), list) else []
        for i, item in enumerate(collection_items):
            priority = item.get("priority", "MEDIUM")
            backlog_items.append({
                "id": f"BACKLOG-{i+1:03d}",
                "title": f"Collect {item.get('target_samples', 0)} samples for {item.get('symbol')} {item.get('timeframe')}",
                "category": "SAMPLE_COLLECTION",
                "priority": priority,
                "blocks_readiness": priority == "HIGH",
                "recommended_task_range": "T381-T385",
                "acceptance_hint": f"complete_{item.get('setup')}",
            })

    # Add default backlog item if still empty
    if not backlog_items:
        backlog_items.append({
            "id": "BACKLOG-001",
            "title": "Continue shadow observation mode",
            "category": "READINESS",
            "priority": "MEDIUM",
            "blocks_readiness": True,
            "recommended_task_range": "T381-T385",
            "acceptance_hint": "continue_shadow_observation",
        })

    # Determine top priority
    if backlog_items:
        high_priority_items = [b for b in backlog_items if b["priority"] == "HIGH"]
        if high_priority_items:
            top_priority = high_priority_items[0]["category"]
        else:
            top_priority = backlog_items[0]["category"]

    # Override with primary blocker if available
    if primary_blocker != "UNKNOWN":
        if primary_blocker == "SAFETY":
            top_priority = "SAFETY"
        elif primary_blocker == "SAMPLE":
            top_priority = "SAMPLE_COLLECTION"
        elif primary_blocker == "CONVERGENCE":
            top_priority = "CONVERGENCE"
        elif primary_blocker == "REMEDIATION":
            top_priority = "READINESS"

    backlog_count = len(backlog_items)
    high_priority_count = sum(1 for b in backlog_items if b["priority"] == "HIGH")

    # Ensure at least one item blocks readiness if still_not_ready
    if still_not_ready and backlog_items and not any(b["blocks_readiness"] for b in backlog_items):
        backlog_items[0]["blocks_readiness"] = True

    # Determine final verdict
    final_verdict = "PASS"
    if top_priority == "SAFETY":
        final_verdict = "FAIL"
    elif missing_inputs:
        final_verdict = "PARTIAL"

    # Safety overrides
    if testnet_submit_allowed or real_submit_allowed:
        final_verdict = "FAIL"
        top_priority = "SAFETY"
        still_not_ready = True

    report: dict[str, Any] = {
        "task_id": "T379",
        "phase": "SHADOW_ONLY_BACKLOG_PRIORITIZATION",
        "allowed_mode": allowed_mode,
        "submit_permission": submit_permission,
        "testnet_submit_allowed": testnet_submit_allowed,
        "real_submit_allowed": real_submit_allowed,
        "submit_attempted": submit_attempted,
        "cancel_attempted": cancel_attempted,
        "flatten_attempted": flatten_attempted,
        "backlog_count": backlog_count,
        "high_priority_count": high_priority_count,
        "backlog_items": backlog_items,
        "top_priority": top_priority,
        "still_not_ready": still_not_ready,
        "missing_inputs": missing_inputs,
        "final_verdict": final_verdict,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
    }

    report_json = out_dir / "shadow_only_backlog_prioritization.json"
    summary_md = out_dir / "summary.md"

    report_json.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    md_lines = [
        "# Shadow Only Backlog Prioritization",
        "",
        f"- task_id: {report['task_id']}",
        f"- phase: {report['phase']}",
        f"- final_verdict: {report['final_verdict']}",
        f"- backlog_count: {report['backlog_count']}",
        f"- high_priority_count: {report['high_priority_count']}",
        f"- top_priority: {report['top_priority']}",
        f"- backlog_items_count: {len(report['backlog_items'])}",
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
    parser = argparse.ArgumentParser(description="Prioritize shadow only backlog")
    parser.add_argument("--blocker-attribution-json", default="reports/readiness_blocker_attribution/readiness_blocker_attribution.json")
    parser.add_argument("--shadow-collection-plan-v4-json", default="reports/shadow_collection_plan_v4/shadow_collection_plan_v4.json")
    parser.add_argument("--sample-quality-audit-json", default="reports/shadow_sample_quality_audit/shadow_sample_quality_audit.json")
    parser.add_argument("--output-dir", default="reports/shadow_only_backlog_prioritization")
    parser.add_argument("--json", action="store_true")
    return parser


def main() -> None:
    args = build_arg_parser().parse_args()
    result = prioritize_shadow_only_backlog(
        blocker_attribution_json=str(args.blocker_attribution_json or "reports/readiness_blocker_attribution/readiness_blocker_attribution.json"),
        shadow_collection_plan_v4_json=str(args.shadow_collection_plan_v4_json or "reports/shadow_collection_plan_v4/shadow_collection_plan_v4.json"),
        sample_quality_audit_json=str(args.sample_quality_audit_json or "reports/shadow_sample_quality_audit/shadow_sample_quality_audit.json"),
        output_dir=str(args.output_dir or "reports/shadow_only_backlog_prioritization"),
    )
    if bool(args.json):
        print(json.dumps(result, ensure_ascii=False))
        return
    print(f"task_id={result.get('task_id','')}")
    print(f"final_verdict={result.get('final_verdict','')}")
    print(f"top_priority={result.get('top_priority','UNKNOWN')}")


if __name__ == "__main__":
    main()
