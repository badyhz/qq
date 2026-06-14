"""Runner: paper position store update."""
from __future__ import annotations
import json, pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from src.paper_trading_pipeline.scanner_log_source import load_scanner_snapshot
from src.paper_trading_pipeline.signal_deduplicator import deduplicate_signals
from src.paper_trading_pipeline.trade_plan_batch_builder import build_trade_plans
from src.paper_trading_pipeline.paper_position_store import append_new_positions, load_store, DEFAULT_STORE_PATH
from src.external_scanner_integrations.macd_rebound_config import create_config
from src.external_scanner_integrations.macd_rebound_log_ingest import _read_csv, _read_jsonl

OUT = pathlib.Path("reports/paper_trading/position_store.json")


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
    records, added = append_new_positions([p for p in batch.plans])
    total = len(records)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({"loaded": total - added, "added": added, "total": total,
        "final_verdict": f"PAPER_POSITION_STORE_READY|LOADED={total - added}|ADDED={added}|TOTAL={total}|REAL_ORDER_SUBMIT_NOT_ALLOWED"}, indent=2), encoding="utf-8")
    print(f"loaded={total - added} added={added} total={total} verdict=PAPER_POSITION_STORE_READY")


if __name__ == "__main__":
    main()
