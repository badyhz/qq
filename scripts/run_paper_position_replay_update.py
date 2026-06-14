"""Runner: paper position replay update."""
from __future__ import annotations
import json, pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from src.paper_trading_pipeline.paper_position_store import load_store, DEFAULT_STORE_PATH
from src.paper_trading_pipeline.paper_position_updater import update_positions_batch
from src.paper_trading_pipeline.paper_replay_scheduler import build_replay_schedule

OUT = pathlib.Path("reports/paper_trading/replay_update.json")


def main() -> None:
    records = load_store()
    schedule = build_replay_schedule(records)
    # No OHLCV data in this runner — just report schedule
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({
        "schedule": schedule.to_dict(),
        "positions_total": len(records),
        "final_verdict": f"PAPER_POSITION_UPDATE_READY|TOTAL={len(records)}|NEEDS_ENTRY={schedule.needs_entry_check}|NEEDS_EXIT={schedule.needs_exit_check}|REAL_ORDER_SUBMIT_NOT_ALLOWED",
    }, indent=2), encoding="utf-8")
    print(f"total={len(records)} needs_entry={schedule.needs_entry_check} needs_exit={schedule.needs_exit_check} verdict=PAPER_POSITION_UPDATE_READY")


if __name__ == "__main__":
    main()
