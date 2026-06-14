"""Runner: daily paper trading review."""
from __future__ import annotations
import json, pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from src.paper_trading_pipeline.scanner_log_source import load_scanner_snapshot
from src.paper_trading_pipeline.signal_deduplicator import deduplicate_signals
from src.paper_trading_pipeline.trade_plan_batch_builder import build_trade_plans
from src.paper_trading_pipeline.paper_position_store import load_store
from src.paper_trading_pipeline.paper_replay_scheduler import build_replay_schedule
from src.paper_trading_pipeline.daily_paper_review import generate_daily_review
from src.external_scanner_integrations.macd_rebound_config import create_config
from src.external_scanner_integrations.macd_rebound_log_ingest import _read_csv, _read_jsonl

OUT = pathlib.Path("reports/paper_trading/daily_review.json")
MD = pathlib.Path("reports/paper_trading/daily_review.md")


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
    schedule = build_replay_schedule(positions)
    review = generate_daily_review(snap, deduped, batch, positions, schedule)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(review.to_dict(), indent=2), encoding="utf-8")
    MD.parent.mkdir(parents=True, exist_ok=True)
    lines = ["# Daily Paper Trading Review", "", f"**date={review.date}**", "",
        f"- raw_signals: {review.raw_signals}", f"- deduped: {review.deduped_signals}",
        f"- plans: {review.trade_plans_created}", f"- positions: {review.paper_positions_total}",
        f"- open: {review.paper_open_count}", f"- closed: {review.paper_closed_count}",
        f"- tp1: {review.tp1_count}", f"- stops: {review.stop_count}", "",
        "## Conclusion", "", review.final_verdict, ""]
    MD.write_text("\n".join(lines), encoding="utf-8")
    print(f"signals={review.raw_signals} plans={review.trade_plans_created} positions={review.paper_positions_total} verdict={review.final_verdict}")


if __name__ == "__main__":
    main()
