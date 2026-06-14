"""Runner: paper trade plan batch builder."""
from __future__ import annotations
import json, pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from src.paper_trading_pipeline.scanner_log_source import load_scanner_snapshot
from src.paper_trading_pipeline.signal_deduplicator import deduplicate_signals
from src.paper_trading_pipeline.trade_plan_batch_builder import build_trade_plans
from src.external_scanner_integrations.macd_rebound_config import create_config
from src.external_scanner_integrations.macd_rebound_log_ingest import _read_csv, _read_jsonl

OUT = pathlib.Path("reports/paper_trading/trade_plan_batch.json")


def main() -> None:
    cfg = create_config()
    if not cfg.local_path:
        print("ERROR: scanner path not found")
        sys.exit(1)
    root = pathlib.Path(cfg.local_path)
    snap = load_scanner_snapshot(cfg.local_path)
    signals = _read_csv(root / "data" / "signals.csv")
    alerts = _read_jsonl(root / "logs" / "alerts.jsonl")
    deduped = deduplicate_signals(signals, alerts)
    batch = build_trade_plans(list(deduped.signals), snap.snapshot_id)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(batch.to_dict(), indent=2), encoding="utf-8")
    print(f"created={batch.plans_created} rejected={batch.plans_rejected} verdict={batch.final_verdict}")


if __name__ == "__main__":
    main()
