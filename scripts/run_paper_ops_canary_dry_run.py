"""Runner: paper ops canary dry-run."""
from __future__ import annotations
import json, pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from src.paper_trading_deployment.canary_runner import run_canary

OUT = pathlib.Path("reports/paper_trading_deployment/canary.json")


def main() -> None:
    report = run_canary()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report.to_dict(), indent=2), encoding="utf-8")
    print(f"status={report.canary_status} passed={report.steps_passed} failed={report.steps_failed} verdict={report.final_verdict}")


if __name__ == "__main__":
    main()
