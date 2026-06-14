"""Runner: paper ops log freshness check."""
from __future__ import annotations
import json, pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from src.paper_trading_ops.log_freshness_monitor import check_freshness
from src.external_scanner_integrations.macd_rebound_config import create_config

OUT = pathlib.Path("reports/paper_trading_ops/log_freshness.json")


def main() -> None:
    cfg = create_config()
    if not cfg.local_path:
        print("ERROR: scanner path not found")
        sys.exit(1)
    report = check_freshness(cfg.local_path)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report.to_dict(), indent=2), encoding="utf-8")
    print(f"status={report.freshness_status} verdict={report.final_verdict}")


if __name__ == "__main__":
    main()
