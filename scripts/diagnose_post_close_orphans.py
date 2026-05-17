from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from scripts.check_testnet_state import check_testnet_state
from scripts.post_close_orphan_diagnosis_common import (
    build_orphan_cleanup_recommendation,
    classify_post_close_orphan_state,
    render_post_close_orphan_markdown,
)


def _parse_symbols(value: str) -> list[str]:
    return [item.strip().upper() for item in str(value or "").split(",") if item.strip()]


def _write_md(path: Path, summary: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_post_close_orphan_markdown(summary), encoding="utf-8")


def diagnose_post_close_orphans(
    *,
    env: str = "testnet",
    symbols: str = "FETUSDT,OPUSDT",
    output_md: str = "logs/post_close_orphan_diagnosis.md",
    base_url: str = "",
) -> dict[str, Any]:
    resolved_env = str(env or "").strip().lower()
    symbol_list = _parse_symbols(symbols)
    ts_utc = datetime.now(timezone.utc).isoformat()
    per_symbol: list[dict[str, Any]] = []
    orphan_symbols: list[str] = []
    partial_symbols: list[str] = []
    naked_symbols: list[str] = []
    recommended_commands: list[str] = []

    for symbol in symbol_list:
        state = check_testnet_state(env=resolved_env, symbol=symbol, base_url=base_url)
        if not bool(state.get("ok", False)):
            per_symbol.append(
                {
                    "symbol": symbol,
                    "positionAmt": 0.0,
                    "openAlgoOrdersCount": 0,
                    "protection_status": "UNKNOWN",
                    "diagnosis": "UNKNOWN",
                    "action_required": str(state.get("error_message", "state_query_failed")),
                    "error_code": str(state.get("error_code", "")),
                }
            )
            continue

        classified = classify_post_close_orphan_state(
            {
                "symbol": symbol,
                "positionAmt": state.get("positionAmt", 0.0),
                "openAlgoOrdersCount": state.get("openAlgoOrdersCount", 0),
                "protection_status": state.get("protection_status", "UNKNOWN"),
                "action_required": state.get("action_required", ""),
            }
        )
        diagnosis = str(classified.get("diagnosis", "")).strip().upper()
        if diagnosis == "ORPHAN_PROTECTION":
            orphan_symbols.append(symbol)
        elif diagnosis == "PARTIAL_PROTECTED":
            partial_symbols.append(symbol)
        elif diagnosis == "NAKED_POSITION":
            naked_symbols.append(symbol)
        recommended_commands.extend(build_orphan_cleanup_recommendation(classified))
        per_symbol.append(classified)

    verdict = "PASS"
    verdict_reason = "no_orphan_or_partial_or_naked"
    if naked_symbols or partial_symbols:
        verdict = "FAIL"
        verdict_reason = "partial_or_naked_position_detected"
    elif orphan_symbols:
        verdict = "PARTIAL"
        verdict_reason = "orphan_protection_detected"
    elif any(str(row.get("diagnosis", "")) == "UNKNOWN" for row in per_symbol):
        verdict = "PARTIAL"
        verdict_reason = "state_query_unavailable"

    summary = {
        "ok": verdict != "FAIL",
        "ts_utc": ts_utc,
        "env": resolved_env,
        "symbols": symbol_list,
        "per_symbol_diagnosis": per_symbol,
        "orphan_symbols": orphan_symbols,
        "partial_symbols": partial_symbols,
        "naked_symbols": naked_symbols,
        "recommended_commands": recommended_commands,
        "verdict": verdict,
        "verdict_reason": verdict_reason,
        "output_md": output_md,
    }
    _write_md(Path(output_md), summary)
    return summary


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Diagnose post-close orphan protection without executing cleanup")
    parser.add_argument("--env", default="testnet")
    parser.add_argument("--symbols", default="FETUSDT,OPUSDT")
    parser.add_argument("--output-md", default="logs/post_close_orphan_diagnosis.md")
    parser.add_argument("--base-url", default="")
    parser.add_argument("--json", action="store_true")
    return parser


def main() -> None:
    args = build_arg_parser().parse_args()
    result = diagnose_post_close_orphans(
        env=str(args.env or "testnet"),
        symbols=str(args.symbols or "FETUSDT,OPUSDT"),
        output_md=str(args.output_md or "logs/post_close_orphan_diagnosis.md"),
        base_url=str(args.base_url or ""),
    )
    if bool(args.json):
        print(json.dumps(result, ensure_ascii=False))
        return
    print(f"verdict={result.get('verdict', '')}")
    print(f"verdict_reason={result.get('verdict_reason', '')}")
    print(f"output_md={result.get('output_md', '')}")


if __name__ == "__main__":
    main()
