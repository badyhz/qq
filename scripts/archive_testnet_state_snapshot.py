from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from scripts.check_testnet_state import check_testnet_state
from scripts.testnet_state_snapshot_report_common import (
    build_snapshot_archive_payload,
    render_snapshot_markdown,
)


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _default_snapshot_id() -> str:
    return _now_utc().strftime("snapshot_%Y%m%d_%H%M%S")


def _parse_symbols(value: str) -> list[str]:
    return [item.strip().upper() for item in str(value or "").split(",") if item.strip()]


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _write_md(path: Path, summary: dict[str, Any]) -> None:
    content = render_snapshot_markdown(summary)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def archive_testnet_state_snapshot(
    *,
    env: str = "testnet",
    symbols: str = "FETUSDT,OPUSDT",
    output_dir: str = "logs/testnet_state_snapshots",
    snapshot_id: str = "",
    base_url: str = "",
) -> dict[str, Any]:
    resolved_env = str(env or "").strip().lower()
    symbol_list = _parse_symbols(symbols)
    resolved_snapshot_id = str(snapshot_id or "").strip() or _default_snapshot_id()
    run_dir = Path(output_dir) / resolved_snapshot_id
    run_dir.mkdir(parents=True, exist_ok=True)

    per_symbol_state: list[dict[str, Any]] = []
    for symbol in symbol_list:
        result = check_testnet_state(env=resolved_env, symbol=symbol, base_url=base_url)
        if bool(result.get("ok", False)):
            per_symbol_state.append(
                {
                    "ok": True,
                    "symbol": symbol,
                    "positionAmt": result.get("positionAmt", 0.0),
                    "entryPrice": result.get("entryPrice", 0.0),
                    "markPrice": result.get("markPrice", 0.0),
                    "openAlgoOrdersCount": result.get("openAlgoOrdersCount", 0),
                    "open_stop_market_count": result.get("open_stop_market_count", 0),
                    "open_take_profit_market_count": result.get("open_take_profit_market_count", 0),
                    "protection_status": str(result.get("protection_status", "")),
                    "action_required": str(result.get("action_required", "")),
                }
            )
        else:
            per_symbol_state.append(
                {
                    "ok": False,
                    "symbol": symbol,
                    "positionAmt": 0.0,
                    "entryPrice": 0.0,
                    "markPrice": 0.0,
                    "openAlgoOrdersCount": 0,
                    "open_stop_market_count": 0,
                    "open_take_profit_market_count": 0,
                    "protection_status": "UNKNOWN",
                    "action_required": str(result.get("error_message", "state_query_failed")),
                    "error_code": str(result.get("error_code", "")),
                }
            )

    summary = build_snapshot_archive_payload(
        per_symbol_state,
        {
            "snapshot_id": resolved_snapshot_id,
            "env": resolved_env,
            "ts_utc": _now_utc().isoformat(),
            "symbols": symbol_list,
        },
    )
    state_json = run_dir / "state.json"
    state_md = run_dir / "state.md"
    _write_json(state_json, summary)
    _write_md(state_md, summary)
    summary["state_json"] = str(state_json)
    summary["state_md"] = str(state_md)
    return summary


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Archive a read-only testnet state snapshot for symbols")
    parser.add_argument("--env", default="testnet")
    parser.add_argument("--symbols", default="FETUSDT,OPUSDT")
    parser.add_argument("--output-dir", default="logs/testnet_state_snapshots")
    parser.add_argument("--snapshot-id", default="")
    parser.add_argument("--base-url", default="")
    parser.add_argument("--json", action="store_true")
    return parser


def main() -> None:
    args = build_arg_parser().parse_args()
    summary = archive_testnet_state_snapshot(
        env=str(args.env or "testnet"),
        symbols=str(args.symbols or "FETUSDT,OPUSDT"),
        output_dir=str(args.output_dir or "logs/testnet_state_snapshots"),
        snapshot_id=str(args.snapshot_id or ""),
        base_url=str(args.base_url or ""),
    )
    if bool(args.json):
        print(json.dumps(summary, ensure_ascii=False))
        return
    print(f"snapshot_id={summary.get('snapshot_id', '')}")
    print(f"aggregate_status={summary.get('aggregate_status', '')}")
    print(f"state_json={summary.get('state_json', '')}")
    print(f"state_md={summary.get('state_md', '')}")


if __name__ == "__main__":
    main()
