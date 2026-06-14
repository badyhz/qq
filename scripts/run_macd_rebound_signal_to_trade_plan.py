"""Runner: convert MACD rebound signals to trade plans."""
from __future__ import annotations
import json, pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from src.trade_plan_engine.signal_adapter import adapt_signals, write_result, render_report
from src.trade_plan_engine.entry_plan import generate_entry_plan
from src.trade_plan_engine.exit_plan import compute_stop_loss, compute_take_profits
from src.trade_plan_engine.risk_plan import calculate_risk_plan
from src.trade_plan_engine.models import TradePlan, new_id, utc_now_iso
from src.external_scanner_integrations.macd_rebound_config import create_config

OUT = pathlib.Path("reports/trade_plan/signal_to_plan.json")
MD = pathlib.Path("reports/trade_plan/signal_to_plan.md")


def main() -> None:
    cfg = create_config()
    if not cfg.local_path:
        print("ERROR: scanner path not found")
        sys.exit(1)
    result = adapt_signals(cfg.local_path)
    plans: list[dict] = []
    for sig in result.candidates:
        entry = generate_entry_plan(sig)
        sl = compute_stop_loss(entry["entry_price"], sig.ma25)
        tp1, tp2, tp3 = compute_take_profits(entry["entry_price"], sl)
        risk = calculate_risk_plan(entry["entry_price"], sl)
        r = entry["entry_price"] - sl
        plan = TradePlan(
            plan_id=new_id("TP"),
            signal_id=sig.signal_id, symbol=sig.symbol, timeframe=sig.timeframe,
            side="LONG", entry_type=entry["entry_type"],
            entry_price=entry["entry_price"],
            entry_zone_low=entry["entry_zone_low"],
            entry_zone_high=entry["entry_zone_high"],
            stop_loss=sl, take_profit_1=tp1, take_profit_2=tp2, take_profit_3=tp3,
            risk_pct=round(abs(sl - entry["entry_price"]) / entry["entry_price"] * 100, 2),
            reward_risk_1=round(1.5, 2), reward_risk_2=round(2.5, 2), reward_risk_3=round(4.0, 2),
            position_size_hint=risk.suggested_quantity_placeholder,
            max_account_risk_pct=0.01,
            plan_grade="B" if entry["confidence"] != "LOW" else "C",
            valid_until="4h", invalid_if="price < ma25 or MACD histogram negative",
            explain=entry["entry_reason"],
            dry_run_only=True,
        )
        if risk.risk_level == "REJECTED":
            plan = TradePlan(
                plan_id=plan.plan_id, signal_id=plan.signal_id, symbol=plan.symbol,
                timeframe=plan.timeframe, side=plan.side, entry_type=plan.entry_type,
                entry_price=plan.entry_price, entry_zone_low=plan.entry_zone_low,
                entry_zone_high=plan.entry_zone_high, stop_loss=plan.stop_loss,
                take_profit_1=plan.take_profit_1, take_profit_2=plan.take_profit_2,
                take_profit_3=plan.take_profit_3, risk_pct=plan.risk_pct,
                reward_risk_1=plan.reward_risk_1, reward_risk_2=plan.reward_risk_2,
                reward_risk_3=plan.reward_risk_3, position_size_hint=plan.position_size_hint,
                max_account_risk_pct=plan.max_account_risk_pct, plan_grade="REJECTED",
                valid_until=plan.valid_until, invalid_if=plan.invalid_if,
                explain=risk.risk_notes, dry_run_only=True,
            )
        plans.append(plan.to_dict())

    out_data = {
        "adapter": result.to_dict(),
        "plans": plans,
        "total_plans": len(plans),
        "final_verdict": f"MACD_REBOUND_SIGNAL_TO_TRADE_PLAN_READY|PLANS={len(plans)}|REAL_ORDER_SUBMIT_NOT_ALLOWED",
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out_data, indent=2), encoding="utf-8")
    MD.parent.mkdir(parents=True, exist_ok=True)
    lines = ["# Signal to Trade Plan", "", f"**total_plans={len(plans)}**", "",
        "| Symbol | Grade | Entry | SL | TP1 | Risk% |",
        "|--------|-------|-------|-----|-----|-------|"]
    for p in plans:
        lines.append(f"| {p['symbol']} | {p['plan_grade']} | {p['entry_price']} | {p['stop_loss']} | {p['take_profit_1']} | {p['risk_pct']}% |")
    lines.extend(["", "## Conclusion", "", out_data["final_verdict"], ""])
    MD.write_text("\n".join(lines), encoding="utf-8")
    print(f"plans={len(plans)} verdict={out_data['final_verdict']}")


if __name__ == "__main__":
    main()
