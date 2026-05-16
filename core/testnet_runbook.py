from __future__ import annotations

from typing import Any


def build_testnet_runbook(
    *,
    mode: str,
    environment: str,
    endpoint: str,
    connector_available: bool,
    symbol: str = "BTCUSDT",
) -> dict[str, Any]:
    normalized_mode = str(mode or "unknown").strip().lower()
    normalized_environment = str(environment or "unknown").strip().lower()
    normalized_symbol = str(symbol or "BTCUSDT").strip().upper() or "BTCUSDT"
    is_testnet = normalized_environment in {"testnet", "sandbox"}

    prerequisites = [
        {
            "name": "mode_check",
            "ok": normalized_mode == "live",
            "message": "Execution mode should be `live` when running testnet connector paths.",
        },
        {
            "name": "environment_check",
            "ok": is_testnet,
            "message": "Connector environment must be `testnet` or `sandbox`.",
        },
        {
            "name": "connector_check",
            "ok": bool(connector_available),
            "message": "Broker connector must be injected and available.",
        },
        {
            "name": "auth_material_check",
            "ok": True,
            "message": "API key/secret should be configured for signed account probes.",
        },
        {
            "name": "endpoint_check",
            "ok": endpoint != "",
            "message": "Endpoint should point to Binance testnet/sandbox host.",
        },
    ]

    step_list = [
        {
            "id": 1,
            "step": "identify_mode_and_environment",
            "description": "Verify current mode and environment are not dry-run/live-mainnet mix.",
        },
        {
            "id": 2,
            "step": "run_preflight_checks",
            "description": "Run preflight gate; stop if blocking issues exist.",
        },
        {
            "id": 3,
            "step": "run_testnet_connectivity_probe",
            "description": "Probe ping/time/account/exchangeInfo/auth pipeline for testnet.",
        },
        {
            "id": 4,
            "step": "run_account_and_rules_sync",
            "description": f"Refresh account snapshot and sync symbol rules for {normalized_symbol}.",
        },
        {
            "id": 5,
            "step": "run_testnet_order_smoke",
            "description": "Execute small-size submit/status/update/cancel smoke cycle.",
        },
        {
            "id": 6,
            "step": "review_failures_and_snapshots",
            "description": "Review failure snapshots and run review before deciding retry.",
        },
    ]

    blocking_issues: list[dict[str, str]] = []
    if normalized_mode == "dry-run":
        blocking_issues.append(
            {
                "code": "dry_run_mode_not_testnet",
                "message": "Current mode is dry-run; testnet real connectivity cannot be validated.",
            }
        )
    if not is_testnet:
        blocking_issues.append(
            {
                "code": "environment_not_testnet",
                "message": f"Current environment is {normalized_environment or 'unknown'}, not testnet/sandbox.",
            }
        )
    if not connector_available:
        blocking_issues.append(
            {
                "code": "connector_missing",
                "message": "Connector is missing/unavailable for testnet probing.",
            }
        )

    stop_conditions = [
        "Any preflight blocking issue appears.",
        "Connectivity probe returns auth/signing/endpoint failure.",
        "Account snapshot or exchangeInfo probe fails.",
        "Order smoke submit/status/cancel/update path returns blocking issues.",
        "Runtime status enters ERROR.",
    ]

    next_actions = [
        "retry_testnet_probe",
        "retry_testnet_order_smoke",
        "inspect_auth",
        "inspect_endpoint",
        "inspect_symbol_rules",
        "do_not_start_live",
    ]
    if blocking_issues:
        next_actions = ["retry_testnet_probe", "do_not_start_live"]

    return {
        "title": "Testnet Live Connectivity & Order Smoke Runbook",
        "mode": normalized_mode,
        "environment": normalized_environment,
        "endpoint": str(endpoint or ""),
        "prerequisites": prerequisites,
        "step_list": step_list,
        "stop_conditions": stop_conditions,
        "next_actions": next_actions,
        "blocking_issues": blocking_issues,
        "safety_notice": "Do not switch directly to real-money live trading based on this runbook alone.",
    }


def format_testnet_runbook(runbook: dict[str, Any]) -> str:
    rows = dict(runbook or {})
    lines = [
        f"title: {rows.get('title', '')}",
        f"mode: {rows.get('mode', '')}",
        f"environment: {rows.get('environment', '')}",
        f"endpoint: {rows.get('endpoint', '')}",
        "",
        "prerequisites:",
    ]
    for item in rows.get("prerequisites", []):
        if not isinstance(item, dict):
            continue
        status = "OK" if bool(item.get("ok", False)) else "BLOCK"
        lines.append(f"- [{status}] {item.get('name', '')}: {item.get('message', '')}")
    lines.append("")
    lines.append("step_list:")
    for item in rows.get("step_list", []):
        if not isinstance(item, dict):
            continue
        lines.append(f"- {item.get('id', '')}. {item.get('step', '')}: {item.get('description', '')}")
    lines.append("")
    lines.append("stop_conditions:")
    for condition in rows.get("stop_conditions", []):
        lines.append(f"- {condition}")
    lines.append("")
    lines.append("next_actions:")
    for action in rows.get("next_actions", []):
        lines.append(f"- {action}")
    lines.append("")
    lines.append(f"safety_notice: {rows.get('safety_notice', '')}")
    return "\n".join(lines)
