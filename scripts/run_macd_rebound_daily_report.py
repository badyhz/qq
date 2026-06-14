"""Runner: MACD rebound daily report."""
from __future__ import annotations
import pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from src.external_scanner_integrations.macd_rebound_config import create_config
from src.external_scanner_integrations.macd_rebound_daily_report import generate_daily_report, write_report, render_report

OUT = pathlib.Path("reports/macd_rebound/daily_report.json")
MD = pathlib.Path("reports/macd_rebound/daily_report.md")

def main() -> None:
    cfg = create_config()
    if not cfg.local_path:
        print("ERROR: scanner path not found")
        sys.exit(1)
    report = generate_daily_report(cfg.local_path)
    write_report(report, OUT)
    MD.parent.mkdir(parents=True, exist_ok=True)
    MD.write_text(render_report(report), encoding="utf-8")
    print(f"status={report.scanner_status} score={report.health_score}% verdict={report.final_verdict}")

if __name__ == "__main__":
    main()
