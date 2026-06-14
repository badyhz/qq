"""Feishu trade plan payload generator — dry-run only, no real send."""
from __future__ import annotations
import json, pathlib
from dataclasses import dataclass
from datetime import datetime, timezone

from src.trade_plan_engine.models import TradePlan, new_id, utc_now_iso


@dataclass(frozen=True)
class FeishuPayload:
    payload_id: str
    created_at: str
    title: str
    symbol: str
    timeframe: str
    side: str
    plan_grade: str
    entry_zone: str
    stop_loss: float
    take_profit_1: float
    take_profit_2: float
    take_profit_3: float
    risk_pct: float
    position_size_hint: float
    invalid_if: str
    dry_run_only: bool
    risk_warning: str
    final_verdict: str

    def to_dict(self) -> dict:
        return {
            "payload_id": self.payload_id, "created_at": self.created_at,
            "title": self.title, "symbol": self.symbol,
            "timeframe": self.timeframe, "side": self.side,
            "plan_grade": self.plan_grade, "entry_zone": self.entry_zone,
            "stop_loss": self.stop_loss,
            "take_profit_1": self.take_profit_1,
            "take_profit_2": self.take_profit_2,
            "take_profit_3": self.take_profit_3,
            "risk_pct": self.risk_pct,
            "position_size_hint": self.position_size_hint,
            "invalid_if": self.invalid_if,
            "dry_run_only": self.dry_run_only,
            "risk_warning": self.risk_warning,
            "final_verdict": self.final_verdict,
        }


def generate_payload(plan: TradePlan) -> FeishuPayload:
    entry_zone = f"{plan.entry_zone_low:.8f} - {plan.entry_zone_high:.8f}"
    title = f"[DRY-RUN] {plan.symbol} {plan.side} {plan.plan_grade}"

    return FeishuPayload(
        payload_id=new_id("FP"),
        created_at=utc_now_iso(),
        title=title,
        symbol=plan.symbol,
        timeframe=plan.timeframe,
        side=plan.side,
        plan_grade=plan.plan_grade,
        entry_zone=entry_zone,
        stop_loss=plan.stop_loss,
        take_profit_1=plan.take_profit_1,
        take_profit_2=plan.take_profit_2,
        take_profit_3=plan.take_profit_3,
        risk_pct=plan.risk_pct,
        position_size_hint=plan.position_size_hint,
        invalid_if=plan.invalid_if,
        dry_run_only=True,
        risk_warning="THIS IS A DRY-RUN PAYLOAD. NO REAL ORDER WILL BE PLACED.",
        final_verdict="FEISHU_TRADE_PLAN_PAYLOAD_DRY_RUN_READY|DRY_RUN_ONLY=TRUE|REAL_ORDER_SUBMIT_NOT_ALLOWED",
    )


def write_payload(payload: FeishuPayload, out: pathlib.Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload.to_dict(), indent=2), encoding="utf-8")


def render_report(payload: FeishuPayload) -> str:
    lines = ["# Feishu Trade Plan Payload (Dry-Run)", "",
        f"**payload_id={payload.payload_id}**",
        f"**title={payload.title}**", "",
        f"- symbol: {payload.symbol}",
        f"- timeframe: {payload.timeframe}",
        f"- side: {payload.side}",
        f"- plan_grade: {payload.plan_grade}",
        f"- entry_zone: {payload.entry_zone}",
        f"- stop_loss: {payload.stop_loss}",
        f"- take_profit_1: {payload.take_profit_1}",
        f"- take_profit_2: {payload.take_profit_2}",
        f"- take_profit_3: {payload.take_profit_3}",
        f"- risk_pct: {payload.risk_pct}%",
        f"- position_size_hint: {payload.position_size_hint}",
        f"- invalid_if: {payload.invalid_if}",
        f"- dry_run_only: {payload.dry_run_only}",
        f"- risk_warning: {payload.risk_warning}", "",
        "## Conclusion", "", payload.final_verdict, ""]
    return "\n".join(lines)
