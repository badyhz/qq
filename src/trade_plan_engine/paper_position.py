"""Paper position creation from trade plans."""
from __future__ import annotations
from src.trade_plan_engine.models import TradePlan, PaperPosition, new_id, utc_now_iso


def create_paper_position(plan: TradePlan) -> PaperPosition:
    return PaperPosition(
        paper_position_id=new_id("PP"),
        plan_id=plan.plan_id,
        symbol=plan.symbol,
        side=plan.side,
        status="PLANNED",
        paper_entry_price=plan.entry_price,
        paper_entry_time="",
        paper_stop_loss=plan.stop_loss,
        paper_take_profit_1=plan.take_profit_1,
        paper_take_profit_2=plan.take_profit_2,
        paper_take_profit_3=plan.take_profit_3,
        paper_exit_price=0.0,
        paper_exit_time="",
        paper_exit_reason="",
        paper_pnl_r=0.0,
        paper_pnl_pct=0.0,
        bars_held=0,
        dry_run_only=True,
    )
