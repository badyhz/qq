"""Runner: Feishu trade plan payload dry-run."""
from __future__ import annotations
import json, pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from src.trade_plan_engine.signal_adapter import adapt_signals
from src.trade_plan_engine.entry_plan import generate_entry_plan
from src.trade_plan_engine.exit_plan import compute_stop_loss, compute_take_profits
from src.trade_plan_engine.risk_plan import calculate_risk_plan
from src.trade_plan_engine.feishu_trade_plan_payload import generate_payload, write_payload, render_report
from src.trade_plan_engine.models import TradePlan, new_id
from src.external_scanner_integrations.macd_rebound_config import create_config

OUT = pathlib.Path("reports/trade_plan/feishu_payload_dry_run.json")
MD = pathlib.Path("reports/trade_plan/feishu_payload_dry_run.md")


def main() -> None:
    cfg = create_config()
    if not cfg.local_path:
        print("ERROR: scanner path not found")
        sys.exit(1)
    result = adapt_signals(cfg.local_path)
    payloads = []
    for sig in result.candidates:
        entry = generate_entry_plan(sig)
        sl = compute_stop_loss(entry["entry_price"], sig.ma25)
        tp1, tp2, tp3 = compute_take_profits(entry["entry_price"], sl)
        plan = TradePlan(
            plan_id=new_id("TP"), signal_id=sig.signal_id, symbol=sig.symbol,
            timeframe=sig.timeframe, side="LONG", entry_type=entry["entry_type"],
            entry_price=entry["entry_price"], entry_zone_low=entry["entry_zone_low"],
            entry_zone_high=entry["entry_zone_high"], stop_loss=sl,
            take_profit_1=tp1, take_profit_2=tp2, take_profit_3=tp3,
            risk_pct=round(abs(sl - entry["entry_price"]) / entry["entry_price"] * 100, 2),
            reward_risk_1=1.5, reward_risk_2=2.5, reward_risk_3=4.0,
            position_size_hint=0.0, max_account_risk_pct=0.01, plan_grade="B",
            valid_until="4h", invalid_if="price < ma25", explain="", dry_run_only=True,
        )
        payload = generate_payload(plan)
        payloads.append(payload.to_dict())

    out_data = {"payloads": payloads, "total": len(payloads),
        "final_verdict": "FEISHU_TRADE_PLAN_PAYLOAD_DRY_RUN_READY|DRY_RUN_ONLY=TRUE|REAL_ORDER_SUBMIT_NOT_ALLOWED"}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out_data, indent=2), encoding="utf-8")
    MD.parent.mkdir(parents=True, exist_ok=True)
    lines = ["# Feishu Trade Plan Payload (Dry-Run)", "", f"**total={len(payloads)}**", ""]
    for p in payloads:
        lines.append(f"- {p['title']} | {p['symbol']} | dry_run_only={p['dry_run_only']}")
    lines.extend(["", "## Conclusion", "", out_data["final_verdict"], ""])
    MD.write_text("\n".join(lines), encoding="utf-8")
    print(f"payloads={len(payloads)} verdict={out_data['final_verdict']}")


if __name__ == "__main__":
    main()
