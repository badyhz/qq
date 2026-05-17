from __future__ import annotations

from typing import Any


def classify_post_close_orphan_state(state: dict[str, Any]) -> dict[str, Any]:
    symbol = str(state.get("symbol", "")).strip().upper()
    position_amt = float(state.get("positionAmt", 0.0) or 0.0)
    open_count = int(state.get("openAlgoOrdersCount", 0) or 0)
    protection_status = str(state.get("protection_status", "UNKNOWN")).strip().upper()

    diagnosis = protection_status
    action_required = str(state.get("action_required", "")).strip()
    if abs(position_amt) <= 0 and open_count <= 0:
        diagnosis = "FLAT_CLEAN"
        action_required = "none"
    elif abs(position_amt) <= 0 and open_count > 0:
        diagnosis = "ORPHAN_PROTECTION"
        action_required = "review_orphan_and_clean_if_confirmed"
    elif abs(position_amt) > 0 and protection_status == "FULLY_PROTECTED":
        diagnosis = "FULLY_PROTECTED"
        action_required = "none"
    elif abs(position_amt) > 0 and protection_status == "PARTIAL_PROTECTED":
        diagnosis = "PARTIAL_PROTECTED"
        action_required = "repair_missing_protection_immediately"
    elif abs(position_amt) > 0 and protection_status == "NAKED_POSITION":
        diagnosis = "NAKED_POSITION"
        action_required = "stop_new_orders_and_protect_or_flatten"

    return {
        "symbol": symbol,
        "positionAmt": position_amt,
        "openAlgoOrdersCount": open_count,
        "protection_status": protection_status,
        "diagnosis": diagnosis,
        "action_required": action_required,
    }


def build_orphan_cleanup_recommendation(classification: dict[str, Any]) -> list[str]:
    if str(classification.get("diagnosis", "")).strip().upper() != "ORPHAN_PROTECTION":
        return []
    symbol = str(classification.get("symbol", "")).strip().upper()
    if not symbol:
        return []
    return [
        "PYTHONPATH=. ./.venv/bin/python scripts/safe_flatten_testnet_symbol.py "
        f"--env testnet --symbol {symbol} --cancel-protective-orders --dry-run --json",
        "PYTHONPATH=. ./.venv/bin/python scripts/safe_flatten_testnet_symbol.py "
        f"--env testnet --symbol {symbol} --cancel-protective-orders --confirm --json",
    ]


def render_post_close_orphan_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Post-Close Orphan Diagnosis",
        "",
        f"- ts_utc: {payload.get('ts_utc', '')}",
        f"- env: {payload.get('env', '')}",
        f"- symbols: {','.join(list(payload.get('symbols', [])))}",
        f"- verdict: {payload.get('verdict', '')}",
        f"- verdict_reason: {payload.get('verdict_reason', '')}",
        "",
        "| symbol | positionAmt | openAlgoOrdersCount | protection_status | diagnosis | action_required |",
        "|---|---:|---:|---|---|---|",
    ]
    for row in list(payload.get("per_symbol_diagnosis", [])):
        lines.append(
            f"| {row.get('symbol', '')} | {row.get('positionAmt', 0)} | {row.get('openAlgoOrdersCount', 0)} | {row.get('protection_status', '')} | "
            f"{row.get('diagnosis', '')} | {row.get('action_required', '')} |"
        )
    lines.extend(["", "## Recommended Commands"])
    for cmd in list(payload.get("recommended_commands", [])):
        lines.append(f"- `{cmd}`")
    return "\n".join(lines) + "\n"
