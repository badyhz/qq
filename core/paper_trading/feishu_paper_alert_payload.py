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
    title = f"[PAPER WATCH] {symbol} {timeframe} {direction}"
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
        f"# Phase 10C-3J Feishu-Ready Paper Alert Payload - {payload_file.get('date', '')}",
        "",
        f"**Source mode:** {payload_file.get('source_mode', '')}",
        f"**Payload scope:** {payload_file.get('payload_scope', '')}",
        f"**Payload count:** {payload_file.get('payload_count', 0)}",
        "",
        "## Decision Summary",
        "",
        "| Decision | Count |",
        "|---|---:|",
    ]
    counts = payload_file.get("decision_counts", {})
    for decision in ["WATCH", "WAIT", "AVOID"]:
        lines.append(f"| {decision} | {int(counts.get(decision, 0) or 0)} |")

    lines.extend(["", "## Payload Preview", ""])
    payloads = payload_file.get("payloads", [])
    if not payloads:
        lines.append("No WATCH payloads generated.")
    for payload in payloads:
        lines.extend([
            f"### {payload.get('title', '')}",
            "",
            f"- priority: {payload.get('priority', '')}",
            f"- symbol: {payload.get('symbol', '')}",
            f"- timeframe: {payload.get('timeframe', '')}",
            f"- direction: {payload.get('direction', '')}",
            f"- dry_run_only: {payload.get('dry_run_only')}",
            f"- actually_sent: {payload.get('actually_sent')}",
            f"- webhook_send_attempted: {payload.get('webhook_send_attempted')}",
            f"- not_order_payload: {payload.get('not_order_payload')}",
            "",
            "```text",
            str(payload.get("message_text", "")),
            "```",
            "",
        ])

    lines.extend([
        "## Safety",
        "",
        "- Paper-only observation alert payload.",
        "- No webhook send attempted.",
        "- No secrets, accounts, orders, testnet, or live trading.",
        "- Not a trading recommendation.",
        "",
        "## Verdict",
        "",
        str(payload_file.get("final_verdict", "")),
        "",
    ])
    return "\n".join(lines)


def _message_text(plan: dict[str, Any]) -> str:
    return (
        f"{plan.get('symbol')} {plan.get('timeframe')} {plan.get('direction')} | "
        f"entry_observation={plan.get('entry_observation')} | "
        f"invalidation_level={plan.get('invalidation_level')} | "
        f"take_profit_observation={plan.get('take_profit_observation')} | "
        f"rr={plan.get('rr_ratio')} | "
        f"risk={plan.get('risk_distance_pct')}% | "
        f"reward={plan.get('reward_distance_pct')}% | "
        f"reason={plan.get('reason')} | "
        "paper-only; no order; no webhook sent"
    )


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
                        _field("Entry", plan.get("entry_observation")),
                        _field("Invalidation", plan.get("invalidation_level")),
                        _field("Take Profit", plan.get("take_profit_observation")),
                        _field("R:R", plan.get("rr_ratio")),
                    ],
                },
                {"tag": "div", "text": {"tag": "plain_text", "content": f"Created: {created_at}"}},
                {"tag": "hr"},
                {
                    "tag": "note",
                    "elements": [
                        {
                            "tag": "plain_text",
                            "content": "DRY RUN ONLY. No webhook sent. Not a trading recommendation.",
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
