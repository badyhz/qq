"""Runner: paper ops deployment safety regression."""
from __future__ import annotations
import json, pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from src.paper_trading_deployment.deployment_safety_regression import run_safety_regression

OUT = pathlib.Path("reports/paper_trading_deployment/safety_regression.json")


def main() -> None:
    report = run_safety_regression()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report.to_dict(), indent=2), encoding="utf-8")
    print(f"checked={report.total_checked} flagged={report.total_flagged} verdict={report.final_verdict}")


if __name__ == "__main__":
    main()
