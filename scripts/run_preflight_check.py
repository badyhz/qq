#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import logging
import os
from typing import Any, Optional

from core.binance_connector import BinanceConnector
from core.execution import ExecutionEngine
from core.order_manager import OrderManager


def validate_preflight_mode(*, mode: str, environment: str, connector_enabled: bool) -> list[str]:
    resolved_mode = str(mode or "").strip().lower()
    resolved_env = str(environment or "").strip().lower()
    issues: list[str] = []

    if resolved_mode == "live":
        issues.append("mode_live_blocked")

    if bool(connector_enabled):
        if resolved_env not in {"testnet", "sandbox"}:
            issues.append("connector_environment_not_testnet_or_sandbox")

    if resolved_mode == "dry-run" and bool(connector_enabled):
        issues.append("dry_run_connector_not_allowed")

    return issues


class _NoopExchange:
    def is_enabled(self) -> bool:
        return False

    def place_short_bracket(self, *_args: Any, **_kwargs: Any) -> dict[str, Any]:
        return {"accepted": False, "reason": "exchange_not_enabled"}

    def ensure_protection_orders(self, *_args: Any, **_kwargs: Any) -> list[str]:
        return []


def _build_connector(mode: str, environment: str, market_type: str):
    if mode == "dry-run":
        return None
    api_key = os.getenv("BINANCE_API_KEY", "")
    api_secret = os.getenv("BINANCE_API_SECRET", "")
    connector_mode = "testnet" if mode == "testnet" else "live"
    connector_environment = "testnet" if mode == "testnet" else environment
    return BinanceConnector(
        mode=connector_mode,
        environment=connector_environment,
        market_type=str(market_type or "spot").strip().lower() or "spot",
        enabled=True,
        api_key=api_key,
        api_secret=api_secret,
    )


def _summarize_account_failure(probe: Optional[dict[str, Any]]) -> dict[str, Any]:
    row = dict(probe or {})
    summary = {
        "market_type": str(row.get("market_type", "") or ""),
        "account_path": str(row.get("account_path", "") or ""),
        "base_url": str(row.get("base_url", "") or ""),
        "category": str(row.get("account_category", "") or ""),
        "http_status": row.get("http_status"),
        "binance_code": row.get("binance_code"),
        "binance_msg": str(row.get("binance_msg", "") or ""),
    }
    if summary["category"] and (summary["account_path"] or summary["base_url"]):
        return summary
    for item in list(row.get("raw_failures", [])):
        if not isinstance(item, dict):
            continue
        if str(item.get("step", "")) != "account":
            continue
        details = item.get("details", {})
        if not isinstance(details, dict):
            details = {}
        summary["market_type"] = str(details.get("market_type", summary["market_type"]) or "")
        summary["account_path"] = str(details.get("account_path", summary["account_path"]) or "")
        summary["base_url"] = str(details.get("base_url", summary["base_url"]) or "")
        summary["category"] = str(details.get("category", item.get("category", summary["category"])) or "")
        summary["http_status"] = details.get("http_status", summary["http_status"])
        summary["binance_code"] = details.get("binance_code", summary["binance_code"])
        summary["binance_msg"] = str(details.get("binance_msg", summary["binance_msg"]) or "")
        break
    return summary


def _format_account_failure_line(summary: dict[str, Any]) -> str:
    return (
        "- ACCOUNT_FAIL: "
        f"market_type={summary.get('market_type', '') or 'unknown'} "
        f"account_path={summary.get('account_path', '') or 'unknown'} "
        f"base_url={summary.get('base_url', '') or 'unknown'} "
        f"category={summary.get('category', '') or 'unknown'} "
        f"http_status={summary.get('http_status')} "
        f"binance_code={summary.get('binance_code')} "
        f"binance_msg={summary.get('binance_msg', '') or ''}"
    )


def run_preflight_bundle(
    *,
    mode: str,
    environment: str,
    enable_live_trading: bool,
    symbol: str = "BTCUSDT",
    market_type: str = "spot",
    connector_override: Optional[Any] = None,
) -> dict[str, Any]:
    resolved_mode = str(mode or "").strip().lower()
    resolved_environment = str(environment or "").strip().lower()
    planned_connector_enabled = bool(connector_override is not None) or (resolved_mode != "dry-run")
    guard_issues = validate_preflight_mode(
        mode=resolved_mode,
        environment=resolved_environment,
        connector_enabled=planned_connector_enabled,
    )
    if guard_issues:
        raise ValueError(";".join(guard_issues))

    engine_mode = "dry-run" if mode == "dry-run" else "live"
    config = {
        "mode": engine_mode,
        "execution": {
            "dry_run_fee_rate": 0.0004,
            "enable_live_trading": bool(enable_live_trading),
        },
        "symbol": str(symbol or "").strip().upper(),
    }
    resolved_market_type = str(market_type or "spot").strip().lower() or "spot"
    connector = (
        connector_override
        if connector_override is not None
        else _build_connector(mode, environment, resolved_market_type)
    )
    manager = OrderManager(config)
    logger = logging.getLogger("preflight-check")
    logger.setLevel(logging.INFO)
    if not logger.handlers:
        logger.addHandler(logging.StreamHandler())

    engine = ExecutionEngine(config, manager, _NoopExchange(), logger, broker_connector=connector)
    readiness = engine.run_operational_readiness_check(connector=connector)
    env = engine.get_broker_environment(connector=connector)
    connectivity = engine.check_connector_connectivity(connector=connector)
    connector_ready = bool(connectivity.get("success", False))

    probe_result: dict[str, Any] = {}
    probe_failures: list[dict[str, Any]] = []
    account_failure: dict[str, Any] = {}
    env_name = str(env.get("environment", "unknown")).strip().lower()
    if mode == "testnet" or env_name in {"testnet", "sandbox"}:
        probe_result = engine.run_testnet_connectivity_probe(
            symbols=[str(symbol or "").strip().upper()] if str(symbol or "").strip() else None,
            connector=connector,
            market_type=resolved_market_type,
        )
        account_failure = _summarize_account_failure(probe_result)
        for row in list(probe_result.get("raw_failures", [])):
            if not isinstance(row, dict):
                continue
            code = str(row.get("code", "probe_failed"))
            step = str(row.get("step", "probe"))
            message = str(row.get("message", "probe failed"))
            category = engine.classify_runtime_error(code=code, step=step, message=message, details=row.get("details", {}))
            probe_failures.append(
                {
                    "category": category,
                    "code": code,
                    "step": step,
                    "message": message,
                    "details": dict(row.get("details", {})) if isinstance(row.get("details"), dict) else {},
                }
            )
    failure_snapshots = engine.list_failure_snapshots()

    return {
        "mode": mode,
        "engine_mode": engine_mode,
        "market_type": resolved_market_type,
        "environment": env,
        "connector_available": connector is not None,
        "connector_ready": connector_ready,
        "connectivity": connectivity,
        "status": str(readiness.get("status", "NOT_READY")),
        "blocking_issues": list(readiness.get("blocking_issues", [])),
        "warnings": list(readiness.get("warnings", [])),
        "checked_items": dict(readiness.get("preflight", {}).get("checked_items", {}))
        if isinstance(readiness.get("preflight"), dict)
        else {},
        "preflight": dict(readiness.get("preflight", {})) if isinstance(readiness, dict) else {},
        "readiness": readiness,
        "probe": probe_result,
        "account_failure": account_failure,
        "probe_failures": probe_failures,
        "failure_snapshots": failure_snapshots,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run one-click operational readiness checks.")
    parser.add_argument("--mode", choices=["dry-run", "testnet", "live"], default="dry-run")
    parser.add_argument("--environment", default="live")
    parser.add_argument("--market-type", choices=["spot", "futures"], default="spot")
    parser.add_argument("--enable-live-trading", action="store_true")
    parser.add_argument("--symbol", default="BTCUSDT")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    effective_live_trading = bool(args.enable_live_trading or args.mode == "testnet")
    try:
        report = run_preflight_bundle(
            mode=args.mode,
            environment=args.environment,
            enable_live_trading=effective_live_trading,
            symbol=args.symbol,
            market_type=args.market_type,
        )
    except ValueError as exc:
        guard_report = {
            "ok": False,
            "status": "NOT_READY",
            "error": "preflight_guard_failed",
            "guard_issues": [item for item in str(exc).split(";") if item],
            "mode": str(args.mode or ""),
            "environment": str(args.environment or ""),
            "market_type": str(args.market_type or ""),
        }
        if args.json:
            print(json.dumps(guard_report, ensure_ascii=False, indent=2))
        else:
            print("status=NOT_READY")
            print(f"error={guard_report['error']}")
            print(f"guard_issues={','.join(list(guard_report.get('guard_issues', [])))}")
        return 2

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(f"status={report.get('status', 'NOT_READY')}")
        env = report.get("environment", {})
        print(
            f"mode={report.get('mode', 'unknown')} engine_mode={report.get('engine_mode', 'unknown')} "
            f"environment={env.get('environment', 'unknown')} "
            f"market_type={env.get('market_type', report.get('market_type', 'spot'))}"
        )
        print(
            "connector_available="
            f"{bool(report.get('connector_available', False))} "
            f"connector_ready={bool(report.get('connector_ready', False))}"
        )
        probe = report.get("probe", {})
        if isinstance(probe, dict) and probe:
            print(
                "probe="
                f"ok={bool(probe.get('ok', False))} "
                f"auth={bool(probe.get('auth_ok', False))} "
                f"ping={bool(probe.get('ping_ok', False))} "
                f"time={bool(probe.get('time_ok', False))} "
                f"account={bool(probe.get('account_ok', False))} "
                f"exchange_info={bool(probe.get('exchange_info_ok', False))}"
            )
            if not bool(probe.get("ok", False)):
                account_failure = _summarize_account_failure(probe)
                if str(account_failure.get("category", "")).strip():
                    print(_format_account_failure_line(account_failure))
        for issue in report.get("blocking_issues", []):
            print(f"- BLOCK: {issue.get('code', 'unknown')} | {issue.get('message', '')}")
        for warning in report.get("warnings", []):
            print(f"- WARN: {warning}")
        for failure in report.get("probe_failures", []):
            if not isinstance(failure, dict):
                continue
            print(
                f"- PROBE_FAIL: {failure.get('category', 'unknown')} "
                f"| step={failure.get('step', 'unknown')} "
                f"| code={failure.get('code', 'unknown')} "
                f"| {failure.get('message', '')}"
            )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
