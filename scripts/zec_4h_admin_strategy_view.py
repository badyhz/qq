#!/usr/bin/env python3
"""Serve the governed ZEC admin with strategy-owned history and explicit clocks.

This is a narrow presentation/data-integrity guard around the existing V2 admin.
It does not add an exchange write path.  Binance account fills are shown only
when a FILLED live-ledger record proves that the order belongs to this strategy.
Signal-bar time, exchange fill time, and local record/replay time remain separate.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Iterable

from core.zec_4h_admin import (
    DEFAULT_LEDGER_PATH,
    collect_admin_snapshot as _collect_admin_snapshot,
)
from core.zec_4h_live import LiveExecutionLedger
import scripts.run_zec_4h_admin as base


BEIJING = timezone(timedelta(hours=8))


def _number(value: Any) -> float:
    try:
        return float(value if value not in (None, "") else 0.0)
    except (TypeError, ValueError):
        return 0.0


def _parse_iso(value: Any) -> datetime | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _beijing_text(value: Any) -> str:
    parsed = _parse_iso(value)
    if parsed is None:
        return "—"
    return parsed.astimezone(BEIJING).strftime("%Y-%m-%d %H:%M:%S")


def _latest_strategy_records(
    records: Iterable[dict[str, Any]],
    *,
    strategy_id: str,
    symbol: str,
) -> list[dict[str, Any]]:
    latest: dict[str, dict[str, Any]] = {}
    unkeyed: list[dict[str, Any]] = []
    wanted_symbol = str(symbol).upper()
    for raw in records:
        row = dict(raw)
        if str(row.get("strategy_id", "")) != strategy_id:
            continue
        # Legacy v1 rows may not have persisted symbol.  They can only inherit
        # the current symbol for the original ZECUSDT strategy.
        row_symbol = str(row.get("symbol") or ("ZECUSDT" if wanted_symbol == "ZECUSDT" else "")).upper()
        if row_symbol != wanted_symbol:
            continue
        key = str(row.get("signal_key", ""))
        if key:
            latest[key] = row
        else:
            unkeyed.append(row)
    rows = [*unkeyed, *latest.values()]
    return sorted(rows, key=lambda row: str(row.get("recorded_at", "")), reverse=True)


def _signal_reason_text(row: dict[str, Any]) -> str:
    reason = str(row.get("reason", "") or "")
    action = str(row.get("action", "") or "")
    if action == "OPEN" and reason == "BUY_FALSE_TO_TRUE":
        return "买入条件 false→true：收盘>SMA27、DIF上升、5根反向过滤通过"
    if reason == "STALE_RISK_INCREASE_BLOCKED":
        return "旧信号回放：禁止补开仓/加仓"
    if reason == "REDUCE_SIGNAL_OBSERVED_FLAT":
        return "减仓源信号出现，但当时为空仓"
    if reason == "REDUCE_SIGNAL_BLOCKED_HALF_TARGET":
        return "减仓源信号出现，但安全规则禁止减到半仓以下"
    return reason or "—"


def repair_admin_snapshot(
    payload: dict[str, Any],
    records: Iterable[dict[str, Any]],
) -> dict[str, Any]:
    """Fail closed: only ledger-proven strategy fills may appear as history."""
    fixed = dict(payload)
    strategy = dict(fixed.get("strategy") or {})
    strategy_id = str(strategy.get("strategy_id") or "zec_4h_live_v1")
    symbol = str(strategy.get("symbol") or "ZECUSDT").upper()
    latest = _latest_strategy_records(records, strategy_id=strategy_id, symbol=symbol)

    ledger_by_order: dict[str, dict[str, Any]] = {}
    for row in latest:
        order_id = str(row.get("exchange_order_id", "") or "")
        if not order_id:
            continue
        if str(row.get("status", "")).upper() != "FILLED":
            continue
        if _number(row.get("filled_qty")) <= 0:
            continue
        ledger_by_order[order_id] = row

    strategy_history: list[dict[str, Any]] = []
    for raw in list(fixed.get("history") or []):
        row = dict(raw)
        order_id = str(row.get("order_id", "") or "")
        evidence = ledger_by_order.get(order_id)
        if evidence is None:
            # This is an account-level Binance fill, not a proven strategy fill.
            continue
        row["strategy_owned"] = True
        row["signal_bar_close_time"] = str(evidence.get("bar_close_time", "") or "")
        row["fill_time"] = str(row.get("time", "") or "")
        row["recorded_at"] = str(evidence.get("recorded_at", "") or "")
        row["signal_time_cn"] = _beijing_text(row["signal_bar_close_time"])
        row["fill_time_cn"] = _beijing_text(row["fill_time"])
        row["record_time_cn"] = _beijing_text(row["recorded_at"])
        row["signal_reason"] = str(evidence.get("reason", "") or "")
        row["signal_reason_cn"] = _signal_reason_text(evidence)
        row["signal_key"] = str(evidence.get("signal_key", "") or "")
        row["config_revision"] = evidence.get("config_revision")
        strategy_history.append(row)
    fixed["history"] = strategy_history

    events: list[dict[str, Any]] = []
    for row in latest[:50]:
        event = {
            "signal_bar_close_time": str(row.get("bar_close_time", "") or ""),
            "recorded_at": str(row.get("recorded_at", "") or ""),
            "signal_time_cn": _beijing_text(row.get("bar_close_time")),
            "record_time_cn": _beijing_text(row.get("recorded_at")),
            "action": str(row.get("action", "") or ""),
            "status": str(row.get("status", "") or ""),
            "reason": str(row.get("reason", "") or ""),
            "reason_cn": _signal_reason_text(row),
            "filled_qty": _number(row.get("filled_qty")),
            "average_fill_price": _number(row.get("average_fill_price")),
            "realized_pnl": _number(row.get("realized_pnl")),
            "fee": _number(row.get("fee")),
            "exchange_order_id": str(row.get("exchange_order_id", "") or ""),
            "signal_key": str(row.get("signal_key", "") or ""),
        }
        events.append(event)
    fixed["recent_events"] = events
    fixed["history_integrity"] = {
        "strategy_only": True,
        "account_level_unmatched_fills_hidden": True,
        "time_semantics": {
            "signal_bar_close_time": "4H closed-bar signal boundary",
            "fill_time": "exchange fill time",
            "recorded_at": "local ledger/replay record time",
        },
    }
    return fixed


def collect_admin_snapshot() -> dict[str, Any]:
    payload = _collect_admin_snapshot()
    try:
        records = LiveExecutionLedger(DEFAULT_LEDGER_PATH).read()
    except Exception:
        # Never fall back to displaying raw account fills as if they were
        # strategy trades.  If ledger ownership cannot be proven, history is
        # deliberately empty and the UI can state why.
        fixed = dict(payload)
        fixed["history"] = []
        fixed["recent_events"] = []
        fixed["history_integrity"] = {
            "strategy_only": True,
            "ok": False,
            "error": "LEDGER_READ_FAILED",
        }
        return fixed
    fixed = repair_admin_snapshot(payload, records)
    fixed["history_integrity"]["ok"] = True
    return fixed


OLD_HISTORY_HEADER = (
    '<div class="section"><h3>最近交易记录</h3><div class="table"><table><thead><tr>'
    '<th>时间</th><th>方向</th><th>动作</th><th>成交价</th><th>数量</th><th>名义价值</th>'
    '<th>手续费</th><th>已实现盈亏</th><th>退出原因</th></tr></thead><tbody id="history"></tbody>'
    '</table></div></div>'
)
NEW_HISTORY_HEADER = (
    '<div class="section"><h3>策略成交记录（仅本策略订单）</h3>'
    '<div class="tiny" style="margin:6px 0 10px">信号时间=4H收盘确认；实际成交时间=交易所 fill。两者不得混用。</div>'
    '<div class="table"><table><thead><tr>'
    '<th>信号K线时间（北京时间）</th><th>实际成交时间（北京时间）</th><th>方向</th><th>动作</th>'
    '<th>成交价</th><th>数量</th><th>名义价值</th><th>手续费</th><th>已实现盈亏</th>'
    '<th>信号原因</th><th>退出原因</th></tr></thead><tbody id="history"></tbody></table></div></div>'
    '<div class="section"><h3>策略信号 / 回放日志</h3>'
    '<div class="tiny" style="margin:6px 0 10px">“记录/回放时间”只是程序处理时间，不代表买卖信号发生时间。</div>'
    '<div class="table"><table><thead><tr><th>信号K线时间（北京时间）</th><th>记录/回放时间（北京时间）</th>'
    '<th>动作</th><th>状态</th><th>原因</th><th>成交数量</th><th>成交价</th><th>订单ID</th></tr></thead>'
    '<tbody id="events"></tbody></table></div></div>'
)

OLD_HISTORY_RENDER = """const rows=(DATA.history||[]).slice(0,50);$('history').innerHTML=rows.length?rows.map(x=>`<tr><td>${esc(x.time)}</td><td>${esc(x.side)}</td><td>${esc(x.action||'—')}</td><td>${n(x.price,4)}</td><td>${n(x.qty,6)}</td><td>${n(x.notional,4)}</td><td>${n(x.fee,6)} ${esc(x.fee_asset||'')}</td><td class=\"${cls(x.realized_pnl)}\">${m(x.realized_pnl)}</td><td>${esc(x.exit_reason||'—')}</td></tr>`).join(''):`<tr><td colspan=\"9\">暂无历史成交</td></tr>`;}"""
NEW_HISTORY_RENDER = """const rows=(DATA.history||[]).slice(0,50);$('history').innerHTML=rows.length?rows.map(x=>`<tr><td>${esc(x.signal_time_cn||'—')}</td><td>${esc(x.fill_time_cn||'—')}</td><td>${esc(x.side)}</td><td>${esc(x.action||'—')}</td><td>${n(x.price,4)}</td><td>${n(x.qty,6)}</td><td>${n(x.notional,4)}</td><td>${n(x.fee,6)} ${esc(x.fee_asset||'')}</td><td class=\"${cls(x.realized_pnl)}\">${m(x.realized_pnl)}</td><td>${esc(x.signal_reason_cn||x.signal_reason||'—')}</td><td>${esc(x.exit_reason||'—')}</td></tr>`).join(''):`<tr><td colspan=\"11\">暂无已确认的本策略成交</td></tr>`;const events=(DATA.recent_events||[]).slice(0,50);$('events').innerHTML=events.length?events.map(e=>`<tr><td>${esc(e.signal_time_cn||'—')}</td><td>${esc(e.record_time_cn||'—')}</td><td>${esc(e.action||'—')}</td><td>${esc(e.status||'—')}</td><td>${esc(e.reason_cn||e.reason||'—')}</td><td>${n(e.filled_qty,6)}</td><td>${n(e.average_fill_price,4)}</td><td>${esc(e.exchange_order_id||'—')}</td></tr>`).join(''):`<tr><td colspan=\"8\">暂无策略事件</td></tr>`;}"""


HTML = base.HTML.replace(OLD_HISTORY_HEADER, NEW_HISTORY_HEADER).replace(
    OLD_HISTORY_RENDER, NEW_HISTORY_RENDER
)
if OLD_HISTORY_HEADER not in base.HTML or OLD_HISTORY_RENDER not in base.HTML:
    raise RuntimeError("ZEC_ADMIN_V2_HTML_CONTRACT_CHANGED")

# AdminHandler resolves these module globals from scripts.run_zec_4h_admin at
# request time.  Replace only the snapshot producer and HTML; all authenticated
# control POST semantics remain exactly those of V2.
base.HTML = HTML
base.collect_admin_snapshot = collect_admin_snapshot


def main() -> int:
    return base.main()


if __name__ == "__main__":
    raise SystemExit(main())
