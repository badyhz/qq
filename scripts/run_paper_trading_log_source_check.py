"""Runner: paper trading scanner log source check."""
from __future__ import annotations
import json, pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from src.paper_trading_pipeline.scanner_log_source import load_scanner_snapshot
from src.external_scanner_integrations.macd_rebound_config import create_config

OUT = pathlib.Path("reports/paper_trading/log_source.json")


def main() -> None:
    cfg = create_config()
    if not cfg.local_path:
        print("ERROR: scanner path not found")
        sys.exit(1)
    snap = load_scanner_snapshot(cfg.local_path)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(snap.to_dict(), indent=2), encoding="utf-8")
    print(f"signals={snap.signals_count} alerts={snap.alerts_count} errors={snap.errors_count} verdict={snap.final_verdict}")


if __name__ == "__main__":
    main()
