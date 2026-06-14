"""Runner: Feishu paper review payload dry-run."""
from __future__ import annotations
import json, pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from src.paper_trading_pipeline.scanner_log_source import load_scanner_snapshot
from src.paper_trading_pipeline.signal_deduplicator import deduplicate_signals
from src.paper_trading_pipeline.trade_plan_batch_builder import build_trade_plans
from src.paper_trading_pipeline.paper_position_store import load_store
from src.paper_trading_pipeline.daily_paper_review import generate_daily_review
from src.paper_trading_pipeline.feishu_paper_review_payload import generate_feishu_payload
from src.external_scanner_integrations.macd_rebound_config import create_config
from src.external_scanner_integrations.macd_rebound_log_ingest import _read_csv, _read_jsonl

OUT = pathlib.Path("reports/paper_trading/feishu_payload_dry_run.json")


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
    positions = load_store()
    review = generate_daily_review(snap, deduped, batch, positions)
    payload = generate_feishu_payload(review)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload.to_dict(), indent=2), encoding="utf-8")
    print(f"dry_run_only={payload.dry_run_only} verdict={payload.final_verdict}")


if __name__ == "__main__":
    main()
