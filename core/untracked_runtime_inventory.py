"""T23001 — Untracked Runtime Inventory and Risk Classification.

Pure deterministic. No I/O. No network.
Inventories all untracked files and classifies them by risk level.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

RELEASE_HOLD_REQUIRED = "HOLD"

VALID_RISK_CATEGORIES: tuple[str, ...] = (
    "SAFE_RESEARCH",
    "SAFE_IMPORTER",
    "SAFE_REPORT",
    "SHADOW_PIPELINE",
    "ALERT_PIPELINE",
    "TESTNET_DRY_RUN_ONLY",
    "HIGH_RISK_TESTNET_SUBMIT",
    "HIGH_RISK_LIVE_RUNTIME",
    "HIGH_RISK_FLATTEN",
    "HIGH_RISK_SECRET_OR_WEBHOOK",
    "ARCHIVE_CANDIDATE",
    "NEEDS_HUMAN_REVIEW",
)

HIGH_RISK_CATEGORIES: tuple[str, ...] = (
    "HIGH_RISK_TESTNET_SUBMIT",
    "HIGH_RISK_LIVE_RUNTIME",
    "HIGH_RISK_FLATTEN",
    "HIGH_RISK_SECRET_OR_WEBHOOK",
)

DANGER_KEYWORDS: tuple[str, ...] = (
    "live", "submit", "testnet_order", "flatten",
    "replay_submit", "approved_candidates", "exchange",
    "broker", "api_key", "secret", "webhook",
)


@dataclass(frozen=True)
class UntrackedFileRecord:
    """Single untracked file inventory record."""
    record_id: str
    path: str
    risk_category: str
    risk_reason: str
    has_network_calls: bool
    has_api_keys: bool
    has_order_submit: bool
    has_exchange_adapter: bool
    integration_recommendation: str
    is_high_risk: bool
    no_touch_required: bool

    def to_dict(self) -> dict:
        return {
            "record_id": self.record_id,
            "path": self.path,
            "risk_category": self.risk_category,
            "risk_reason": self.risk_reason,
            "has_network_calls": self.has_network_calls,
            "has_api_keys": self.has_api_keys,
            "has_order_submit": self.has_order_submit,
            "has_exchange_adapter": self.has_exchange_adapter,
            "integration_recommendation": self.integration_recommendation,
            "is_high_risk": self.is_high_risk,
            "no_touch_required": self.no_touch_required,
        }


def _safe_id(path: str) -> str:
    return path.replace("/", "__").replace("\\", "__").replace(".", "_")


def _integration_rec(category: str) -> str:
    """Generate integration recommendation based on category."""
    recs = {
        "SAFE_RESEARCH": "Integrate into strategy registry as research artifact",
        "SAFE_IMPORTER": "Integrate into alert center as data source adapter",
        "SAFE_REPORT": "Integrate into operator console as report generator",
        "SHADOW_PIPELINE": "Connect to shadow pipeline registry and operator console",
        "ALERT_PIPELINE": "Connect to unified alert center",
        "TESTNET_DRY_RUN_ONLY": "Wrap in dry-run adapter for testnet simulation framework",
        "HIGH_RISK_TESTNET_SUBMIT": "ISOLATE: Add to denylist, require human approval before any execution",
        "HIGH_RISK_LIVE_RUNTIME": "ISOLATE: Add to denylist, require human approval before any execution",
        "HIGH_RISK_FLATTEN": "ISOLATE: Add to denylist, require human approval before any execution",
        "HIGH_RISK_SECRET_OR_WEBHOOK": "ISOLATE: Scan for secrets, quarantine, require human review",
        "ARCHIVE_CANDIDATE": "Simulate archive, require human decision",
        "NEEDS_HUMAN_REVIEW": "Queue for human review before any integration",
    }
    return recs.get(category, "Requires human review")


def build_file_record(
    path: str,
    risk_category: str,
    risk_reason: str,
    has_network: bool = False,
    has_keys: bool = False,
    has_submit: bool = False,
    has_adapter: bool = False,
) -> UntrackedFileRecord:
    """Build an inventory record for a single file."""
    safe_id = _safe_id(path)
    is_high = risk_category in HIGH_RISK_CATEGORIES
    return UntrackedFileRecord(
        record_id=f"inv_{safe_id}",
        path=path,
        risk_category=risk_category,
        risk_reason=risk_reason,
        has_network_calls=has_network,
        has_api_keys=has_keys,
        has_order_submit=has_submit,
        has_exchange_adapter=has_adapter,
        integration_recommendation=_integration_rec(risk_category),
        is_high_risk=is_high,
        no_touch_required=is_high,
    )


# Complete inventory of all untracked files
UNTRACKED_FILE_INVENTORY: list[dict] = [
    # core/
    {"path": "core/live_runner.py", "cat": "NEEDS_HUMAN_REVIEW", "reason": "Orchestration gateway: delegates to execution_engine, has run_testnet_order_smoke with order params; safe only if engine is noop", "net": False, "keys": False, "submit": True, "adapter": False},
    # docs
    {"path": "docs/octopusycc_mouse_trade_plan_2026-05-23_2026-05-30.md", "cat": "SAFE_RESEARCH", "reason": "Pure research notes on public X posts, no executable code, explicitly forbids live orders", "net": False, "keys": False, "submit": False, "adapter": False},
    # SAFE_RESEARCH
    {"path": "scripts/analyze_aleabitoreddit_watchlist.py", "cat": "SAFE_RESEARCH", "reason": "Offline scanner, reads local exports only, never places orders", "net": False, "keys": False, "submit": False, "adapter": False},
    {"path": "scripts/run_right_breakout_scan_dry.py", "cat": "SAFE_RESEARCH", "reason": "Mock connector, RuntimeError on submit, NoopExchange, pure dry signal scan", "net": False, "keys": False, "submit": False, "adapter": False},
    {"path": "scripts/run_shadow_observation_experiments.py", "cat": "SAFE_RESEARCH", "reason": "Pure local kline cache computation, no network, no submit", "net": False, "keys": False, "submit": False, "adapter": False},
    {"path": "scripts/run_next_shadow_experiment_plan.py", "cat": "SAFE_RESEARCH", "reason": "Offline signal scoring from cached klines, SHADOW_ONLY, NO_SUBMIT", "net": False, "keys": False, "submit": False, "adapter": False},
    # SAFE_IMPORTER
    {"path": "scripts/import_x_local_content.py", "cat": "SAFE_IMPORTER", "reason": "Local file/clipboard import, no API, no network, subprocess only for pbpaste", "net": False, "keys": False, "submit": False, "adapter": False},
    {"path": "scripts/update_aleabitoreddit_market_data.py", "cat": "SAFE_IMPORTER", "reason": "Fetches public OHLCV via yfinance, no API keys, no trading", "net": True, "keys": False, "submit": False, "adapter": False},
    # SAFE_REPORT
    {"path": "scripts/verify_risk_release_flow.py", "cat": "SAFE_REPORT", "reason": "Read-only verification, force-locks dry_run=True, outputs manual commands only", "net": False, "keys": False, "submit": False, "adapter": False},
    # SHADOW_PIPELINE
    {"path": "scripts/run_daily_shadow_scan_pipeline.py", "cat": "SHADOW_PIPELINE", "reason": "Shadow pipeline orchestrator, all steps shadow/observation, no submit", "net": False, "keys": False, "submit": False, "adapter": False},
    {"path": "scripts/run_shadow_sample_collection_pipeline.py", "cat": "SHADOW_PIPELINE", "reason": "Shadow sample collection orchestrator, kline backfill forced dry_run=True", "net": False, "keys": False, "submit": False, "adapter": False},
    {"path": "scripts/run_shadow_universe_collector.py", "cat": "SHADOW_PIPELINE", "reason": "Shadow universe collector, NO_TESTNET_SUBMIT, cached klines only", "net": False, "keys": False, "submit": False, "adapter": False},
    {"path": "scripts/run_right_breakout_param_observation.py", "cat": "SHADOW_PIPELINE", "reason": "Public market data + signal eval, enable_live_trading=False, dormant submit path", "net": True, "keys": False, "submit": False, "adapter": False},
    # TESTNET_DRY_RUN_ONLY
    {"path": "scripts/replay_shadow_order_plans_as_testnet_dry.py", "cat": "TESTNET_DRY_RUN_ONLY", "reason": "Public exchange info call, submit path explicitly stubbed out, writes dry-run payloads", "net": True, "keys": False, "submit": False, "adapter": False},
    {"path": "scripts/verify_testnet_repair_scenarios.py", "cat": "TESTNET_DRY_RUN_ONLY", "reason": "Read-only testnet diagnostic, force-locks dry_run=True, produces repair plans", "net": True, "keys": True, "submit": False, "adapter": True},
    # HIGH_RISK_TESTNET_SUBMIT
    {"path": "scripts/run_controlled_testnet_shift.py", "cat": "HIGH_RISK_TESTNET_SUBMIT", "reason": "Generates submit_approved_candidates.py commands, calls testnet API, orchestrates full pipeline", "net": True, "keys": False, "submit": True, "adapter": False},
    {"path": "scripts/run_observation_shift_runtime.py", "cat": "HIGH_RISK_TESTNET_SUBMIT", "reason": "Queries live testnet state via API, argparse self-labels HIGH_RISK", "net": True, "keys": True, "submit": False, "adapter": True},
    {"path": "scripts/run_replay_submit_batch.py", "cat": "HIGH_RISK_TESTNET_SUBMIT", "reason": "Submits orders to testnet via submit_replayed_testnet_payloads", "net": True, "keys": False, "submit": True, "adapter": True},
    {"path": "scripts/run_signal_testnet_trial.py", "cat": "HIGH_RISK_TESTNET_SUBMIT", "reason": "Creates real Binance testnet connector, --submit-testnet flag enables order submit", "net": True, "keys": True, "submit": True, "adapter": True},
    {"path": "scripts/run_spot_testnet_acceptance.py", "cat": "HIGH_RISK_TESTNET_SUBMIT", "reason": "Full testnet acceptance: submit order, query status, cancel order", "net": True, "keys": True, "submit": True, "adapter": True},
    {"path": "scripts/run_testnet_order_smoke.py", "cat": "HIGH_RISK_TESTNET_SUBMIT", "reason": "Testnet smoke test with real order submit, accepts --mode live", "net": True, "keys": True, "submit": True, "adapter": True},
    {"path": "scripts/submit_approved_candidates.py", "cat": "HIGH_RISK_TESTNET_SUBMIT", "reason": "Main approved-candidate-to-order bridge, delegates to run_replay_submit_batch", "net": True, "keys": False, "submit": True, "adapter": True},
    {"path": "scripts/submit_replayed_testnet_payload.py", "cat": "HIGH_RISK_TESTNET_SUBMIT", "reason": "Core order submission engine, submits entry+SL+TP to Binance testnet", "net": True, "keys": True, "submit": True, "adapter": True},
    # HIGH_RISK_LIVE_RUNTIME
    {"path": "scripts/live_playbook.py", "cat": "HIGH_RISK_LIVE_RUNTIME", "reason": "Accepts --mode live, imports ExecutionEngine+OrderManager, enable_live_trading=True", "net": False, "keys": False, "submit": True, "adapter": True},
    # HIGH_RISK_FLATTEN
    {"path": "scripts/safe_flatten_testnet_symbol.py", "cat": "HIGH_RISK_FLATTEN", "reason": "Submits MARKET reduce-only orders + cancels algo orders on testnet, reads API keys", "net": True, "keys": True, "submit": True, "adapter": True},
    # NEEDS_HUMAN_REVIEW
    {"path": "scripts/run_remediation_shadow_only_loop.py", "cat": "NEEDS_HUMAN_REVIEW", "reason": "Executes arbitrary shell commands via subprocess.run(shell=True), command injection surface", "net": False, "keys": False, "submit": False, "adapter": False},
    # SAFE_RESEARCH (tests)
    {"path": "tests/unit/test_analyze_aleabitoreddit_watchlist.py", "cat": "SAFE_RESEARCH", "reason": "Pure unit tests for watchlist analysis, no network, no trading", "net": False, "keys": False, "submit": False, "adapter": False},
    {"path": "tests/unit/test_import_x_local_content.py", "cat": "SAFE_RESEARCH", "reason": "Unit tests for local content import, subprocess only for local CLI", "net": False, "keys": False, "submit": False, "adapter": False},
    {"path": "tests/unit/test_update_aleabitoreddit_market_data.py", "cat": "SAFE_RESEARCH", "reason": "Unit tests for market data updater with mock fetcher", "net": False, "keys": False, "submit": False, "adapter": False},
]


def build_inventory(
    release_hold: str = RELEASE_HOLD_REQUIRED,
) -> list[UntrackedFileRecord]:
    """Build full inventory from known untracked files."""
    if release_hold != RELEASE_HOLD_REQUIRED:
        raise ValueError(f"release_hold={release_hold!r} != HOLD")
    records: list[UntrackedFileRecord] = []
    for item in UNTRACKED_FILE_INVENTORY:
        records.append(build_file_record(
            path=item["path"],
            risk_category=item["cat"],
            risk_reason=item["reason"],
            has_network=item["net"],
            has_keys=item["keys"],
            has_submit=item["submit"],
            has_adapter=item["adapter"],
        ))
    return records


def compute_inventory_hash(records: list[UntrackedFileRecord]) -> str:
    raw = json.dumps([r.to_dict() for r in records], sort_keys=True, indent=2)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def render_inventory_markdown(records: list[UntrackedFileRecord]) -> str:
    lines = [
        "# Untracked Runtime Inventory",
        "",
        f"**Total files:** {len(records)}",
        f"**High-risk files:** {sum(1 for r in records if r.is_high_risk)}",
        "",
        "## Risk Category Summary",
        "",
    ]
    cat_counts: dict[str, int] = {}
    for r in records:
        cat_counts[r.risk_category] = cat_counts.get(r.risk_category, 0) + 1
    for cat, count in sorted(cat_counts.items()):
        lines.append(f"- **{cat}:** {count}")

    lines.append("")
    lines.append("## Inventory Details")
    lines.append("")

    for r in records:
        marker = "🔴" if r.is_high_risk else "🟡" if r.risk_category in ("NEEDS_HUMAN_REVIEW",) else "🟢"
        lines.append(f"### {marker} {r.path}")
        lines.append("")
        lines.append(f"- **Risk category:** {r.risk_category}")
        lines.append(f"- **Reason:** {r.risk_reason}")
        lines.append(f"- **Network calls:** {r.has_network_calls}")
        lines.append(f"- **API keys:** {r.has_api_keys}")
        lines.append(f"- **Order submit:** {r.has_order_submit}")
        lines.append(f"- **Exchange adapter:** {r.has_exchange_adapter}")
        lines.append(f"- **Recommendation:** {r.integration_recommendation}")
        lines.append("")

    return "\n".join(lines)


def render_risk_matrix_markdown(records: list[UntrackedFileRecord]) -> str:
    lines = [
        "# Untracked Runtime Risk Matrix",
        "",
        "| File | Category | Network | API Keys | Submit | Adapter | High Risk |",
        "|------|----------|---------|----------|--------|---------|-----------|",
    ]
    for r in records:
        lines.append(
            f"| {r.path} | {r.risk_category} | {r.has_network_calls} | {r.has_api_keys} "
            f"| {r.has_order_submit} | {r.has_exchange_adapter} | {r.is_high_risk} |"
        )
    lines.append("")
    return "\n".join(lines)


def render_human_review_queue_markdown(records: list[UntrackedFileRecord]) -> str:
    review = [r for r in records if r.risk_category == "NEEDS_HUMAN_REVIEW"]
    lines = [
        "# Untracked Runtime Human Review Queue",
        "",
        f"**Files requiring human review:** {len(review)}",
        "",
    ]
    for r in review:
        lines.append(f"### {r.path}")
        lines.append(f"- **Reason:** {r.risk_reason}")
        lines.append(f"- **Recommendation:** {r.integration_recommendation}")
        lines.append("")
    return "\n".join(lines)


def render_archive_candidates_markdown(records: list[UntrackedFileRecord]) -> str:
    archive = [r for r in records if r.risk_category == "ARCHIVE_CANDIDATE"]
    lines = [
        "# Untracked Runtime Archive Candidates",
        "",
        f"**Archive candidates:** {len(archive)}",
        "",
    ]
    if archive:
        for r in archive:
            lines.append(f"- **{r.path}:** {r.risk_reason}")
    else:
        lines.append("- No archive candidates identified.")
    lines.append("")
    return "\n".join(lines)


def write_json(records: list[UntrackedFileRecord], out_path) -> None:
    import pathlib
    p = pathlib.Path(out_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps([r.to_dict() for r in records], indent=2), encoding="utf-8")


def write_manifest(records: list[UntrackedFileRecord], out_path, release_hold: str) -> None:
    import pathlib
    p = pathlib.Path(out_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    cat_counts: dict[str, int] = {}
    for r in records:
        cat_counts[r.risk_category] = cat_counts.get(r.risk_category, 0) + 1
    manifest = {
        "total_files": len(records),
        "high_risk_count": sum(1 for r in records if r.is_high_risk),
        "category_counts": dict(sorted(cat_counts.items())),
        "release_hold": release_hold,
        "inventory_hash": compute_inventory_hash(records),
    }
    p.write_text(json.dumps(manifest, indent=2), encoding="utf-8")


def write_markdown(content: str, out_path) -> None:
    import pathlib
    p = pathlib.Path(out_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
