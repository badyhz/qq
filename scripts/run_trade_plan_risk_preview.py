"""Runner: trade plan risk preview."""
from __future__ import annotations
import json, pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from src.trade_plan_engine.signal_adapter import adapt_signals
from src.trade_plan_engine.entry_plan import generate_entry_plan
from src.trade_plan_engine.exit_plan import compute_stop_loss
from src.trade_plan_engine.risk_plan import calculate_risk_plan
from src.external_scanner_integrations.macd_rebound_config import create_config

OUT = pathlib.Path("reports/trade_plan/risk_preview.json")
MD = pathlib.Path("reports/trade_plan/risk_preview.md")


def main() -> None:
    cfg = create_config()
    if not cfg.local_path:
        print("ERROR: scanner path not found")
        sys.exit(1)
    result = adapt_signals(cfg.local_path)
    previews: list[dict] = []
    for sig in result.candidates:
        entry = generate_entry_plan(sig)
        sl = compute_stop_loss(entry["entry_price"], sig.ma25)
        risk = calculate_risk_plan(entry["entry_price"], sl)
        previews.append({
            "symbol": sig.symbol, "entry_price": entry["entry_price"],
            "stop_loss": sl, "risk_plan": risk.to_dict(),
        })
    out_data = {"previews": previews, "total": len(previews),
        "final_verdict": f"TRADE_RISK_PLAN_READY|PREVIEWS={len(previews)}|REAL_ORDER_SUBMIT_NOT_ALLOWED"}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out_data, indent=2), encoding="utf-8")
    MD.parent.mkdir(parents=True, exist_ok=True)
    lines = ["# Risk Preview", "", f"**total={len(previews)}**", "",
        "| Symbol | Entry | SL | Risk Level | Suggested Qty |",
        "|--------|-------|-----|-----------|---------------|"]
    for p in previews:
        rp = p["risk_plan"]
        lines.append(f"| {p['symbol']} | {p['entry_price']} | {p['stop_loss']} | {rp['risk_level']} | {rp['suggested_quantity_placeholder']:.6f} |")
    lines.extend(["", "## Conclusion", "", out_data["final_verdict"], ""])
    MD.write_text("\n".join(lines), encoding="utf-8")
    print(f"previews={len(previews)} verdict={out_data['final_verdict']}")


if __name__ == "__main__":
    main()
