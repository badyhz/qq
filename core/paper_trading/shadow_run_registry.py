"""Shadow run registry — records each lifecycle run for sample collection tracking.

No orders, no accounts, no secrets. Pure metadata logging.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


REGISTRY_FILENAME = "shadow_run_registry.jsonl"

GATE_BLOCKED_INSUFFICIENT = "BLOCKED_INSUFFICIENT_CLOSED_SAMPLE"
GATE_BLOCKED_LOW = "BLOCKED_LOW_SAMPLE_SIZE"
GATE_READY_FOR_REVIEW = "PAPER_SAMPLE_READY_FOR_HUMAN_REVIEW"


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
) -> ShadowRunRecord:
    """Build a registry record from lifecycle pipeline result."""
    summary = pipeline_result.get("summary", {})
    steps = pipeline_result.get("steps", [])
    started = steps[0]["started_at"] if steps else pipeline_result.get("date", "")
    finished = steps[-1]["finished_at"] if steps else ""

    steps_passed = sum(1 for s in steps if s.get("status") == "PASS")
    steps_failed = sum(1 for s in steps if s.get("status") == "FAIL")

    closed = summary.get("closed_clean_positions", 0)
    sample_status = summary.get("sample_status", "UNKNOWN")
    gate_status, gate_reasons = evaluate_gate(closed, sample_status)

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
    """Compute sample gate status from registry history."""
    records = read_registry(registry_dir)
    today = datetime.utcnow().strftime("%Y-%m-%d")

    if not records:
        return ShadowSampleGateResult(
            date=today,
            total_runs=0,
            latest_run_id="",
            closed_clean_positions=0,
            sample_status="UNKNOWN",
            testnet_gate_status=GATE_BLOCKED_INSUFFICIENT,
            testnet_gate_reasons=["no registry records"],
            registry_path=os.path.join(registry_dir, REGISTRY_FILENAME),
            safety_flags=list(GATE_SAFETY_FLAGS),
        )

    latest = records[-1]
    closed = latest.get("closed_clean_positions", 0)
    sample_status = latest.get("sample_status", "UNKNOWN")
    gate_status, gate_reasons = evaluate_gate(closed, sample_status)

    return ShadowSampleGateResult(
        date=today,
        total_runs=len(records),
        latest_run_id=latest.get("run_id", ""),
        closed_clean_positions=closed,
        sample_status=sample_status,
        testnet_gate_status=gate_status,
        testnet_gate_reasons=gate_reasons,
        registry_path=os.path.join(registry_dir, REGISTRY_FILENAME),
        safety_flags=list(GATE_SAFETY_FLAGS),
    )
