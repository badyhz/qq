"""Paper position store — local JSONL state file."""
from __future__ import annotations
import json, pathlib
from src.paper_trading_pipeline.models import PaperPositionRecord, new_id, utc_now_iso

DEFAULT_STORE_PATH = pathlib.Path("data/runtime/paper_trading_pipeline/paper_positions.jsonl")


def load_store(path: pathlib.Path = DEFAULT_STORE_PATH) -> list[PaperPositionRecord]:
    if not path.exists():
        return []
    records: list[PaperPositionRecord] = []
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line:
                try:
                    d = json.loads(line)
                    records.append(PaperPositionRecord(**d))
                except (json.JSONDecodeError, TypeError):
                    pass
    except Exception:
        pass
    return records


def _write_store(records: list[PaperPositionRecord], path: pathlib.Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [json.dumps(r.to_dict()) for r in records]
    path.write_text("\n".join(lines) + "\n" if lines else "", encoding="utf-8")


def append_new_positions(
    plans: list[dict],
    store_path: pathlib.Path = DEFAULT_STORE_PATH,
) -> tuple[list[PaperPositionRecord], int]:
    existing = load_store(store_path)
    existing_plan_ids = {r.plan_id for r in existing}
    now = utc_now_iso()
    added = 0
    for p in plans:
        pid = p.get("plan_id", "")
        if pid in existing_plan_ids:
            continue
        record = PaperPositionRecord(
            record_id=new_id("PR"),
            paper_position_id=new_id("PP"),
            plan_id=pid,
            symbol=p.get("symbol", ""),
            timeframe=p.get("timeframe", "5m"),
            status="PLANNED",
            entry_price=p.get("entry_price", 0),
            stop_loss=p.get("stop_loss", 0),
            take_profit_1=p.get("take_profit_1", 0),
            take_profit_2=p.get("take_profit_2", 0),
            take_profit_3=p.get("take_profit_3", 0),
            created_at=now,
            updated_at=now,
            source_signal_id=p.get("signal_id", ""),
            dry_run_only=True,
        )
        existing.append(record)
        added += 1
    _write_store(existing, store_path)
    return existing, added


def upsert_position(
    record: PaperPositionRecord,
    store_path: pathlib.Path = DEFAULT_STORE_PATH,
) -> list[PaperPositionRecord]:
    records = load_store(store_path)
    found = False
    for i, r in enumerate(records):
        if r.plan_id == record.plan_id:
            records[i] = record
            found = True
            break
    if not found:
        records.append(record)
    _write_store(records, store_path)
    return records


def dedupe_by_plan_id(store_path: pathlib.Path = DEFAULT_STORE_PATH) -> int:
    records = load_store(store_path)
    seen: set[str] = set()
    deduped: list[PaperPositionRecord] = []
    removed = 0
    for r in records:
        if r.plan_id not in seen:
            seen.add(r.plan_id)
            deduped.append(r)
        else:
            removed += 1
    if removed > 0:
        _write_store(deduped, store_path)
    return removed


def mark_updated(
    plan_id: str,
    status: str,
    store_path: pathlib.Path = DEFAULT_STORE_PATH,
) -> PaperPositionRecord | None:
    records = load_store(store_path)
    now = utc_now_iso()
    for i, r in enumerate(records):
        if r.plan_id == plan_id:
            updated = PaperPositionRecord(
                record_id=r.record_id, paper_position_id=r.paper_position_id,
                plan_id=r.plan_id, symbol=r.symbol, timeframe=r.timeframe,
                status=status, entry_price=r.entry_price, stop_loss=r.stop_loss,
                take_profit_1=r.take_profit_1, take_profit_2=r.take_profit_2,
                take_profit_3=r.take_profit_3, created_at=r.created_at,
                updated_at=now, source_signal_id=r.source_signal_id,
                dry_run_only=True,
            )
            records[i] = updated
            _write_store(records, store_path)
            return updated
    return None
