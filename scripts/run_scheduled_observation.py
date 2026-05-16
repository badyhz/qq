from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from core.risk_event_logger import DEFAULT_RISK_EVENTS_PATH, log_risk_event
from scripts.build_execution_candidates import build_execution_candidates
from scripts.run_observation_shift import run_observation_shift
from scripts.send_notification_digest import run_notification_digest
from scripts.strategy_edge_common import read_jsonl_rows


def _now_run_id() -> str:
    return datetime.now(timezone.utc).strftime("sched_%Y%m%d_%H%M%S")


def _to_bool(value: Any, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    text = str(value or "").strip().lower()
    if text in {"1", "true", "yes", "y", "on"}:
        return True
    if text in {"0", "false", "no", "n", "off"}:
        return False
    return bool(default)


def _parse_symbols(value: str) -> list[str]:
    return [item.strip().upper() for item in str(value or "").split(",") if item.strip()]


def _risk_event_counts(path: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    try:
        rows = read_jsonl_rows(path)
    except Exception:
        return counts
    for row in rows:
        severity = str(row.get("severity", "UNKNOWN")).upper()
        counts[severity] = int(counts.get(severity, 0)) + 1
    return counts


def _write_summary_markdown(path: Path, summary: dict[str, Any]) -> None:
    lines = [
        "# Scheduled Observation Summary",
        "",
        f"- run_id: {summary.get('run_id', '')}",
        f"- env: {summary.get('env', '')}",
        f"- dry_run: {summary.get('dry_run', True)}",
        f"- overall_status: {summary.get('overall_status', '')}",
        f"- observation_shift_id: {summary.get('observation_shift_id', '')}",
        f"- candidates_created: {summary.get('candidates_created', 0)}",
        f"- candidates_skipped: {summary.get('candidates_skipped', 0)}",
        f"- notification_status: {summary.get('notification_status', 'not_requested')}",
        "",
        "## Recommended Actions",
    ]
    for action in list(summary.get("recommended_actions", [])):
        lines.append(f"- {action}")
    lines.extend(["", "## Step Results"])
    for step in list(summary.get("steps", [])):
        lines.append(f"- {step.get('name', '')}: {step.get('status', '')} {step.get('error', '')}".rstrip())
    lines.extend(["", "## Generated Files"])
    for item in list(summary.get("generated_files", [])):
        lines.append(f"- {item}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _step_call(
    *,
    name: str,
    summary: dict[str, Any],
    fn: Callable[[], dict[str, Any]],
    env: str,
    risk_events_jsonl: str,
    run_id: str,
) -> dict[str, Any]:
    try:
        result = fn()
        summary["steps"].append({"name": name, "status": "PASS"})
        return result if isinstance(result, dict) else {"result": result}
    except Exception as exc:
        message = str(exc)
        summary["steps"].append({"name": name, "status": "FAIL", "error": message})
        summary.setdefault("errors", []).append({"step": name, "error": message})
        log_risk_event(
            env=env,
            symbol="",
            component="run_scheduled_observation",
            event_type="SCHEDULER_RUN_FAILED",
            message=f"scheduler step failed: {name}",
            context={"error": message},
            action_required="inspect_scheduler_step",
            event_scope="LOCAL_DRY_RUN",
            is_test_event=True,
            run_id=run_id,
            output_path=risk_events_jsonl,
        )
        return {"ok": False, "error": message}


def run_scheduled_observation(
    *,
    env: str = "testnet",
    symbols: str = "FETUSDT,OPUSDT",
    dry_run: bool = True,
    output_dir: str = "logs/scheduled_observations",
    run_id: str = "",
    build_candidates: bool = True,
    send_digest: bool = False,
    notification_channel: str = "stdout",
    risk_events_jsonl: str = DEFAULT_RISK_EVENTS_PATH,
    candidates_jsonl: str = "logs/execution_candidates.jsonl",
    input_jsonl: str = "logs/replayed_testnet_dry_payloads_exchangeinfo.jsonl",
    state_jsonl: str = "",
    allowlist: str = "FETUSDT,OPUSDT",
    max_candidates: int = 10,
    ttl_minutes: int = 60,
    lookback_minutes: int = 120,
    base_url: str = "",
) -> dict[str, Any]:
    resolved_env = str(env or "").strip().lower()
    resolved_run_id = str(run_id or "").strip() or _now_run_id()
    run_dir = Path(output_dir) / resolved_run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    symbol_list = _parse_symbols(symbols)
    generated_files: list[str] = []

    summary: dict[str, Any] = {
        "run_id": resolved_run_id,
        "env": resolved_env,
        "dry_run": True if dry_run else True,
        "symbols": symbol_list,
        "state_source": str(state_jsonl or "MISSING"),
        "observation_shift_id": "",
        "candidates_created": 0,
        "candidates_skipped": 0,
        "notification_status": "not_requested",
        "risk_event_counts": {},
        "recommended_actions": [],
        "generated_files": generated_files,
        "overall_status": "PASS",
        "steps": [],
        "errors": [],
    }

    if resolved_env == "live":
        summary["overall_status"] = "FAIL"
        summary["recommended_actions"] = ["use_testnet_env_only"]
        summary["steps"].append({"name": "env_preflight", "status": "FAIL", "error": "live_blocked"})
        log_risk_event(
            env=resolved_env,
            symbol="",
            component="run_scheduled_observation",
            event_type="LIVE_SUBMIT_BLOCKED",
            message="scheduled observation blocked: live env is not allowed",
            context={"run_id": resolved_run_id},
            action_required="use_testnet_env_only",
            event_scope="LIVE_BLOCK_TEST",
            is_test_event=True,
            is_expected_block=True,
            run_id=resolved_run_id,
            output_path=risk_events_jsonl,
        )
    else:
        observation = _step_call(
            name="run_observation_shift",
            summary=summary,
            env=resolved_env,
            risk_events_jsonl=risk_events_jsonl,
            run_id=resolved_run_id,
            fn=lambda: run_observation_shift(
                env=resolved_env,
                symbols=",".join(symbol_list),
                shift_id=f"{resolved_run_id}_shift",
                risk_events_jsonl=risk_events_jsonl,
                candidates_jsonl=candidates_jsonl,
                output_dir=str(run_dir / "observation_shifts"),
                dry_run=True,
                lookback_minutes=int(lookback_minutes),
                state_jsonl=str(state_jsonl or ""),
            ),
        )
        summary["observation_shift_id"] = str(observation.get("shift_id", ""))
        for key in ("summary_json", "summary_md"):
            if observation.get(key):
                generated_files.append(str(observation.get(key)))
        summary["recommended_actions"] = list(observation.get("recommended_actions", []))

        preflight_unavailable = [
            row for row in list(observation.get("per_symbol_state", []))
            if str(row.get("protection_status", "")) == "preflight_unavailable"
        ]
        for row in preflight_unavailable:
            log_risk_event(
                env=resolved_env,
                symbol=str(row.get("symbol", "")),
                component="run_scheduled_observation",
                event_type="SCHEDULER_PREFLIGHT_UNAVAILABLE",
                message="scheduled observation preflight unavailable",
                context={"error_code": row.get("error_code", ""), "error_message": row.get("error_message", "")},
                action_required="check_testnet_api_key_or_network",
                event_scope="LOCAL_DRY_RUN",
                is_test_event=True,
                run_id=resolved_run_id,
                shift_id=str(observation.get("shift_id", "")),
                output_path=risk_events_jsonl,
            )

        if build_candidates:
            candidate_summary = _step_call(
                name="build_execution_candidates",
                summary=summary,
                env=resolved_env,
                risk_events_jsonl=risk_events_jsonl,
                run_id=resolved_run_id,
                fn=lambda: build_execution_candidates(
                    env=resolved_env,
                    input_jsonl=input_jsonl,
                    output_jsonl=candidates_jsonl,
                    symbols=",".join(symbol_list),
                    allowlist=allowlist,
                    max_candidates=int(max_candidates),
                    ttl_minutes=int(ttl_minutes),
                    dry_run=True,
                    json_summary=False,
                    base_url=base_url,
                ),
            )
            summary["candidates_created"] = int(candidate_summary.get("candidates_created", 0) or 0)
            summary["candidates_skipped"] = int(candidate_summary.get("candidates_skipped", 0) or 0)
        else:
            summary["steps"].append({"name": "build_execution_candidates", "status": "SKIPPED"})

        if send_digest:
            digest = _step_call(
                name="send_notification_digest",
                summary=summary,
                env=resolved_env,
                risk_events_jsonl=risk_events_jsonl,
                run_id=resolved_run_id,
                fn=lambda: run_notification_digest(
                    env=resolved_env,
                    channel=notification_channel,
                    summary_md=str(observation.get("summary_md", "")),
                    risk_events_jsonl=risk_events_jsonl,
                    candidates_jsonl=candidates_jsonl,
                    acceptance_report_md="",
                    dry_run=True,
                    send=False,
                    max_events=10,
                    title="Scheduled Testnet Observation Digest",
                ),
            )
            summary["notification_status"] = str(
                dict(digest.get("notification_result", {})).get("status", "unknown")
            )
        else:
            summary["steps"].append({"name": "send_notification_digest", "status": "SKIPPED"})

        if summary.get("errors"):
            summary["overall_status"] = "PARTIAL"
        if preflight_unavailable:
            summary["overall_status"] = "PARTIAL"
            if "check_testnet_api_key_or_network" not in summary["recommended_actions"]:
                summary["recommended_actions"].append("check_testnet_api_key_or_network")

    summary["risk_event_counts"] = _risk_event_counts(risk_events_jsonl)
    summary_json = run_dir / "summary.json"
    summary_md = run_dir / "summary.md"
    generated_files.extend([str(summary_json), str(summary_md)])
    summary_json.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    _write_summary_markdown(summary_md, summary)
    summary["summary_json"] = str(summary_json)
    summary["summary_md"] = str(summary_md)
    return summary


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run one scheduled testnet observation duty cycle")
    parser.add_argument("--env", default="testnet")
    parser.add_argument("--symbols", default="FETUSDT,OPUSDT")
    parser.add_argument("--dry-run", action="store_true", default=True)
    parser.add_argument("--output-dir", default="logs/scheduled_observations")
    parser.add_argument("--run-id", default="")
    parser.add_argument("--build-candidates", default="true")
    parser.add_argument("--send-digest", default="false")
    parser.add_argument("--notification-channel", default="stdout")
    parser.add_argument("--risk-events-jsonl", default=DEFAULT_RISK_EVENTS_PATH)
    parser.add_argument("--candidates-jsonl", default="logs/execution_candidates.jsonl")
    parser.add_argument("--input-jsonl", default="logs/replayed_testnet_dry_payloads_exchangeinfo.jsonl")
    parser.add_argument("--state-jsonl", default="")
    parser.add_argument("--allowlist", default="FETUSDT,OPUSDT")
    parser.add_argument("--max-candidates", type=int, default=10)
    parser.add_argument("--ttl-minutes", type=int, default=60)
    parser.add_argument("--lookback-minutes", type=int, default=120)
    parser.add_argument("--base-url", default="")
    parser.add_argument("--json", action="store_true")
    return parser


def main() -> None:
    args = build_arg_parser().parse_args()
    result = run_scheduled_observation(
        env=str(args.env or "testnet"),
        symbols=str(args.symbols or "FETUSDT,OPUSDT"),
        dry_run=True,
        output_dir=str(args.output_dir or "logs/scheduled_observations"),
        run_id=str(args.run_id or ""),
        build_candidates=_to_bool(args.build_candidates, default=True),
        send_digest=_to_bool(args.send_digest, default=False),
        notification_channel=str(args.notification_channel or "stdout"),
        risk_events_jsonl=str(args.risk_events_jsonl or DEFAULT_RISK_EVENTS_PATH),
        candidates_jsonl=str(args.candidates_jsonl or "logs/execution_candidates.jsonl"),
        input_jsonl=str(args.input_jsonl or "logs/replayed_testnet_dry_payloads_exchangeinfo.jsonl"),
        state_jsonl=str(args.state_jsonl or ""),
        allowlist=str(args.allowlist or "FETUSDT,OPUSDT"),
        max_candidates=int(args.max_candidates or 10),
        ttl_minutes=int(args.ttl_minutes or 60),
        lookback_minutes=int(args.lookback_minutes or 120),
        base_url=str(args.base_url or ""),
    )
    if bool(args.json):
        print(json.dumps(result, ensure_ascii=False))
        return
    print(f"run_id={result.get('run_id', '')}")
    print(f"overall_status={result.get('overall_status', '')}")
    print(f"summary_json={result.get('summary_json', '')}")
    print(f"summary_md={result.get('summary_md', '')}")


if __name__ == "__main__":
    main()
