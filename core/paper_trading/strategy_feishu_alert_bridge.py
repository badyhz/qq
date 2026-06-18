"""Strategy → Feishu alert bridge. Reads strategy_payload_input, produces Feishu payloads.

Pure renderer. No network, no secrets, no webhook send, no orders.
"""
from __future__ import annotations

import hashlib
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from core.paper_trading.feishu_paper_alert_payload import (
    DIRECTION_CN,
    TIMEFRAME_CN,
    PAYLOAD_SAFETY_FLAGS,
    FINAL_VERDICT,
    _reason_to_chinese,
    _suggestion_cn,
)

WATCH_STATE_CN = {
    "LONG_READY": "多头就绪",
    "LONG_WATCH": "多头观察",
    "NEAR_TURN_UP": "即将转折向上",
    "SHORT_WATCH": "空头观察",
    "WEAK_AVOID": "弱势回避",
}

PRIORITY_CN = {
    "HIGH": "高",
    "MEDIUM": "中",
    "LOW": "低",
}


@dataclass(frozen=True)
class StrategyFeishuPayload:
    payload_id: str
    created_at: str
    strategy_id: str
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
            "strategy_id": self.strategy_id,
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


def build_strategy_payloads(payload_input: dict[str, Any]) -> dict[str, Any]:
    """Build Feishu payload file from strategy_payload_input.json."""
    plans = [p for p in payload_input.get("plans", []) if isinstance(p, dict)]
    watch_plans = [p for p in plans if p.get("plan_decision") == "WATCH"]

    payloads = [_build_one_payload(plan).to_dict() for plan in watch_plans]
    date = str(payload_input.get("date") or _today_utc())

    return {
        "date": date,
        "source_mode": str(payload_input.get("mode") or "unknown"),
        "source_total_plans": len(plans),
        "decision_counts": payload_input.get("decision_counts", {}),
        "payload_count": len(payloads),
        "payload_scope": "WATCH_ONLY",
        "payloads": payloads,
        "dry_run_only": True,
        "actually_sent": False,
        "webhook_send_attempted": False,
        "not_order_payload": True,
        "safety_flags": list(PAYLOAD_SAFETY_FLAGS),
        "final_verdict": FINAL_VERDICT,
    }


def _build_one_payload(plan: dict[str, Any]) -> StrategyFeishuPayload:
    """Build one Feishu payload for one WATCH plan."""
    strategy_id = str(plan.get("reason", "").split(":")[0].strip() or "unknown")
    symbol = str(plan.get("symbol") or "")
    timeframe = str(plan.get("timeframe") or "")
    direction = str(plan.get("direction") or "NO_TRADE")
    direction_cn = DIRECTION_CN.get(direction, direction)
    source_status = str(plan.get("source_status") or "")
    priority = str(plan.get("plan_decision") or "WATCH")

    title = f"[PAPER STRATEGY] {strategy_id}｜{symbol}｜{timeframe}｜{direction_cn}"
    created_at = _utc_now_iso()
    message = _message_text(plan, strategy_id)
    dedup_key = _dedup_key(strategy_id, symbol, timeframe, direction, plan)

    return StrategyFeishuPayload(
        payload_id=f"SPA_{uuid.uuid4().hex[:12]}",
        created_at=created_at,
        strategy_id=strategy_id,
        symbol=symbol,
        timeframe=timeframe,
        direction=direction,
        priority=priority,
        title=title,
        message_text=message,
        dedup_key=dedup_key,
        feishu_payload=_feishu_card(title, message, plan, strategy_id, created_at),
        source_plan=dict(plan),
        dry_run_only=True,
        actually_sent=False,
        webhook_send_attempted=False,
        not_order_payload=True,
        safety_flags=list(PAYLOAD_SAFETY_FLAGS),
        final_verdict=FINAL_VERDICT,
    )


def _message_text(plan: dict[str, Any], strategy_id: str) -> str:
    symbol = plan.get("symbol", "")
    tf = plan.get("timeframe", "")
    direction = plan.get("direction", "NO_TRADE")
    direction_cn = DIRECTION_CN.get(direction, direction)
    tf_cn = TIMEFRAME_CN.get(tf, tf)
    source_status = plan.get("source_status", "")
    status_cn = WATCH_STATE_CN.get(source_status, source_status)
    reason = plan.get("reason", "")
    reason_cn = _reason_to_chinese(reason, direction)

    return (
        f"策略：{strategy_id}\n"
        f"标的：{symbol}\n"
        f"周期：{tf_cn}\n"
        f"方向：{direction_cn}\n"
        f"优先级：WATCH\n"
        f"触发状态：{status_cn}\n"
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


def render_strategy_markdown(payload_file: dict[str, Any]) -> str:
    """Render human-readable markdown from strategy Feishu payload file."""
    lines = [
        f"# 策略信号飞书预览 - {payload_file.get('date', '')}",
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
        lines.append(f"| {decision} | {int(counts.get(decision, 0) or 0)} |")

    lines.extend(["", "## 信号提醒预览", ""])
    payloads = payload_file.get("payloads", [])
    if not payloads:
        lines.append("暂无信号提醒。")
    for payload in payloads:
        strategy_id = payload.get("strategy_id", "")
        symbol = payload.get("symbol", "")
        tf = payload.get("timeframe", "")
        direction = payload.get("direction", "NO_TRADE")
        direction_cn = DIRECTION_CN.get(direction, direction)
        lines.extend([
            f"### {strategy_id}｜{symbol}｜{tf}｜{direction_cn}",
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


def _feishu_card(
    title: str, message: str, plan: dict[str, Any],
    strategy_id: str, created_at: str,
) -> dict[str, Any]:
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
                {"tag": "div", "text": {"tag": "plain_text", "content": f"策略: {strategy_id} | 生成时间: {created_at}"}},
                {"tag": "hr"},
                {
                    "tag": "note",
                    "elements": [
                        {"tag": "plain_text", "content": "纸面观察，不下单。不构成交易建议。"},
                    ],
                },
            ],
        },
    }


def _field(label: str, value: Any) -> dict[str, Any]:
    return {"is_short": True, "text": {"tag": "plain_text", "content": f"{label}: {value}"}}


def _dedup_key(
    strategy_id: str, symbol: str, timeframe: str,
    direction: str, plan: dict[str, Any],
) -> str:
    raw = "|".join([
        strategy_id, symbol, timeframe, direction,
        str(plan.get("entry_observation")),
        str(plan.get("invalidation_level")),
        str(plan.get("take_profit_observation")),
    ])
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:20]


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _today_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")
