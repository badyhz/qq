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
    shadow_collection_plan_v4_json: str,
) -> list[str]:
    missing: list[str] = []
    if not Path(shadow_collection_plan_v4_json).exists():
        missing.append("shadow_collection_plan_v4_json")
    return missing


def generate_shadow_collection_queue_v1(
    *,
    shadow_collection_plan_v4_json: str = "reports/shadow_collection_plan_v4/shadow_collection_plan_v4.json",
    output_dir: str = "reports/shadow_collection_queue_v1",
) -> dict[str, Any]:
    missing_inputs = _collect_missing_inputs(
        shadow_collection_plan_v4_json=shadow_collection_plan_v4_json,
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

    collection_plan = _read_json(Path(shadow_collection_plan_v4_json))
    source_plan_version = collection_plan.get("plan_version", "v4")

    queue_items: list[dict[str, Any]] = []
    total_target_samples = 0
    queue_ready = False

    if collection_plan and "collection_items" in collection_plan:
        for idx, item in enumerate(collection_plan["collection_items"]):
            queue_item = {
                "queue_id": f"QUEUE-{idx+1:03d}",
                "symbol": item.get("symbol", "BTCUSDT"),
                "timeframe": item.get("timeframe", "1h"),
                "setup": item.get("setup", "observation"),
                "target_samples": item.get("target_samples", 0),
                "priority": item.get("priority", "MEDIUM"),
                "observation_only": True,
                "reason": item.get("reason", "shadow observation"),
            }
            queue_items.append(queue_item)
            total_target_samples += queue_item["target_samples"]

    queue_item_count = len(queue_items)
    queue_ready = queue_item_count > 0 and not missing_inputs

    final_verdict = "PASS"
    if missing_inputs:
        final_verdict = "PARTIAL"

    if testnet_submit_allowed or real_submit_allowed:
        final_verdict = "FAIL"

    report: dict[str, Any] = {
        "task_id": "T381",
        "phase": "SHADOW_COLLECTION_QUEUE_V1",
        "allowed_mode": allowed_mode,
        "submit_permission": submit_permission,
        "testnet_submit_allowed": testnet_submit_allowed,
        "real_submit_allowed": real_submit_allowed,
        "submit_attempted": submit_attempted,
        "cancel_attempted": cancel_attempted,
        "flatten_attempted": flatten_attempted,
        "source_plan_version": source_plan_version,
        "queue_ready": queue_ready,
        "queue_item_count": queue_item_count,
        "total_target_samples": total_target_samples,
        "queue_items": queue_items,
        "missing_inputs": missing_inputs,
        "final_verdict": final_verdict,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
    }

    report_json = out_dir / "shadow_collection_queue_v1.json"
    summary_md = out_dir / "summary.md"

    report_json.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    md_lines = [
        "# Shadow Collection Queue V1",
        "",
        f"- task_id: {report['task_id']}",
        f"- phase: {report['phase']}",
        f"- final_verdict: {report['final_verdict']}",
        f"- source_plan_version: {report['source_plan_version']}",
        f"- queue_ready: {report['queue_ready']}",
        f"- queue_item_count: {report['queue_item_count']}",
        f"- total_target_samples: {report['total_target_samples']}",
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
    parser = argparse.ArgumentParser(description="Generate shadow collection queue v1")
    parser.add_argument("--shadow-collection-plan-v4-json", default="reports/shadow_collection_plan_v4/shadow_collection_plan_v4.json")
    parser.add_argument("--output-dir", default="reports/shadow_collection_queue_v1")
    parser.add_argument("--json", action="store_true")
    return parser


def main() -> None:
    args = build_arg_parser().parse_args()
    result = generate_shadow_collection_queue_v1(
        shadow_collection_plan_v4_json=str(args.shadow_collection_plan_v4_json or "reports/shadow_collection_plan_v4/shadow_collection_plan_v4.json"),
        output_dir=str(args.output_dir or "reports/shadow_collection_queue_v1"),
    )
    if bool(args.json):
        print(json.dumps(result, ensure_ascii=False))
        return
    print(f"task_id={result.get('task_id','')}")
    print(f"final_verdict={result.get('final_verdict','')}")
    print(f"queue_ready={result.get('queue_ready',False)}")


if __name__ == "__main__":
    main()
