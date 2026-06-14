"""Runner: MACD rebound integration safety regression."""
from __future__ import annotations
import pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from src.external_scanner_integrations.macd_rebound_safety_regression import run_safety_regression, write_report, render_report

OUT = pathlib.Path("reports/macd_rebound/safety_regression.json")
MD = pathlib.Path("reports/macd_rebound/safety_regression.md")

def main() -> None:
    report = run_safety_regression()
    write_report(report, OUT)
    MD.parent.mkdir(parents=True, exist_ok=True)
    MD.write_text(render_report(report), encoding="utf-8")
    print(f"checked={report.total_checked} clean={report.total_clean} flagged={report.total_flagged} verdict={report.final_verdict}")

if __name__ == "__main__":
    main()
