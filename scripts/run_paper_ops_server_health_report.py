"""Runner: paper ops server health report."""
from __future__ import annotations
import json, pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from src.paper_trading_deployment.server_health_report import generate_health_report

OUT = pathlib.Path("reports/paper_trading_deployment/server_health.json")


def main() -> None:
    report = generate_health_report()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report.to_dict(), indent=2), encoding="utf-8")
    print(f"score={report.health_score} status={report.health_status} verdict={report.final_verdict}")


if __name__ == "__main__":
    main()
