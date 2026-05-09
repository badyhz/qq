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


def _collect_missing_inputs(
    *,
    readiness_blocker_attribution_json: str,
    shadow_only_backlog_prioritization_json: str,
) -> list[str]:
    missing: list[str] = []
    if not Path(readiness_blocker_attribution_json).exists():
        missing.append("readiness_blocker_attribution_json")
    if not Path(shadow_only_backlog_prioritization_json).exists():
        missing.append("shadow_only_backlog_prioritization_json")
    return missing


def map_readiness_blockers_to_actions(
    *,
    readiness_blocker_attribution_json: str = "reports/readiness_blocker_attribution/readiness_blocker_attribution.json",
    shadow_only_backlog_prioritization_json: str = "reports/shadow_only_backlog_prioritization/shadow_only_backlog_prioritization.json",
    output_dir: str = "reports/readiness_blocker_to_action_map_v1",
) -> dict[str, Any]:
    missing_inputs = _collect_missing_inputs(
        readiness_blocker_attribution_json=readiness_blocker_attribution_json,
        shadow_only_backlog_prioritization_json=shadow_only_backlog_prioritization_json,
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

    blocker_attr = _read_json(Path(readiness_blocker_attribution_json))
    backlog_prio = _read_json(Path(shadow_only_backlog_prioritization_json))

    actions: list[dict[str, Any]] = []
    blocker_count = 0
    action_count = 0
    primary_action_category = "UNKNOWN"
    still_not_ready = True

    blockers = blocker_attr.get("blockers", []) if isinstance(blocker_attr.get("blockers"), list) else []
    backlog_items = backlog_prio.get("backlog_items", []) if isinstance(backlog_prio.get("backlog_items"), list) else []

    for idx, blocker in enumerate(blockers):
        code = blocker.get("code", "")
        severity = blocker.get("severity", "MEDIUM")
        priority = severity
        category = "READINESS"

        if "SAFETY" in code:
            category = "SAFETY"
            priority = "CRITICAL"
        elif "SAMPLE_QUALITY" in code:
            category = "DATA_QUALITY"
        elif "SAMPLE" in code:
            category = "SAMPLE_COLLECTION"
        elif "CONVERGENCE" in code:
            category = "CONVERGENCE"

        action = {
            "action_id": f"ACTION-{idx+1:03d}",
            "source_blocker": code,
            "category": category,
            "priority": priority,
            "shadow_only": True,
            "recommended_task_range": "T386-T390",
            "acceptance_hint": blocker.get("recommended_action", ""),
        }
        actions.append(action)

    for idx, item in enumerate(backlog_items):
        exists = any(a["source_blocker"] == item.get("id") for a in actions)
        if not exists:
            category = item.get("category", "READINESS")
            priority = item.get("priority", "MEDIUM")
            if priority == "CRITICAL":
                priority = "CRITICAL"
            action = {
                "action_id": f"ACTION-B{idx+1:03d}",
                "source_blocker": item.get("id", ""),
                "category": category,
                "priority": priority,
                "shadow_only": True,
                "recommended_task_range": "T386-T390",
                "acceptance_hint": item.get("acceptance_hint", ""),
            }
            actions.append(action)

    blocker_count = len(blockers)
    action_count = len(actions)

    if actions:
        high_actions = [a for a in actions if a["priority"] in ("HIGH", "CRITICAL")]
        if high_actions:
            primary_action_category = high_actions[0]["category"]
        else:
            primary_action_category = actions[0]["category"]

    still_not_ready = blocker_attr.get("still_not_ready", True)
    if not still_not_ready:
        still_not_ready = backlog_prio.get("still_not_ready", True)

    final_verdict = "PASS"
    if missing_inputs:
        final_verdict = "PARTIAL"

    if any(a["priority"] == "CRITICAL" and a["category"] == "SAFETY" for a in actions):
        final_verdict = "FAIL"

    if testnet_submit_allowed or real_submit_allowed:
        final_verdict = "FAIL"

    report: dict[str, Any] = {
        "task_id": "T383",
        "phase": "READINESS_BLOCKER_TO_ACTION_MAP_V1",
        "allowed_mode": allowed_mode,
        "submit_permission": submit_permission,
        "testnet_submit_allowed": testnet_submit_allowed,
        "real_submit_allowed": real_submit_allowed,
        "submit_attempted": submit_attempted,
        "cancel_attempted": cancel_attempted,
        "flatten_attempted": flatten_attempted,
        "blocker_count": blocker_count,
        "action_count": action_count,
        "primary_action_category": primary_action_category,
        "actions": actions,
        "still_not_ready": still_not_ready,
        "missing_inputs": missing_inputs,
        "final_verdict": final_verdict,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
    }

    report_json = out_dir / "readiness_blocker_to_action_map_v1.json"
    summary_md = out_dir / "summary.md"

    report_json.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    md_lines = [
        "# Readiness Blocker to Action Map V1",
        "",
        f"- task_id: {report['task_id']}",
        f"- phase: {report['phase']}",
        f"- final_verdict: {report['final_verdict']}",
        f"- blocker_count: {report['blocker_count']}",
        f"- action_count: {report['action_count']}",
        f"- primary_action_category: {report['primary_action_category']}",
        f"- actions count: {len(report['actions'])}",
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
    parser = argparse.ArgumentParser(description="Map readiness blockers to actions")
    parser.add_argument("--readiness-blocker-attribution-json", default="reports/readiness_blocker_attribution/readiness_blocker_attribution.json")
    parser.add_argument("--shadow-only-backlog-prioritization-json", default="reports/shadow_only_backlog_prioritization/shadow_only_backlog_prioritization.json")
    parser.add_argument("--output-dir", default="reports/readiness_blocker_to_action_map_v1")
    parser.add_argument("--json", action="store_true")
    return parser


def main() -> None:
    args = build_arg_parser().parse_args()
    result = map_readiness_blockers_to_actions(
        readiness_blocker_attribution_json=str(args.readiness_blocker_attribution_json or "reports/readiness_blocker_attribution/readiness_blocker_attribution.json"),
        shadow_only_backlog_prioritization_json=str(args.shadow_only_backlog_prioritization_json or "reports/shadow_only_backlog_prioritization/shadow_only_backlog_prioritization.json"),
        output_dir=str(args.output_dir or "reports/readiness_blocker_to_action_map_v1"),
    )
    if bool(args.json):
        print(json.dumps(result, ensure_ascii=False))
        return
    print(f"task_id={result.get('task_id','')}")
    print(f"final_verdict={result.get('final_verdict','')}")
    print(f"action_count={result.get('action_count',0)}")


if __name__ == "__main__":
    main()
