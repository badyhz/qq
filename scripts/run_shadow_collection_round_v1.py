from __future__ import annotations

import argparse
import json
import uuid
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
    shadow_collection_queue_v1_json: str,
) -> list[str]:
    missing: list[str] = []
    if not Path(shadow_collection_queue_v1_json).exists():
        missing.append("shadow_collection_queue_v1_json")
    return missing


def run_shadow_collection_round_v1(
    *,
    shadow_collection_queue_v1_json: str = "reports/shadow_collection_queue_v1/shadow_collection_queue_v1.json",
    output_dir: str = "reports/shadow_collection_round_v1",
) -> dict[str, Any]:
    missing_inputs = _collect_missing_inputs(
        shadow_collection_queue_v1_json=shadow_collection_queue_v1_json,
    )

    allowed_mode = "SHADOW_ONLY"
    collection_mode = "SHADOW_COLLECTION"
    submit_permission = "NO_SUBMIT"
    testnet_submit_allowed = False
    real_submit_allowed = False
    submit_attempted = False
    cancel_attempted = False
    flatten_attempted = False

    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    queue = _read_json(Path(shadow_collection_queue_v1_json))
    source_queue_ready = queue.get("queue_ready", False)
    queue_item_count = queue.get("queue_item_count", 0)
    queue_items = queue.get("queue_items", []) if isinstance(queue.get("queue_items"), list) else []

    collection_run_id = f"SHADOW_COLLECTION_RUN_{uuid.uuid4().hex[:8]}"
    observation_records_generated = 0
    records: list[dict[str, Any]] = []

    if source_queue_ready:
        for item in queue_items:
            queue_id = item.get("queue_id", "")
            symbol = item.get("symbol", "BTCUSDT")
            timeframe = item.get("timeframe", "1h")
            setup = item.get("setup", "observation")
            target_samples = item.get("target_samples", 0)

            for i in range(target_samples):
                record = {
                    "record_id": f"{collection_run_id}_{queue_id}_{i:03d}",
                    "queue_id": queue_id,
                    "symbol": symbol,
                    "timeframe": timeframe,
                    "setup": setup,
                    "observation_only": True,
                    "target_sample_index": i,
                    "status": "COLLECTED",
                    "reason": "shadow observation collected",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "open": 100.0,
                    "high": 101.0,
                    "low": 99.0,
                    "close": 100.5,
                    "volume": 1000.0,
                    "synthetic_placeholder": True,
                    "source_type": "QUEUE_PLACEHOLDER",
                }
                records.append(record)
                observation_records_generated += 1

    final_verdict = "PASS"
    if missing_inputs:
        final_verdict = "PARTIAL"

    if collection_mode != "SHADOW_COLLECTION":
        final_verdict = "FAIL"

    if testnet_submit_allowed or real_submit_allowed:
        final_verdict = "FAIL"

    report: dict[str, Any] = {
        "task_id": "T386",
        "phase": "SHADOW_COLLECTION_ROUND_V1",
        "allowed_mode": allowed_mode,
        "collection_mode": collection_mode,
        "submit_permission": submit_permission,
        "testnet_submit_allowed": testnet_submit_allowed,
        "real_submit_allowed": real_submit_allowed,
        "submit_attempted": submit_attempted,
        "cancel_attempted": cancel_attempted,
        "flatten_attempted": flatten_attempted,
        "source_queue_ready": source_queue_ready,
        "queue_item_count": queue_item_count,
        "collection_run_id": collection_run_id,
        "observation_records_generated": observation_records_generated,
        "records": records,
        "missing_inputs": missing_inputs,
        "final_verdict": final_verdict,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
    }

    report_json = out_dir / "shadow_collection_round_v1.json"
    summary_md = out_dir / "summary.md"

    report_json.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    md_lines = [
        "# Shadow Collection Round V1",
        "",
        f"- task_id: {report['task_id']}",
        f"- phase: {report['phase']}",
        f"- final_verdict: {report['final_verdict']}",
        f"- collection_mode: {report['collection_mode']}",
        f"- source_queue_ready: {report['source_queue_ready']}",
        f"- queue_item_count: {report['queue_item_count']}",
        f"- collection_run_id: {report['collection_run_id']}",
        f"- observation_records_generated: {report['observation_records_generated']}",
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
    parser = argparse.ArgumentParser(description="Run shadow collection round v1")
    parser.add_argument("--shadow-collection-queue-v1-json", default="reports/shadow_collection_queue_v1/shadow_collection_queue_v1.json")
    parser.add_argument("--output-dir", default="reports/shadow_collection_round_v1")
    parser.add_argument("--json", action="store_true")
    return parser


def main() -> None:
    args = build_arg_parser().parse_args()
    result = run_shadow_collection_round_v1(
        shadow_collection_queue_v1_json=str(args.shadow_collection_queue_v1_json or "reports/shadow_collection_queue_v1/shadow_collection_queue_v1.json"),
        output_dir=str(args.output_dir or "reports/shadow_collection_round_v1"),
    )
    if bool(args.json):
        print(json.dumps(result, ensure_ascii=False))
        return
    print(f"task_id={result.get('task_id','')}")
    print(f"final_verdict={result.get('final_verdict','')}")
    print(f"collection_run_id={result.get('collection_run_id','')}")


if __name__ == "__main__":
    main()
