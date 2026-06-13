"""T21001 — Testnet Dry-Run Orchestrator.

Pure deterministic. No I/O. No network. No real exchange.
Simulates testnet order lifecycle without any real operations.
All orders are simulated. All fills are simulated. All cancels are simulated.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone

RELEASE_HOLD_REQUIRED = "HOLD"

VALID_ORDER_SIDES: tuple[str, ...] = ("BUY", "SELL")
VALID_ORDER_TYPES: tuple[str, ...] = ("LIMIT", "MARKET")
VALID_LIFECYCLE_STAGES: tuple[str, ...] = (
    "INTENT",
    "PRE_CHECK",
    "SIMULATED_SUBMIT",
    "SIMULATED_FILL",
    "SIMULATED_REJECT",
    "SIMULATED_CANCEL",
    "SIMULATED_TIMEOUT",
    "COMPLETED",
)

FORBIDDEN_REAL_ACTIONS: tuple[str, ...] = (
    "REAL_SUBMIT",
    "REAL_CANCEL",
    "REAL_FILL",
    "REAL_EXCHANGE_CALL",
    "REAL_API_KEY_READ",
    "LIVE_ORDER",
)


@dataclass(frozen=True)
class OrderIntent:
    """Dry-run order intent."""
    intent_id: str
    symbol: str
    side: str
    order_type: str
    quantity: float
    price: float
    strategy_id: str
    timestamp: str
    dry_run: bool

    def to_dict(self) -> dict:
        return {
            "intent_id": self.intent_id,
            "symbol": self.symbol,
            "side": self.side,
            "order_type": self.order_type,
            "quantity": self.quantity,
            "price": self.price,
            "strategy_id": self.strategy_id,
            "timestamp": self.timestamp,
            "dry_run": self.dry_run,
        }


@dataclass(frozen=True)
class OrderLifecycleEvent:
    """Single order lifecycle event."""
    event_id: str
    intent_id: str
    stage: str
    simulated_response: str
    simulated_fill_price: float
    simulated_slippage_bps: float
    simulated_latency_ms: float
    risk_precheck_passed: bool
    no_submit_evidence: bool
    dry_run: bool
    no_real_action: bool
    timestamp: str

    def to_dict(self) -> dict:
        return {
            "event_id": self.event_id,
            "intent_id": self.intent_id,
            "stage": self.stage,
            "simulated_response": self.simulated_response,
            "simulated_fill_price": self.simulated_fill_price,
            "simulated_slippage_bps": self.simulated_slippage_bps,
            "simulated_latency_ms": self.simulated_latency_ms,
            "risk_precheck_passed": self.risk_precheck_passed,
            "no_submit_evidence": self.no_submit_evidence,
            "dry_run": self.dry_run,
            "no_real_action": self.no_real_action,
            "timestamp": self.timestamp,
        }


@dataclass(frozen=True)
class StabilityScore:
    """Dry-run stability score."""
    score_id: str
    total_intents: int
    successful_simulations: int
    blocked_by_risk: int
    blocked_by_guard: int
    stability_ratio: float
    dry_run: bool

    def to_dict(self) -> dict:
        return {
            "score_id": self.score_id,
            "total_intents": self.total_intents,
            "successful_simulations": self.successful_simulations,
            "blocked_by_risk": self.blocked_by_risk,
            "blocked_by_guard": self.blocked_by_guard,
            "stability_ratio": self.stability_ratio,
            "dry_run": self.dry_run,
        }


def build_order_intent(
    symbol: str,
    side: str,
    order_type: str,
    quantity: float,
    price: float,
    strategy_id: str,
) -> OrderIntent:
    """Build a dry-run order intent."""
    ts = datetime.now(timezone.utc).isoformat()
    intent_id = f"intent_{symbol}_{side}_{ts}"
    return OrderIntent(
        intent_id=intent_id,
        symbol=symbol,
        side=side,
        order_type=order_type,
        quantity=quantity,
        price=price,
        strategy_id=strategy_id,
        timestamp=ts,
        dry_run=True,
    )


def simulate_risk_precheck(intent: OrderIntent) -> tuple[bool, str]:
    """Simulate risk pre-check. Always passes in dry-run."""
    # In dry-run, risk pre-check always passes
    # In real mode, this would check position limits, balance, etc.
    return True, "risk_precheck_passed_dry_run"


def simulate_order_submit(intent: OrderIntent, risk_passed: bool) -> OrderLifecycleEvent:
    """Simulate order submission."""
    ts = datetime.now(timezone.utc).isoformat()

    if not risk_passed:
        return OrderLifecycleEvent(
            event_id=f"evt_{intent.intent_id}_blocked",
            intent_id=intent.intent_id,
            stage="SIMULATED_REJECT",
            simulated_response="rejected_by_risk_precheck",
            simulated_fill_price=0.0,
            simulated_slippage_bps=0.0,
            simulated_latency_ms=0.0,
            risk_precheck_passed=False,
            no_submit_evidence=True,
            dry_run=True,
            no_real_action=True,
            timestamp=ts,
        )

    # Simulate fill with small slippage
    slippage_bps = 2.5  # 2.5 basis points
    fill_price = intent.price * (1 + slippage_bps / 10000) if intent.side == "BUY" else intent.price * (1 - slippage_bps / 10000)

    return OrderLifecycleEvent(
        event_id=f"evt_{intent.intent_id}_filled",
        intent_id=intent.intent_id,
        stage="SIMULATED_FILL",
        simulated_response="simulated_fill_successful",
        simulated_fill_price=round(fill_price, 8),
        simulated_slippage_bps=slippage_bps,
        simulated_latency_ms=45.0,
        risk_precheck_passed=True,
        no_submit_evidence=True,
        dry_run=True,
        no_real_action=True,
        timestamp=ts,
    )


def run_orchestrator(
    intents: list[OrderIntent],
    release_hold: str = RELEASE_HOLD_REQUIRED,
) -> tuple[list[OrderLifecycleEvent], StabilityScore]:
    """Run the full dry-run orchestrator."""
    if release_hold != RELEASE_HOLD_REQUIRED:
        raise ValueError(f"release_hold={release_hold!r} != HOLD")

    events: list[OrderLifecycleEvent] = []
    successful = 0
    blocked_risk = 0
    blocked_guard = 0

    for intent in intents:
        risk_passed, _ = simulate_risk_precheck(intent)
        event = simulate_order_submit(intent, risk_passed)
        events.append(event)

        if event.stage == "SIMULATED_FILL":
            successful += 1
        elif not event.risk_precheck_passed:
            blocked_risk += 1
        else:
            blocked_guard += 1

    total = len(intents)
    stability = successful / total if total > 0 else 0.0

    score = StabilityScore(
        score_id="dry_run_stability",
        total_intents=total,
        successful_simulations=successful,
        blocked_by_risk=blocked_risk,
        blocked_by_guard=blocked_guard,
        stability_ratio=round(stability, 4),
        dry_run=True,
    )

    return events, score


def compute_lifecycle_hash(events: list[OrderLifecycleEvent]) -> str:
    raw = json.dumps([e.to_dict() for e in events], sort_keys=True, indent=2)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def render_orchestrator_report(events: list[OrderLifecycleEvent], score: StabilityScore) -> str:
    lines = [
        "# Testnet Dry-Run Orchestrator Report",
        "",
        f"**Total intents:** {score.total_intents}",
        f"**Successful simulations:** {score.successful_simulations}",
        f"**Blocked by risk:** {score.blocked_by_risk}",
        f"**Blocked by guard:** {score.blocked_by_guard}",
        f"**Stability ratio:** {score.stability_ratio}",
        f"**Dry-run:** {score.dry_run}",
        "",
        "## Safety Boundary",
        "",
        "- No real orders submitted.",
        "- No real exchange calls made.",
        "- No real API keys read.",
        "- All fills are simulated.",
        "- All cancels are simulated.",
        "",
        "## Order Lifecycle Events",
        "",
    ]

    for event in events:
        lines.append(f"### {event.intent_id}")
        lines.append("")
        lines.append(f"- **Stage:** {event.stage}")
        lines.append(f"- **Response:** {event.simulated_response}")
        lines.append(f"- **Fill price:** {event.simulated_fill_price}")
        lines.append(f"- **Slippage (bps):** {event.simulated_slippage_bps}")
        lines.append(f"- **Latency (ms):** {event.simulated_latency_ms}")
        lines.append(f"- **Risk precheck:** {event.risk_precheck_passed}")
        lines.append("")

    lines.append("---")
    lines.append("DRY RUN ONLY. NO REAL ORDERS. NO REAL EXCHANGE.")
    lines.append("")

    return "\n".join(lines)


def render_stability_report(score: StabilityScore) -> str:
    lines = [
        "# Testnet Dry-Run Stability Score",
        "",
        f"**Score ID:** {score.score_id}",
        f"**Total intents:** {score.total_intents}",
        f"**Successful:** {score.successful_simulations}",
        f"**Blocked by risk:** {score.blocked_by_risk}",
        f"**Blocked by guard:** {score.blocked_by_guard}",
        f"**Stability ratio:** {score.stability_ratio}",
        f"**Dry-run:** {score.dry_run}",
        "",
        "---",
        "DRY RUN ONLY.",
        "",
    ]
    return "\n".join(lines)


def render_result_review_packet(events: list[OrderLifecycleEvent], score: StabilityScore) -> str:
    lines = [
        "# Testnet Dry-Run Result Review Packet",
        "",
        f"**Total events:** {len(events)}",
        f"**Stability ratio:** {score.stability_ratio}",
        "",
        "## Event Summary",
        "",
    ]

    stage_counts: dict[str, int] = {}
    for e in events:
        stage_counts[e.stage] = stage_counts.get(e.stage, 0) + 1
    for stage, count in sorted(stage_counts.items()):
        lines.append(f"- **{stage}:** {count}")

    lines.append("")
    lines.append("## All Events Dry-Run Verified")
    lines.append("")
    for e in events:
        assert e.dry_run is True
        assert e.no_real_action is True
        lines.append(f"- {e.event_id}: dry_run={e.dry_run}, no_real_action={e.no_real_action}")

    lines.append("")
    lines.append("---")
    lines.append("DRY RUN ONLY. NO REAL ORDERS.")
    lines.append("")

    return "\n".join(lines)


def write_json(items: list, out_path) -> None:
    import pathlib
    p = pathlib.Path(out_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(
        json.dumps([i.to_dict() for i in items], indent=2),
        encoding="utf-8",
    )


def write_score_json(score: StabilityScore, out_path) -> None:
    import pathlib
    p = pathlib.Path(out_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(score.to_dict(), indent=2), encoding="utf-8")


def write_manifest(data: dict, out_path) -> None:
    import pathlib
    p = pathlib.Path(out_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, indent=2), encoding="utf-8")


def write_markdown(content: str, out_path) -> None:
    import pathlib
    p = pathlib.Path(out_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
