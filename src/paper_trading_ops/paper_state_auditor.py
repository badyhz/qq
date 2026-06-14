"""Paper state auditor — audits paper_positions.jsonl health."""
from __future__ import annotations
import json, pathlib
from collections import Counter
from datetime import datetime, timezone, timedelta
from src.paper_trading_ops.models import PaperStateAudit, new_id, utc_now_iso

VALID_STATUSES = (
    "PLANNED", "PAPER_OPEN", "PAPER_TP1_HIT", "PAPER_TP2_HIT",
    "PAPER_STOPPED", "PAPER_TIME_STOPPED", "PAPER_CLOSED_TP3",
    "PAPER_CLOSED", "PAPER_INVALIDATED",
)
STALE_HOURS = 72


def _parse_time(t: str) -> datetime | None:
    if not t:
        return None
    t = t.strip().replace("T", " ").split("+")[0].split("Z")[0]
    if "." in t:
        t = t.split(".")[0]
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M"):
        try:
            return datetime.strptime(t, fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None


def audit_store(store_path: str | pathlib.Path) -> PaperStateAudit:
    path = pathlib.Path(store_path)
    notes: list[str] = []

    if not path.exists():
        return PaperStateAudit(
            audit_id=new_id("PSA"), created_at=utc_now_iso(),
            store_path=str(path), records_total=0,
            duplicate_plan_ids=0, duplicate_position_ids=0,
            invalid_status_count=0, not_dry_run_count=0,
            stale_open_count=0, stale_planned_count=0,
            missing_price_field_count=0,
            audit_status="PASS", audit_notes=["Store file does not exist — no records to audit"],
            final_verdict=f"PAPER_STATE_AUDITOR_READY|STATUS=PASS|RECORDS=0|REAL_ORDER_SUBMIT_NOT_ALLOWED",
        )

    records: list[dict] = []
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line:
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    except Exception:
        pass

    total = len(records)
    plan_ids = [r.get("plan_id", "") for r in records]
    pos_ids = [r.get("paper_position_id", "") for r in records]

    dup_plan = sum(c - 1 for c in Counter(plan_ids).values() if c > 1)
    dup_pos = sum(c - 1 for c in Counter(pos_ids).values() if c > 1)

    invalid_status = sum(1 for r in records if r.get("status", "") not in VALID_STATUSES)
    not_dry = sum(1 for r in records if not r.get("dry_run_only", True))

    now = datetime.now(timezone.utc)
    stale_cutoff = now - timedelta(hours=STALE_HOURS)
    stale_open = 0
    stale_planned = 0
    missing_price = 0

    for r in records:
        if r.get("entry_price", 0) <= 0 or r.get("stop_loss", 0) <= 0:
            missing_price += 1
        updated = _parse_time(r.get("updated_at", ""))
        if r.get("status") == "PAPER_OPEN" and updated and updated < stale_cutoff:
            stale_open += 1
        if r.get("status") == "PLANNED" and updated and updated < stale_cutoff:
            stale_planned += 1

    if dup_plan > 0:
        notes.append(f"{dup_plan} duplicate plan_ids found")
    if dup_pos > 0:
        notes.append(f"{dup_pos} duplicate position_ids found")
    if invalid_status > 0:
        notes.append(f"{invalid_status} records with invalid status")
    if not_dry > 0:
        notes.append(f"{not_dry} records with dry_run_only=false")
    if stale_open > 0:
        notes.append(f"{stale_open} PAPER_OPEN records stale (>{STALE_HOURS}h)")
    if stale_planned > 0:
        notes.append(f"{stale_planned} PLANNED records stale (>{STALE_HOURS}h)")
    if missing_price > 0:
        notes.append(f"{missing_price} records with missing entry/SL fields")

    issues = dup_plan + dup_pos + invalid_status + not_dry + missing_price
    if issues > 0:
        status = "FAIL"
    elif stale_open > 0 or stale_planned > 0:
        status = "WARNING"
    else:
        status = "PASS"
        if not notes:
            notes.append("All records healthy")

    return PaperStateAudit(
        audit_id=new_id("PSA"), created_at=utc_now_iso(),
        store_path=str(path), records_total=total,
        duplicate_plan_ids=dup_plan, duplicate_position_ids=dup_pos,
        invalid_status_count=invalid_status, not_dry_run_count=not_dry,
        stale_open_count=stale_open, stale_planned_count=stale_planned,
        missing_price_field_count=missing_price,
        audit_status=status, audit_notes=notes,
        final_verdict=f"PAPER_STATE_AUDITOR_READY|STATUS={status}|RECORDS={total}|REAL_ORDER_SUBMIT_NOT_ALLOWED",
    )
