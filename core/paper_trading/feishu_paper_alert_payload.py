"""Feishu-ready paper alert payloads for focused plan previews.

Pure renderer. No network, no secrets, no webhook send, no orders.
"""
from __future__ import annotations

import hashlib
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any


FINAL_VERDICT = (
    "PHASE10C3J_FEISHU_READY_PAPER_ALERT_PAYLOAD_READY|"
    "DRY_RUN_ONLY=TRUE|WEBHOOK_SEND_ATTEMPTED=FALSE|"
    "REAL_ORDER_SUBMIT_NOT_ALLOWED"
)

PAYLOAD_SAFETY_FLAGS = [
    "PAPER_ONLY",
    "FEISHU_READY_ONLY",
    "NO_WEBHOOK_SEND",
    "NO_SECRET",
    "NO_ACCOUNT",
    "NO_ORDER",
    "NO_REAL_ORDER",
    "NO_TESTNET",
    "NO_LIVE",
    "NOT_TRADING_RECOMMENDATION",
]

# Chinese direction labels
DIRECTION_CN = {
    "LONG_OBSERVE": "多头观察",
    "SHORT_OBSERVE": "空头观察",
    "NO_TRADE": "不交易",
}

# Chinese status labels
STATUS_CN = {
    "TRIGGERED": "已触发",
    "WAITING": "等待确认",
    "INVALIDATED": "已失效",
    "SHORT_TRIGGERED": "空头已触发",
    "SHORT_WAITING": "空头等待",
    "SHORT_INVALIDATED": "空头失效",
    "DATA_ERROR": "数据异常",
}

# Chinese decision labels
DECISION_CN = {
    "WATCH": "可观察",
    "WAIT": "继续等待",
    "AVOID": "不参与",
}

# Chinese timeframe labels
TIMEFRAME_CN = {
    "5m": "5分钟",
    "15m": "15分钟",
    "1h": "1小时",
    "4h": "4小时",
    "1d": "日线",
}


@dataclass(frozen=True)
class FeishuPaperAlertPayload:
    payload_id: str
    created_at: str
    symbol: str
    timeframe: str
    direction: str
    priority: str
    title: str
    message_text: str
    dedup_key: str
    feishu_payload: dict[str, Any]
    source_plan: dict[str, Any]
    dry_run_only: bool
    actually_sent: bool
    webhook_send_attempted: bool
    not_order_payload: bool
    safety_flags: list[str]
    final_verdict: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "payload_id": self.payload_id,
            "created_at": self.created_at,
            "symbol": self.symbol,
            "timeframe": self.timeframe,
            "direction": self.direction,
            "priority": self.priority,
            "title": self.title,
            "message_text": self.message_text,
            "dedup_key": self.dedup_key,
            "feishu_payload": self.feishu_payload,
            "source_plan": dict(self.source_plan),
            "dry_run_only": self.dry_run_only,
            "actually_sent": self.actually_sent,
            "webhook_send_attempted": self.webhook_send_attempted,
            "not_order_payload": self.not_order_payload,
            "safety_flags": list(self.safety_flags),
            "final_verdict": self.final_verdict,
        }


def build_payloads_from_preview(preview: dict[str, Any]) -> dict[str, Any]:
    """Build Feishu-ready payload file data from a focused plan preview report."""
    plans = [p for p in preview.get("plans", []) if isinstance(p, dict)]
    watch_plans = [p for p in plans if p.get("plan_decision") == "WATCH"]
    wait_plans = [p for p in plans if p.get("plan_decision") == "WAIT"]
    avoid_plans = [p for p in plans if p.get("plan_decision") == "AVOID"]

    payloads = [build_plan_payload(plan).to_dict() for plan in watch_plans]
    date = str(preview.get("date") or _today_utc())

    return {
        "date": date,
        "source_mode": str(preview.get("mode") or "unknown"),
        "source_total_plans": len(plans),
        "decision_counts": {
            "WATCH": len(watch_plans),
            "WAIT": len(wait_plans),
            "AVOID": len(avoid_plans),
        },
        "payload_count": len(payloads),
        "payload_scope": "WATCH_ONLY",
        "payloads": payloads,
        "skipped": {
            "WAIT": [_plan_ref(p) for p in wait_plans],
            "AVOID": [_plan_ref(p) for p in avoid_plans],
        },
        "dry_run_only": True,
        "actually_sent": False,
        "webhook_send_attempted": False,
        "not_order_payload": True,
        "safety_flags": list(PAYLOAD_SAFETY_FLAGS),
        "final_verdict": FINAL_VERDICT,
    }


def build_plan_payload(plan: dict[str, Any]) -> FeishuPaperAlertPayload:
    """Build one Feishu interactive-card payload for one WATCH plan."""
    symbol = str(plan.get("symbol") or "")
    timeframe = str(plan.get("timeframe") or "")
    direction = str(plan.get("direction") or "NO_TRADE")
    direction_cn = DIRECTION_CN.get(direction, direction)
    title = f"[PAPER WATCH] {symbol} {timeframe} {direction_cn}"
    created_at = _utc_now_iso()
    message = _message_text(plan)
    dedup_key = _dedup_key(symbol, timeframe, direction, plan)

    return FeishuPaperAlertPayload(
        payload_id=f"FPA_{uuid.uuid4().hex[:12]}",
        created_at=created_at,
        symbol=symbol,
        timeframe=timeframe,
        direction=direction,
        priority="WATCH",
        title=title,
        message_text=message,
        dedup_key=dedup_key,
        feishu_payload=_feishu_card(title, message, plan, created_at),
        source_plan=dict(plan),
        dry_run_only=True,
        actually_sent=False,
        webhook_send_attempted=False,
        not_order_payload=True,
        safety_flags=list(PAYLOAD_SAFETY_FLAGS),
        final_verdict=FINAL_VERDICT,
    )


def render_markdown(payload_file: dict[str, Any]) -> str:
    """Render a human-readable preview of generated paper alert payloads."""
    lines = [
        f"# 纸面观察提醒 - {payload_file.get('date', '')}",
        "",
        f"**数据来源:** {payload_file.get('source_mode', '')}",
        f"**提醒范围:** {payload_file.get('payload_scope', '')}",
        f"**提醒数量:** {payload_file.get('payload_count', 0)}",
        "",
        "## 决策摘要",
        "",
        "| 决策 | 数量 |",
        "|---|---:|",
    ]
    counts = payload_file.get("decision_counts", {})
    for decision in ["WATCH", "WAIT", "AVOID"]:
        cn = DECISION_CN.get(decision, decision)
        lines.append(f"| {cn} | {int(counts.get(decision, 0) or 0)} |")

    lines.extend(["", "## 观察提醒预览", ""])
    payloads = payload_file.get("payloads", [])
    if not payloads:
        lines.append("暂无观察提醒。")
    for payload in payloads:
        symbol = payload.get('symbol', '')
        tf = payload.get('timeframe', '')
        direction = payload.get('direction', 'NO_TRADE')
        direction_cn = DIRECTION_CN.get(direction, direction)
        lines.extend([
            f"### {symbol}｜{tf}｜{direction_cn}",
            "",
            "```text",
            str(payload.get("message_text", "")),
            "```",
            "",
        ])

    lines.extend([
        "## 安全边界",
        "",
        "- 纸面观察，不下单",
        "- 不发送 webhook",
        "- 不读取 secret / .env",
        "- 不涉及账户、订单、testnet、live",
        "- 不构成交易建议",
        "",
        "## 验证",
        "",
        str(payload_file.get("final_verdict", "")),
        "",
    ])
    return "\n".join(lines)


def _message_text(plan: dict[str, Any]) -> str:
    symbol = plan.get('symbol', '')
    tf = plan.get('timeframe', '')
    direction = plan.get('direction', 'NO_TRADE')
    direction_cn = DIRECTION_CN.get(direction, direction)
    tf_cn = TIMEFRAME_CN.get(tf, tf)
    reason = plan.get('reason', '')
    reason_cn = _reason_to_chinese(reason, direction)

    return (
        f"状态：纸面观察，不下单\n"
        f"触发：{reason_cn}\n"
        f"观察价：{plan.get('entry_observation')}\n"
        f"失效价：{plan.get('invalidation_level')}\n"
        f"目标观察：{plan.get('take_profit_observation')}\n"
        f"R:R：{plan.get('rr_ratio')}\n"
        f"风险距离：{plan.get('risk_distance_pct')}%\n"
        f"目标空间：{plan.get('reward_distance_pct')}%\n"
        f"\n"
        f"处理建议：{_suggestion_cn(direction, tf)}\n"
        f"安全边界：paper-only / readonly-only / no order / no testnet / no live"
    )


def _reason_to_chinese(reason: str, direction: str) -> str:
    """Convert reason string to Chinese description."""
    if not reason:
        return "信号分析完成"
    reason_lower = reason.lower()
    if "macd" in reason_lower and ("green" in reason_lower or "bullish" in reason_lower or "expanding" in reason_lower):
        if direction == "SHORT_OBSERVE":
            return "MACD 红柱扩张，短周期偏弱"
        return "MACD 绿柱扩张，短周期开始转强"
    if "macd" in reason_lower and ("red" in reason_lower or "bearish" in reason_lower):
        return "MACD 红柱扩张，短周期偏弱"
    if "turning" in reason_lower or "near_turn" in reason_lower:
        return "MACD 即将转折，等待确认"
    if "weakness" in reason_lower:
        return "弱势信号，MACD 持续走弱"
    if "long_ready" in reason_lower or "long_watch" in reason_lower:
        return "多头信号增强，观察中"
    if "short_watch" in reason_lower:
        return "空头信号增强，观察中"
    if "degraded" in reason_lower:
        return "信号走弱，已失效"
    if "still" in reason_lower:
        return "信号维持，继续等待确认"
    # Fallback: keep original but truncate
    return reason[:60] if len(reason) > 60 else reason


def _suggestion_cn(direction: str, tf: str) -> str:
    """Generate Chinese suggestion based on direction and timeframe."""
    if direction == "SHORT_OBSERVE":
        if tf in ("5m",):
            return "空头观察中；等 15m 共振确认再行动。"
        if tf in ("15m",):
            return "空头观察中；等 1h 确认趋势。"
        return "空头信号观察中；不追空。"
    # LONG_OBSERVE
    if tf in ("5m",):
        return "只观察；未再次确认前不追。"
    if tf in ("15m",):
        return "优先等 5m 与 15m 共振，不单独追高。"
    if tf in ("1h",):
        return "等待 1h 级别确认，不急于入场。"
    return "只观察；确认后再行动。"


def _feishu_card(title: str, message: str, plan: dict[str, Any], created_at: str) -> dict[str, Any]:
    return {
        "msg_type": "interactive",
        "card": {
            "header": {
                "template": "orange",
                "title": {"tag": "plain_text", "content": title},
            },
            "elements": [
                {"tag": "div", "text": {"tag": "plain_text", "content": message}},
                {
                    "tag": "div",
                    "fields": [
                        _field("观察价", plan.get("entry_observation")),
                        _field("失效价", plan.get("invalidation_level")),
                        _field("目标观察", plan.get("take_profit_observation")),
                        _field("R:R", plan.get("rr_ratio")),
                    ],
                },
                {"tag": "div", "text": {"tag": "plain_text", "content": f"生成时间: {created_at}"}},
                {"tag": "hr"},
                {
                    "tag": "note",
                    "elements": [
                        {
                            "tag": "plain_text",
                            "content": "纸面观察，不下单。不构成交易建议。",
                        }
                    ],
                },
            ],
        },
    }


def _field(label: str, value: Any) -> dict[str, Any]:
    return {"is_short": True, "text": {"tag": "plain_text", "content": f"{label}: {value}"}}


def _plan_ref(plan: dict[str, Any]) -> dict[str, Any]:
    return {
        "symbol": plan.get("symbol"),
        "timeframe": plan.get("timeframe"),
        "direction": plan.get("direction"),
        "source_status": plan.get("source_status"),
        "reason": plan.get("reason"),
    }


def _dedup_key(symbol: str, timeframe: str, direction: str, plan: dict[str, Any]) -> str:
    raw = "|".join([
        symbol,
        timeframe,
        direction,
        str(plan.get("entry_observation")),
        str(plan.get("invalidation_level")),
        str(plan.get("take_profit_observation")),
    ])
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:20]


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _today_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")
