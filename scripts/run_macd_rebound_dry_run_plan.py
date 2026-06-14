"""Runner: MACD rebound dry-run plan."""
from __future__ import annotations
import pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from src.external_scanner_integrations.macd_rebound_config import create_config
from src.external_scanner_integrations.macd_rebound_dry_run_plan import create_dry_run_plan, write_plan, render_report

OUT = pathlib.Path("reports/macd_rebound/dry_run_plan.json")
MD = pathlib.Path("reports/macd_rebound/dry_run_plan.md")

def main() -> None:
    cfg = create_config()
    if not cfg.local_path:
        print("ERROR: scanner path not found")
        sys.exit(1)
    plan = create_dry_run_plan(cfg.local_path)
    write_plan(plan, OUT)
    MD.parent.mkdir(parents=True, exist_ok=True)
    MD.write_text(render_report(plan), encoding="utf-8")
    print(f"steps={len(plan.steps)} verdict={plan.final_verdict}")

if __name__ == "__main__":
    main()
