"""Runner: paper position lifecycle simulation."""
from __future__ import annotations
import csv, json, pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from src.trade_plan_engine.signal_adapter import adapt_signals
from src.trade_plan_engine.entry_plan import generate_entry_plan
from src.trade_plan_engine.exit_plan import compute_stop_loss, compute_take_profits
from src.trade_plan_engine.risk_plan import calculate_risk_plan
from src.trade_plan_engine.paper_position import create_paper_position
from src.trade_plan_engine.paper_lifecycle import simulate_lifecycle, write_result, render_report
from src.trade_plan_engine.models import TradePlan, new_id
from src.external_scanner_integrations.macd_rebound_config import create_config

OUT = pathlib.Path("reports/trade_plan/paper_lifecycle.json")
MD = pathlib.Path("reports/trade_plan/paper_lifecycle.md")


def _read_ohlcv_csv(path: pathlib.Path) -> list[dict]:
    if not path.exists():
        return []
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def main() -> None:
    cfg = create_config()
    if not cfg.local_path:
        print("ERROR: scanner path not found")
        sys.exit(1)
    result = adapt_signals(cfg.local_path)
    positions = []
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
            valid_until="4h", invalid_if="", explain="", dry_run_only=True,
        )
        pp = create_paper_position(plan)
        pp = simulate_lifecycle(pp, [])  # no OHLCV data in this runner
        positions.append(pp)

    from src.trade_plan_engine.paper_lifecycle import LifecycleResult
    from src.trade_plan_engine.models import utc_now_iso
    lifecycle = LifecycleResult(
        lifecycle_id=new_id("LC"), created_at=utc_now_iso(),
        positions=tuple(positions), total_simulated=len(positions),
        final_verdict=f"PAPER_POSITION_LIFECYCLE_READY|SIMULATED={len(positions)}|REAL_ORDER_SUBMIT_NOT_ALLOWED",
    )
    write_result(lifecycle, OUT)
    MD.parent.mkdir(parents=True, exist_ok=True)
    MD.write_text(render_report(lifecycle), encoding="utf-8")
    print(f"positions={len(positions)} verdict={lifecycle.final_verdict}")


if __name__ == "__main__":
    main()
