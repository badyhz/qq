"""Readonly guard status report generator.

Imports core.execution_guards and emits a structured report.
No network, no subprocess, no trading imports, no file write by default.
"""
from __future__ import annotations

import argparse
import json
import sys
from typing import Any

from core.execution_guards import (
    build_execution_guard_report,
    normalize_execution_mode,
    parse_symbol_allowlist,
    read_bool_env,
)
from core.execution_guard_schema import validate_guard_report


def _resolve_mode(args_mode: str | None) -> str | None:
    if not args_mode:
        return None
    try:
        return normalize_execution_mode(args_mode)
    except ValueError:
        return None


def generate_report(
    *,
    mode: str | None,
    action: str,
    symbol: str = "",
    symbol_allowlist_raw: str | list[str] | None = None,
    capability: bool = False,
    cli_allow: bool = False,
    manual_confirm: bool = False,
) -> dict[str, Any]:
    allowlist = parse_symbol_allowlist(symbol_allowlist_raw)

    env_overrides: dict[str, bool] = {}
    for key in ("QQ_NO_SUBMIT", "QQ_NO_CANCEL", "QQ_NO_FLATTEN", "QQ_NO_LIVE"):
        env_overrides[key] = read_bool_env(key)
    env_overrides["QQ_REQUIRE_DRY_RUN"] = read_bool_env("QQ_REQUIRE_DRY_RUN")

    resolved_mode = _resolve_mode(mode)
    if resolved_mode is None:
        return {
            "status": "BLOCKED",
            "reason": "FAIL_CLOSED",
            "mode": "",
            "action": action,
            "symbol": symbol.upper(),
            "env_overrides": env_overrides,
            "layers": {
                "mode_valid": False,
                "capability": capability,
                "cli_allow": cli_allow,
                "manual_confirm": manual_confirm,
                "symbol_in_allowlist": (
                    not allowlist or symbol.upper() in allowlist
                ),
            },
        }

    if resolved_mode == "live":
        return {
            "status": "BLOCKED",
            "reason": "LIVE_MODE_NOT_ALLOWED",
            "mode": resolved_mode,
            "action": action,
            "symbol": symbol.upper(),
            "env_overrides": env_overrides,
            "layers": {
                "mode_valid": True,
                "capability": capability,
                "cli_allow": cli_allow,
                "manual_confirm": manual_confirm,
                "symbol_in_allowlist": (
                    not allowlist or symbol.upper() in allowlist
                ),
            },
        }

    report = build_execution_guard_report(
        mode=resolved_mode,
        action=action,
        symbol=symbol,
        symbol_allowlist=allowlist,
        env_overrides=env_overrides,
        capability=capability,
        cli_allow=cli_allow,
        manual_confirm=manual_confirm,
    )
    report["status"] = "OK"
    report["env_overrides"] = env_overrides
    return report


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="Generate execution guard status report"
    )
    parser.add_argument("--mode", default=None, help="Execution mode")
    parser.add_argument("--symbol", default="", help="Symbol to check")
    parser.add_argument(
        "--action",
        default="submit",
        choices=["submit", "cancel", "flatten"],
        help="Action to check",
    )
    parser.add_argument(
        "--capability", action="store_true", default=False
    )
    parser.add_argument("--cli-allow", action="store_true", default=False)
    parser.add_argument(
        "--manual-confirm", action="store_true", default=False
    )
    parser.add_argument(
        "--symbol-allowlist", default=None, help="Comma-separated symbols"
    )
    parser.add_argument("--json", action="store_true", default=False)
    parser.add_argument("--compact", action="store_true", default=False)
    parser.add_argument("--pretty", action="store_true", default=False)
    parser.add_argument("--output", default=None, help="Output file path")
    args = parser.parse_args(argv)

    report = generate_report(
        mode=args.mode,
        action=args.action,
        symbol=args.symbol,
        symbol_allowlist_raw=args.symbol_allowlist,
        capability=args.capability,
        cli_allow=args.cli_allow,
        manual_confirm=args.manual_confirm,
    )

    try:
        validate_guard_report(report)
    except (ValueError, KeyError, TypeError):
        report = {
            "status": "BLOCKED",
            "reason": "SCHEMA_VALIDATION_FAILED",
            "mode": report.get("mode", ""),
            "action": args.action,
            "symbol": (args.symbol or "").upper(),
            "env_overrides": report.get("env_overrides", {}),
        }

    if args.compact:
        output_str = json.dumps(report, separators=(",", ":"), sort_keys=True)
    else:
        output_str = json.dumps(report, indent=2, sort_keys=True)

    if args.output:
        with open(args.output, "w") as f:
            f.write(output_str + "\n")
    else:
        print(output_str)


if __name__ == "__main__":
    main()
