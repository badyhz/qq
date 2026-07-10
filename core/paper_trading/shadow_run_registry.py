"""Shadow run registry — records each lifecycle run for sample collection tracking.

No orders, no accounts, no secrets. Pure metadata logging.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from core.paper_trading.paper_position import (
    load_canonical_positions, filter_canonical_closed_clean,
    load_canonical_closed_clean_positions,
)
from core.paper_trading.paper_performance_metrics import _determine_sample_status


REGISTRY_FILENAME = "shadow_run_registry.jsonl"

GATE_BLOCKED_INSUFFICIENT = "BLOCKED_INSUFFICIENT_CLOSED_SAMPLE"
GATE_BLOCKED_LOW = "BLOCKED_LOW_SAMPLE_SIZE"
GATE_READY_FOR_REVIEW = "PAPER_SAMPLE_READY_FOR_HUMAN_REVIEW"
GATE_BLOCKED_ACCOUNTING_ERROR = "BLOCKED_ACCOUNTING_ERROR"


@dataclass(frozen=True)
class ShadowRunRecord:
    """Record of a single shadow lifecycle run."""
    run_id: str
    date: str
    started_at: str
    finished_at: str
    mode: str
    allow_public_http: bool
    pipeline_status: str
    steps_passed: int
    steps_failed: int

    strategy_candidates_count: int
    trade_intents_count: int
    shadow_ready_count: int

    paper_position_count: int
    new_positions_count: int
    existing_positions_count: int
    positions_updated_count: int
    positions_skipped_no_future_bars: int
    positions_skipped_newly_opened: int

    clean_positions: int
    excluded_positions: int
    open_clean_positions: int
    closed_clean_positions: int
    clean_take_profit_hit: int
    clean_stop_loss_hit: int
    clean_timeout_exit: int

    cumulative_closed_clean: int
    accounting_status: str
    accounting_error: str | None

    sample_status: str
    strategy_scorecard_rows: int

    testnet_gate_status: str
    testnet_gate_reasons: list[str]

    safety_flags: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "date": self.date,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "mode": self.mode,
            "allow_public_http": self.allow_public_http,
            "pipeline_status": self.pipeline_status,
            "steps_passed": self.steps_passed,
            "steps_failed": self.steps_failed,
            "strategy_candidates_count": self.strategy_candidates_count,
            "trade_intents_count": self.trade_intents_count,
            "shadow_ready_count": self.shadow_ready_count,
            "paper_position_count": self.paper_position_count,
            "new_positions_count": self.new_positions_count,
            "existing_positions_count": self.existing_positions_count,
            "positions_updated_count": self.positions_updated_count,
            "positions_skipped_no_future_bars": self.positions_skipped_no_future_bars,
            "positions_skipped_newly_opened": self.positions_skipped_newly_opened,
            "clean_positions": self.clean_positions,
            "excluded_positions": self.excluded_positions,
            "open_clean_positions": self.open_clean_positions,
            "closed_clean_positions": self.closed_clean_positions,
            "clean_take_profit_hit": self.clean_take_profit_hit,
            "clean_stop_loss_hit": self.clean_stop_loss_hit,
            "clean_timeout_exit": self.clean_timeout_exit,
            "cumulative_closed_clean": self.cumulative_closed_clean,
            "accounting_status": self.accounting_status,
            "accounting_error": self.accounting_error,
            "sample_status": self.sample_status,
            "strategy_scorecard_rows": self.strategy_scorecard_rows,
            "testnet_gate_status": self.testnet_gate_status,
            "testnet_gate_reasons": list(self.testnet_gate_reasons),
            "safety_flags": list(self.safety_flags),
        }


@dataclass(frozen=True)
class ShadowSampleGateResult:
    """Result of the sample collection gate check."""
    date: str
    total_runs: int
    latest_run_id: str
    closed_clean_positions: int
    cumulative_closed_clean: int
    sample_status: str
    testnet_gate_status: str
    testnet_gate_reasons: list[str]
    registry_path: str
    safety_flags: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "date": self.date,
            "total_runs": self.total_runs,
            "latest_run_id": self.latest_run_id,
            "closed_clean_positions": self.closed_clean_positions,
            "cumulative_closed_clean": self.cumulative_closed_clean,
            "sample_status": self.sample_status,
            "testnet_gate_status": self.testnet_gate_status,
            "testnet_gate_reasons": list(self.testnet_gate_reasons),
            "registry_path": self.registry_path,
            "safety_flags": list(self.safety_flags),
        }


GATE_SAFETY_FLAGS = [
    "PAPER_ONLY",
    "SHADOW_ONLY",
    "NO_ORDER",
    "NO_REAL_ORDER",
    "NO_ACCOUNT",
    "NO_SECRET",
    "NO_TESTNET",
    "NO_LIVE",
    "READONLY_METADATA_ONLY",
    "SAMPLE_GATE_READONLY",
]


def generate_run_id() -> str:
    return datetime.utcnow().strftime("%Y%m%dT%H%M%SZ") + "_shadow_lifecycle"


def build_run_record(
    pipeline_result: dict,
    run_id: str | None = None,
    output_dir: str | None = None,
) -> ShadowRunRecord:
    """Build a registry record from lifecycle pipeline result.

    If output_dir is provided, computes cumulative_closed_clean from
    all ledger files using the unified entry point. Otherwise falls back to summary value.
    """
    summary = pipeline_result.get("summary", {})
    steps = pipeline_result.get("steps", [])
    started = steps[0]["started_at"] if steps else pipeline_result.get("date", "")
    finished = steps[-1]["finished_at"] if steps else ""

    steps_passed = sum(1 for s in steps if s.get("status") == "PASS")
    steps_failed = sum(1 for s in steps if s.get("status") == "FAIL")

    closed = summary.get("closed_clean_positions", 0)

    # Compute cumulative closed clean from canonical ledger using unified entry point
    cumulative_closed = closed  # fallback for when output_dir not provided
    accounting_status = "OK"
    accounting_error = None
    fatal_errors = []
    if output_dir:
        try:
            eligible_positions, all_positions, diag = load_canonical_closed_clean_positions(output_dir)
            cumulative_closed = len(eligible_positions)
            fatal_errors = diag.get("fatal_errors", [])
            if fatal_errors:
                accounting_status = "ERROR"
                accounting_error = str(fatal_errors[:3])
        except Exception as e:
            accounting_status = "ERROR"
            accounting_error = str(e)
            fatal_errors = [str(e)]

    # If accounting error, block the gate
    if fatal_errors:
        sample_status = "ACCOUNTING_ERROR"
        gate_status = GATE_BLOCKED_ACCOUNTING_ERROR
        gate_reasons = fatal_errors
    else:
        sample_status = _determine_sample_status(cumulative_closed)
        gate_status, gate_reasons = evaluate_gate(cumulative_closed, sample_status)

    return ShadowRunRecord(
        run_id=run_id or generate_run_id(),
        date=pipeline_result.get("date", ""),
        started_at=started,
        finished_at=finished,
        mode=pipeline_result.get("mode", ""),
        allow_public_http=pipeline_result.get("allow_public_http", False),
        pipeline_status=pipeline_result.get("pipeline_status", "UNKNOWN"),
        steps_passed=steps_passed,
        steps_failed=steps_failed,
        strategy_candidates_count=summary.get("strategy_candidates_count", 0),
        trade_intents_count=summary.get("trade_intents_count", 0),
        shadow_ready_count=summary.get("shadow_ready_count", 0),
        paper_position_count=summary.get("paper_position_count", 0),
        new_positions_count=summary.get("new_positions_count", 0),
        existing_positions_count=summary.get("existing_positions_count", 0),
        positions_updated_count=summary.get("positions_updated_count", 0),
        positions_skipped_no_future_bars=summary.get("positions_skipped_no_future_bars", 0),
        positions_skipped_newly_opened=summary.get("positions_skipped_newly_opened", 0),
        clean_positions=summary.get("clean_count", 0),
        excluded_positions=summary.get("quarantined_count", 0),
        open_clean_positions=summary.get("open_count", 0),
        closed_clean_positions=closed,
        clean_take_profit_hit=summary.get("tp_count", 0),
        clean_stop_loss_hit=summary.get("sl_count", 0),
        clean_timeout_exit=summary.get("timeout_count", 0),
        cumulative_closed_clean=cumulative_closed,
        accounting_status=accounting_status,
        accounting_error=accounting_error,
        sample_status=sample_status,
        strategy_scorecard_rows=summary.get("strategy_scorecard_rows", 0),
        testnet_gate_status=gate_status,
        testnet_gate_reasons=gate_reasons,
        safety_flags=list(pipeline_result.get("safety_flags", [])),
    )


def evaluate_gate(
    closed_clean_positions: int,
    sample_status: str,
) -> tuple[str, list[str]]:
    """Evaluate sample collection gate status."""
    reasons = []

    if closed_clean_positions < 10:
        reasons.append(f"closed_clean_positions={closed_clean_positions} < 10")
        return GATE_BLOCKED_INSUFFICIENT, reasons

    if sample_status == "LOW_SAMPLE_SIZE":
        reasons.append(f"sample_status=LOW_SAMPLE_SIZE, need >= 10 closed trades")
        return GATE_BLOCKED_LOW, reasons

    if sample_status == "EVALUABLE" and closed_clean_positions >= 30:
        reasons.append(f"closed_clean_positions={closed_clean_positions} >= 30, sample EVALUABLE")
        return GATE_READY_FOR_REVIEW, reasons

    # EVALUABLE but < 30
    reasons.append(f"closed_clean_positions={closed_clean_positions} < 30, need more sample")
    return GATE_BLOCKED_LOW, reasons


def append_registry_record(
    record: ShadowRunRecord,
    registry_dir: str,
) -> str:
    """Append a record to the registry JSONL file. Returns path."""
    path = os.path.join(registry_dir, REGISTRY_FILENAME)
    with open(path, "a") as f:
        f.write(json.dumps(record.to_dict()) + "\n")
    return path


def read_registry(registry_dir: str) -> list[dict[str, Any]]:
    """Read all records from the registry JSONL file."""
    path = os.path.join(registry_dir, REGISTRY_FILENAME)
    if not os.path.isfile(path):
        return []
    records = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def compute_sample_gate(registry_dir: str) -> ShadowSampleGateResult:
    """Compute sample gate status from registry history and canonical ledger.

    Uses unified entry point. Blocks on fatal errors only (not business exclusions).
    """
    records = read_registry(registry_dir)
    today = datetime.utcnow().strftime("%Y-%m-%d")

    # Use unified entry point for consistent eligibility
    try:
        eligible_positions, all_positions, diag = load_canonical_closed_clean_positions(registry_dir)
        cumulative_closed = len(eligible_positions)
        fatal_errors = diag.get("fatal_errors", [])
    except Exception as e:
        # Canonical load failed — block the gate
        return ShadowSampleGateResult(
            date=today,
            total_runs=len(records),
            latest_run_id=records[-1].get("run_id", "") if records else "",
            closed_clean_positions=0,
            cumulative_closed_clean=0,
            sample_status="ACCOUNTING_ERROR",
            testnet_gate_status=GATE_BLOCKED_ACCOUNTING_ERROR,
            testnet_gate_reasons=[f"canonical load failed: {e}"],
            registry_path=os.path.join(registry_dir, REGISTRY_FILENAME),
            safety_flags=list(GATE_SAFETY_FLAGS),
        )

    # Block on fatal errors only (technical issues, not business exclusions)
    if fatal_errors:
        return ShadowSampleGateResult(
            date=today,
            total_runs=len(records),
            latest_run_id=records[-1].get("run_id", "") if records else "",
            closed_clean_positions=0,
            cumulative_closed_clean=0,
            sample_status="ACCOUNTING_ERROR",
            testnet_gate_status=GATE_BLOCKED_ACCOUNTING_ERROR,
            testnet_gate_reasons=fatal_errors,
            registry_path=os.path.join(registry_dir, REGISTRY_FILENAME),
            safety_flags=list(GATE_SAFETY_FLAGS),
        )

    if not records:
        return ShadowSampleGateResult(
            date=today,
            total_runs=0,
            latest_run_id="",
            closed_clean_positions=cumulative_closed,
            cumulative_closed_clean=cumulative_closed,
            sample_status="UNKNOWN",
            testnet_gate_status=GATE_BLOCKED_INSUFFICIENT,
            testnet_gate_reasons=["no registry records"],
            registry_path=os.path.join(registry_dir, REGISTRY_FILENAME),
            safety_flags=list(GATE_SAFETY_FLAGS),
        )

    latest = records[-1]
    # Use cumulative count instead of last record's single-run count
    closed = cumulative_closed
    sample_status = _determine_sample_status(closed)
    gate_status, gate_reasons = evaluate_gate(closed, sample_status)

    return ShadowSampleGateResult(
        date=today,
        total_runs=len(records),
        latest_run_id=latest.get("run_id", ""),
        closed_clean_positions=closed,
        cumulative_closed_clean=cumulative_closed,
        sample_status=sample_status,
        testnet_gate_status=gate_status,
        testnet_gate_reasons=gate_reasons,
        registry_path=os.path.join(registry_dir, REGISTRY_FILENAME),
        safety_flags=list(GATE_SAFETY_FLAGS),
    )
