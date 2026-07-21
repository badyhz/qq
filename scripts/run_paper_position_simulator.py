"""Phase 10G Paper Position Simulator runner.

Reads trade_intents.json, creates paper positions, optionally updates with klines.
Future-only lifecycle: only bars after opened_bar_time can trigger TP/SL.
No orders, no accounts, no secrets, no testnet, no live.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core.paper_trading.paper_position import (
    CLOSED_STATUSES,
    OVERLAP_MANIFEST_FILENAME,
    activate_closed_bar_trusted_cohort,
    build_overlap_exclusion_manifest,
    exposure_identity,
    load_canonical_positions,
    position_state_fingerprint,
    select_canonical_position_state,
)
from core.paper_trading.net_friction import activate_net_friction_trusted_cohort
from core.paper_trading.paper_position_simulator import (
    simulate_intent_only, simulate_with_klines,
    simulate_existing_positions_update_only,
)
from core.paper_trading.data_source import DataSourceConfig
from core.paper_trading.public_market_adapter import BinancePublicKlineAdapter

REPO_ROOT = os.path.join(os.path.dirname(__file__), "..")
REPORT_DIR = os.path.join(REPO_ROOT, "reports", "strategies")

SAFETY_FLAGS = [
    "PAPER_ONLY", "SHADOW_ONLY", "NO_SECRET", "NO_ENV_READ",
    "NO_ACCOUNT", "NO_ORDER", "NO_REAL_ORDER", "NO_TESTNET", "NO_LIVE",
    "NO_WEBSOCKET", "NO_PRIVATE_ENDPOINT", "NO_WEBHOOK_SEND",
    "POSITION_SIMULATOR_DRY_RUN_ONLY",
]


def _today_str() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def _default_input_path(date_str: str) -> str:
    return os.path.join(REPORT_DIR, f"{date_str}_trade_intents.json")


def _default_positions_path(date_str: str) -> str:
    return os.path.join(REPORT_DIR, f"{date_str}_paper_positions.json")


def _positions_path(output_dir: str, date_str: str) -> str:
    return os.path.join(output_dir, f"{date_str}_paper_positions.json")


def _position_dedupe_key(position: dict) -> str:
    pid = str(position.get("position_id") or "").strip()
    if pid:
        return f"position_id:{pid}"
    return "|".join([
        str(position.get("strategy_id") or ""),
        str(position.get("symbol") or ""),
        str(position.get("timeframe") or ""),
        str(position.get("side") or ""),
        str(position.get("opened_bar_time") or ""),
    ])


def _load_update_existing_positions(output_dir: str, date_str: str) -> list[dict]:
    """Load OPEN positions for update-only from cross-day ledgers.

    Uses select_canonical_position_state() to ensure:
    - CLOSED positions from ledger are never reopened by positions.json
    - Terminal state conflicts are detected and reported
    - Same shared rules as canonical load

    Raises RuntimeError on terminal state conflicts (caller must abort).
    """
    open_positions, _all_positions, _signal_keys, _diag = _load_entry_guard_state(
        output_dir, date_str,
    )
    return open_positions


def _load_entry_guard_state(
    output_dir: str,
    date_str: str,
) -> tuple[list[dict], list[dict], set[str], dict]:
    """Load all historical canonical state before any new entry is evaluated."""
    canonical, diagnostics = load_canonical_positions(output_dir)
    fatal = []
    if diagnostics.get("load_error"):
        fatal.append(f"load_error={diagnostics['load_error']}")
    if diagnostics.get("files_error"):
        fatal.append(f"files_error={diagnostics['files_error']}")
    if diagnostics.get("corrupted_lines"):
        fatal.append(f"corrupted_lines={diagnostics['corrupted_lines']}")
    if diagnostics.get("excluded_no_position_id"):
        fatal.append(f"missing_position_id={diagnostics['excluded_no_position_id']}")
    for conflict in diagnostics.get("terminal_conflicts", []):
        if conflict.get("fatal", True):
            fatal.append(
                f"terminal_conflict={conflict.get('position_id')}:"
                f"{conflict.get('old_status')}->{conflict.get('new_status')}"
            )

    latest_by_key = {
        _position_dedupe_key(position): position
        for position in canonical
        if _position_dedupe_key(position)
    }
    current_path = _positions_path(output_dir, date_str)
    if os.path.isfile(current_path):
        try:
            with open(current_path) as f:
                current_data = json.load(f)
            current_positions = current_data.get("positions", [])
            if not isinstance(current_positions, list):
                raise ValueError("positions is not a list")
        except (OSError, json.JSONDecodeError, ValueError) as exc:
            fatal.append(f"current_snapshot_error={exc}")
            current_positions = []
        for position in current_positions:
            if not isinstance(position, dict):
                fatal.append("current_snapshot_non_object_position")
                continue
            key = _position_dedupe_key(position)
            if not key:
                fatal.append("current_snapshot_missing_position_id")
                continue
            old = latest_by_key.get(key)
            if old is None:
                latest_by_key[key] = position
                continue
            selected = select_canonical_position_state(old, position)
            latest_by_key[key] = selected.selected
            if selected.conflict and selected.conflict_reason != "terminal_irreversible":
                fatal.append(
                    f"Terminal state conflicts: current_snapshot={position.get('position_id')}:"
                    f"{old.get('status')}->{position.get('status')}"
                )

    if fatal:
        raise RuntimeError("Canonical entry guard failed closed: " + "; ".join(fatal))

    all_positions = sorted(
        latest_by_key.values(), key=lambda item: str(item.get("position_id") or ""),
    )
    open_positions = [p for p in all_positions if p.get("status") == "OPEN"]
    exposure_owners: dict[str, str] = {}
    duplicate_open_exposures = 0
    for position in open_positions:
        try:
            key = exposure_identity(position)
        except ValueError as exc:
            raise RuntimeError(
                f"Canonical OPEN has invalid exposure identity: {position.get('position_id')}: {exc}"
            ) from exc
        if key in exposure_owners:
            duplicate_open_exposures += 1
        else:
            exposure_owners[key] = str(position.get("position_id") or "")

    signal_keys = {
        str(position.get("signal_key"))
        for position in all_positions if position.get("signal_key")
    }
    diagnostics["canonical_open_count_before_new_entries"] = len(open_positions)
    diagnostics["duplicate_canonical_open_exposures"] = duplicate_open_exposures
    return open_positions, all_positions, signal_keys, diagnostics


def _ensure_overlap_manifest(output_dir: str, canonical_positions: list[dict]) -> str:
    """Create the fixed legacy exclusion manifest once; never rewrite ledgers."""
    path = os.path.join(output_dir, OVERLAP_MANIFEST_FILENAME)
    if os.path.isfile(path):
        return path
    cohort_start = datetime.now(timezone.utc).isoformat(timespec="seconds")
    manifest = build_overlap_exclusion_manifest(canonical_positions, cohort_start)
    os.makedirs(output_dir, exist_ok=True)
    temp_path = f"{path}.tmp"
    with open(temp_path, "w") as f:
        json.dump(manifest, f, indent=2)
        f.write("\n")
    os.replace(temp_path, path)
    return path


def render_markdown(result: dict) -> str:
    """Render human-readable markdown from simulation result."""
    counts = result.get("status_counts", {})
    lc = result.get("lifecycle_stats", {})
    lines = [
        "# Paper Position Simulator",
        "",
        f"**Date:** {result.get('date', '')}",
        f"**Mode:** {result.get('mode', '')}",
        f"**Positions:** {result.get('position_count', 0)}",
        "",
        "## Summary",
        "",
        f"- OPEN: {counts.get('OPEN', 0)}",
        f"- TAKE_PROFIT_HIT: {counts.get('TAKE_PROFIT_HIT', 0)}",
        f"- STOP_LOSS_HIT: {counts.get('STOP_LOSS_HIT', 0)}",
        f"- TIMEOUT_EXIT: {counts.get('TIMEOUT_EXIT', 0)}",
        f"- INVALID: {counts.get('INVALID', 0)}",
        "",
        "纸面持仓模拟",
        "",
        "状态：shadow-only",
        "不会下单",
        "不会连接账户",
        "不会 testnet/live",
        "",
        "本次生成：",
        f"- OPEN: {counts.get('OPEN', 0)}",
        f"- TAKE_PROFIT_HIT: {counts.get('TAKE_PROFIT_HIT', 0)}",
        f"- STOP_LOSS_HIT: {counts.get('STOP_LOSS_HIT', 0)}",
        f"- TIMEOUT_EXIT: {counts.get('TIMEOUT_EXIT', 0)}",
        "",
        "## Lifecycle",
        "",
        f"- future_only: {lc.get('future_only', True)}",
        f"- new positions: {lc.get('new_positions_count', 0)}",
        f"- existing positions: {lc.get('existing_positions_count', 0)}",
        f"- deduped intents: {lc.get('deduped_intents_count', 0)}",
        f"- positions updated: {lc.get('positions_updated_count', 0)}",
        f"- skipped (no future bars): {lc.get('positions_skipped_no_future_bars', 0)}",
        f"- skipped (newly opened): {lc.get('positions_skipped_newly_opened', 0)}",
        f"- skipped (overlap open): {lc.get('positions_skipped_overlap_open', 0)}",
        f"- overlap guard: {lc.get('overlap_guard_enabled', False)}",
        "",
        "newly opened positions are not updated until next run",
        "duplicate intents are ignored",
        "closed positions are not reopened",
        "existing OPEN position blocks same strategy/symbol/timeframe/side",
        "",
    ]

    positions = result.get("positions", [])

    for label, status in [
        ("OPEN", "OPEN"), ("TAKE_PROFIT_HIT", "TAKE_PROFIT_HIT"),
        ("STOP_LOSS_HIT", "STOP_LOSS_HIT"), ("TIMEOUT_EXIT", "TIMEOUT_EXIT"),
    ]:
        group = [p for p in positions if p.get("status") == status]
        if group:
            lines.append(f"## {label}")
            lines.append("")
            for p in group:
                lines.extend(_position_lines(p))
                lines.append("")

    summary = result.get("summary", {})
    by_strat = summary.get("by_strategy", {})
    if by_strat:
        lines.extend(["## Strategy Summary", ""])
        for sid, stats in by_strat.items():
            lines.append(f"### {sid}")
            lines.append("")
            lines.append(f"- Total: {stats.get('total', 0)}")
            lines.append(f"- OPEN: {stats.get('OPEN', 0)}")
            lines.append(f"- TP: {stats.get('TAKE_PROFIT_HIT', 0)}")
            lines.append(f"- SL: {stats.get('STOP_LOSS_HIT', 0)}")
            lines.append(f"- Timeout: {stats.get('TIMEOUT_EXIT', 0)}")
            lines.append(f"- Realized PnL: {stats.get('total_realized_pnl', 0)}")
            lines.append(f"- Avg R: {stats.get('avg_r_multiple', 0)}")
            lines.append("")

    lines.extend([
        "## Safety",
        "",
        "- Paper-only: YES",
        "- Shadow-only: YES",
        "- No order: YES",
        "- No account: YES",
        "- No testnet/live: YES",
        "- No secret: YES",
        "- No real execution: YES",
        "",
    ])
    return "\n".join(lines)


def _position_lines(p: dict) -> list[str]:
    return [
        f"### {p.get('strategy_id', '')}｜{p.get('symbol', '')}｜{p.get('timeframe', '')}｜{p.get('side', '')}",
        "",
        f"- 策略：{p.get('strategy_id', '')}",
        f"- 标的：{p.get('symbol', '')}",
        f"- 周期：{p.get('timeframe', '')}",
        f"- 方向：{p.get('side', '')}",
        f"- 入场价：{p.get('entry_price', 0)}",
        f"- 止损：{p.get('stop_loss', 0)}",
        f"- 止盈：{p.get('take_profit', 0)}",
        f"- 状态：{p.get('status', '')}",
        f"- 纸面仓位：{round(p.get('position_size_preview', 0), 6)}",
        f"- 纸面盈亏：{round(p.get('realized_pnl', 0), 6)}",
        f"- R 倍数：{p.get('r_multiple', 0)}",
        f"- 处理：paper/shadow 记录，不下单",
    ]


def main():
    parser = argparse.ArgumentParser(description="Phase 10G paper position simulator")
    parser.add_argument("--input-file", type=str, default=None)
    parser.add_argument("--date", type=str, default=None)
    parser.add_argument("--output-dir", type=str, default=REPORT_DIR)
    parser.add_argument("--allow-public-http", action="store_true")
    parser.add_argument("--update-with-klines", action="store_true")
    parser.add_argument("--limit", type=int, default=60)
    parser.add_argument("--timeout-bars", type=int, default=24)
    parser.add_argument("--paper-equity-preview", type=float, default=10000.0)
    parser.add_argument("--future-only", action="store_true", default=True)
    parser.add_argument("--allow-update-newly-opened", action="store_true", default=False)
    parser.add_argument("--update-existing-only", action="store_true", default=False)
    parser.add_argument("--entry-only", action="store_true", default=False)
    parser.add_argument("--activate-closed-bar-cohort", action="store_true")
    parser.add_argument("--cohort-start-at", type=str)
    parser.add_argument("--cohort-start-run-id", type=str)
    parser.add_argument("--cohort-start-commit", type=str)
    parser.add_argument("--activate-net-friction-cohort", action="store_true")
    parser.add_argument("--net-friction-start-at", type=str)
    parser.add_argument("--net-friction-start-run-id", type=str)
    parser.add_argument("--net-friction-start-commit", type=str)
    parser.add_argument("--net-friction-assumptions-hash", type=str)
    args = parser.parse_args()

    if args.activate_closed_bar_cohort:
        manifest_path = os.path.join(args.output_dir, OVERLAP_MANIFEST_FILENAME)
        result = activate_closed_bar_trusted_cohort(
            manifest_path,
            start_at=args.cohort_start_at or "",
            start_run_id=args.cohort_start_run_id or "",
            start_commit=args.cohort_start_commit or "",
        )
        print(
            "CLOSED_BAR_COHORT_ACTIVATION_RESULT="
            + json.dumps(result.to_dict(), sort_keys=True)
        )
        return 0 if result.status in {
            "ACTIVATED", "ALREADY_ACTIVE_SAME_METADATA",
        } else 1

    if args.activate_net_friction_cohort:
        manifest_path = os.path.join(args.output_dir, OVERLAP_MANIFEST_FILENAME)
        result = activate_net_friction_trusted_cohort(
            manifest_path,
            start_at=args.net_friction_start_at or "",
            run_id=args.net_friction_start_run_id or "",
            commit=args.net_friction_start_commit or "",
            assumptions_hash_value=args.net_friction_assumptions_hash or "",
        )
        print(
            "NET_FRICTION_COHORT_ACTIVATION_RESULT="
            + json.dumps(result.to_dict(), sort_keys=True)
        )
        return 0 if result.status in {
            "ACTIVATED", "ALREADY_ACTIVE_SAME_METADATA",
        } else 1

    activation_metadata_args = (
        args.cohort_start_at,
        args.cohort_start_run_id,
        args.cohort_start_commit,
    )
    if any(value is not None for value in activation_metadata_args):
        print("ERROR: cohort metadata requires --activate-closed-bar-cohort")
        return 1
    net_activation_metadata_args = (
        args.net_friction_start_at,
        args.net_friction_start_run_id,
        args.net_friction_start_commit,
        args.net_friction_assumptions_hash,
    )
    if any(value is not None for value in net_activation_metadata_args):
        print("ERROR: net friction metadata requires --activate-net-friction-cohort")
        return 1

    date_str = args.date or _today_str()
    input_path = args.input_file or _default_input_path(date_str)
    if not os.path.isfile(input_path):
        print(f"ERROR: input file not found: {input_path}")
        return 1

    with open(input_path) as f:
        intents_data = json.load(f)

    intents = intents_data.get("intents", [])
    shadow_intents = [i for i in intents if i.get("intent_status") == "SHADOW_READY"]
    print(f"Total intents: {len(intents)}")
    print(f"SHADOW_READY: {len(shadow_intents)}")

    # Restore all historical canonical OPEN before evaluating any new intent.
    try:
        existing, canonical_positions, existing_signal_keys, guard_diag = (
            _load_entry_guard_state(args.output_dir, date_str)
        )
        if not args.update_existing_only:
            manifest_path = _ensure_overlap_manifest(args.output_dir, canonical_positions)
            print(f"Overlap exclusion manifest: {manifest_path}")
    except (RuntimeError, ValueError, OSError) as e:
        print(f"ERROR: {e}")
        return 1
    print(f"Existing positions: {len(existing)}")
    print(
        "CANONICAL_OPEN_COUNT_BEFORE_NEW_ENTRIES="
        f"{guard_diag['canonical_open_count_before_new_entries']}"
    )

    if args.allow_public_http and args.update_with_klines and not args.entry_only:
        if args.update_existing_only:
            print("Mode: update_existing_only (future_only)")
        else:
            print("Mode: public_readonly_update (future_only)")
        config = DataSourceConfig(mode="snapshot", network_enabled=True)
        adapter = BinancePublicKlineAdapter(config)

        # Collect unique symbol/timeframe from intents + existing positions
        unique_keys: set = set()
        if not args.update_existing_only:
            for intent in shadow_intents:
                sym = intent.get("symbol", "")
                tf = intent.get("timeframe", "")
                unique_keys.add(f"{sym}_{tf}")
        for pos in existing:
            if pos.get("status") not in CLOSED_STATUSES:
                sym = pos.get("symbol", "")
                tf = pos.get("timeframe", "")
                unique_keys.add(f"{sym}_{tf}")

        bars_by_key: dict = {}
        for key in unique_keys:
            sym, tf = key.rsplit("_", 1)
            print(f"  Fetching {sym} {tf}...", end=" ")
            try:
                bars = adapter.get_bars(sym, timeframe=tf, limit=args.limit)
                bars_by_key[key] = bars
                print(f"OK ({len(bars)} bars)")
            except Exception as e:
                print(f"ERROR: {e}")
            time.sleep(0.3)

        if args.update_existing_only:
            result = simulate_existing_positions_update_only(
                existing, bars_by_key, date_str,
                timeout_bars=args.timeout_bars,
                future_only=args.future_only,
            )
        else:
            result = simulate_with_klines(
                shadow_intents, bars_by_key, date_str,
                existing_positions=existing,
                existing_signal_keys=existing_signal_keys,
                paper_equity=args.paper_equity_preview,
                timeout_bars=args.timeout_bars,
                future_only=args.future_only,
                allow_update_newly_opened=args.allow_update_newly_opened,
            )
    elif args.update_existing_only:
        print("Mode: update_existing_only (offline, no klines)")
        result = simulate_existing_positions_update_only(
            existing, {}, date_str,
            timeout_bars=args.timeout_bars,
            future_only=args.future_only,
        )
    else:
        print("Mode: intent_only")
        result = simulate_intent_only(
            shadow_intents, date_str,
            existing_positions=existing,
            existing_signal_keys=existing_signal_keys,
            paper_equity=args.paper_equity_preview,
        )

    result_dict = result.to_dict()
    os.makedirs(args.output_dir, exist_ok=True)

    # JSON
    json_path = os.path.join(args.output_dir, f"{date_str}_paper_positions.json")
    with open(json_path, "w") as f:
        json.dump(result_dict, f, indent=2)
    print(f"JSON: {json_path}")

    # Markdown
    md_path = os.path.join(args.output_dir, f"{date_str}_paper_positions.md")
    with open(md_path, "w") as f:
        f.write(render_markdown(result_dict))
    print(f"Markdown: {md_path}")

    # Ledger JSONL (fingerprint-idempotent append)
    ledger_path = os.path.join(args.output_dir, f"{date_str}_paper_position_ledger.jsonl")
    now_iso = datetime.now(timezone.utc).isoformat(timespec="seconds")

    # Load existing fingerprints from this ledger file
    existing_fingerprints: set[str] = set()
    if os.path.isfile(ledger_path):
        try:
            with open(ledger_path) as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    rec = json.loads(line)
                    fp = rec.get("_fp")
                    if fp:
                        existing_fingerprints.add(fp)
        except (OSError, json.JSONDecodeError):
            pass

    appended = 0
    skipped = 0
    with open(ledger_path, "a") as f:
        for pos in result_dict.get("positions", []):
            record = dict(pos)
            record["recorded_at"] = now_iso
            fp = position_state_fingerprint(record)
            if fp in existing_fingerprints:
                skipped += 1
                continue
            record["_fp"] = fp
            f.write(json.dumps(record) + "\n")
            existing_fingerprints.add(fp)
            appended += 1
    print(f"Ledger: {ledger_path} (appended={appended}, skipped={skipped})")

    # Summary
    lc = result_dict.get("lifecycle_stats", {})
    summary_path = os.path.join(args.output_dir, f"{date_str}_paper_position_summary.json")
    with open(summary_path, "w") as f:
        json.dump({
            "date": date_str,
            "mode": result_dict["mode"],
            "status_counts": result_dict["status_counts"],
            "summary": result_dict["summary"],
            "lifecycle_stats": lc,
            "safety_flags": SAFETY_FLAGS,
            "dry_run_only": True,
            "actually_executed": False,
        }, f, indent=2)
    print(f"Summary: {summary_path}")

    counts = result_dict["status_counts"]
    print(f"\n=== Paper Position Simulator Complete ===")
    print(f"Total: {result_dict['position_count']}")
    print(f"OPEN: {counts['OPEN']}")
    print(f"TP: {counts['TAKE_PROFIT_HIT']}")
    print(f"SL: {counts['STOP_LOSS_HIT']}")
    print(f"Timeout: {counts['TIMEOUT_EXIT']}")
    print(f"Invalid: {counts['INVALID']}")
    print(f"New positions: {lc.get('new_positions_count', 0)}")
    print(f"Existing positions: {lc.get('existing_positions_count', 0)}")
    print(f"Deduped intents: {lc.get('deduped_intents_count', 0)}")
    print(f"Updated: {lc.get('positions_updated_count', 0)}")
    print(f"Skipped (no future bars): {lc.get('positions_skipped_no_future_bars', 0)}")
    print(f"Skipped (newly opened): {lc.get('positions_skipped_newly_opened', 0)}")
    print(f"Skipped (overlap open): {lc.get('positions_skipped_overlap_open', 0)}")
    print(f"Overlap guard: {lc.get('overlap_guard_enabled', False)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
