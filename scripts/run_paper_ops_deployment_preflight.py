"""Runner: paper ops deployment preflight."""
from __future__ import annotations
import json, pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from src.paper_trading_deployment.preflight_check import run_preflight
from src.paper_trading_deployment.server_config import build_server_config

OUT = pathlib.Path("reports/paper_trading_deployment/preflight.json")


def main() -> None:
    cfg = build_server_config()
    report = run_preflight(cfg.repo_path, cfg.scanner_path)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report.to_dict(), indent=2), encoding="utf-8")
    print(f"status={report.preflight_status} passed={report.checks_passed} failed={report.checks_failed} verdict={report.final_verdict}")


if __name__ == "__main__":
    main()
