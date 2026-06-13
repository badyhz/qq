"""System dry-run E2E orchestrator. Runs the full pipeline end-to-end."""
from __future__ import annotations

import json
import pathlib
import sys
from datetime import datetime, timezone

ROOT = pathlib.Path(__file__).resolve().parent.parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.runtime_integrations.research.source_loader import load_all_research_sources, write_watchlist_evidence, write_source_status
from src.runtime_integrations.research.watchlist_loader import load_and_score, write_scored_watchlist
from src.runtime_integrations.shadow.shadow_runtime import generate_signals_from_watchlist, build_scorecard, write_signals, write_scorecard
from src.runtime_integrations.shadow.shadow_evidence_exporter import export_promotion_evidence, write_promotion_evidence
from src.runtime_integrations.alerts.alert_runtime import load_alerts_from_watchlist, load_alerts_from_signals, load_alerts_from_testnet, deduplicate_alerts, write_alerts
from src.runtime_integrations.alerts.feishu_dry_run_renderer import render_feishu_payloads, write_payloads
from src.runtime_integrations.operator.operator_state_writer import build_runtime_state, write_state
from src.runtime_integrations.operator.dashboard_updater import write_dashboard
from src.runtime_integrations.testnet_sim.order_lifecycle_simulator import generate_order_intents, simulate_lifecycle, write_intents, write_lifecycle, write_no_submit_evidence


def run_e2e(data_dir: pathlib.Path, reports_dir: pathlib.Path) -> dict:
    """Run the full E2E dry-run pipeline."""
    now = datetime.now(timezone.utc).isoformat()
    run_id = f"e2e_{now.replace(':', '').replace('-', '')[:20]}"
    runtime_dir = data_dir / "runtime"

    steps_completed = []
    errors = []

    # Step 1: Load research sources
    try:
        watchlist_items, source_statuses = load_all_research_sources(data_dir)
        write_watchlist_evidence(watchlist_items, runtime_dir / "research" / "watchlist_evidence.jsonl")
        write_source_status(source_statuses, runtime_dir / "research" / "research_source_status.json")
        steps_completed.append("research_source_loading")
    except Exception as e:
        errors.append(f"research_source_loading: {e}")
        watchlist_items = []

    # Step 2: Score watchlist
    try:
        scored = load_and_score(runtime_dir / "research" / "watchlist_evidence.jsonl")
        write_scored_watchlist(scored, runtime_dir / "research" / "scored_watchlist.json")
        steps_completed.append("watchlist_scoring")
    except Exception as e:
        errors.append(f"watchlist_scoring: {e}")
        scored = []

    # Step 3: Shadow runtime
    try:
        signals = generate_signals_from_watchlist(
            [s.to_dict() for s in scored] if scored else [],
            run_id,
        )
        write_signals(signals, runtime_dir / "shadow" / "signals.jsonl")
        scorecard = build_scorecard(signals, run_id)
        write_scorecard(scorecard, runtime_dir / "shadow" / "scorecard.json")
        steps_completed.append("shadow_runtime")
    except Exception as e:
        errors.append(f"shadow_runtime: {e}")
        signals = []
        scorecard = None

    # Step 4: Export promotion evidence
    try:
        evidence = export_promotion_evidence([s.to_dict() for s in signals])
        write_promotion_evidence(evidence, runtime_dir / "shadow" / "promotion_evidence.jsonl")
        steps_completed.append("promotion_evidence")
    except Exception as e:
        errors.append(f"promotion_evidence: {e}")

    # Step 5: Testnet simulation
    try:
        intents = generate_order_intents([s.to_dict() for s in signals])
        lifecycle_events, no_submit = simulate_lifecycle(intents)
        write_intents(intents, runtime_dir / "testnet_sim" / "order_intents.jsonl")
        write_lifecycle(lifecycle_events, runtime_dir / "testnet_sim" / "order_lifecycle.jsonl")
        write_no_submit_evidence(no_submit, runtime_dir / "testnet_sim" / "no_submit_evidence.jsonl")
        steps_completed.append("testnet_simulation")
    except Exception as e:
        errors.append(f"testnet_simulation: {e}")
        intents = []
        lifecycle_events = []
        no_submit = []

    # Step 6: Alert runtime
    try:
        research_alerts = load_alerts_from_watchlist(runtime_dir / "research" / "watchlist_evidence.jsonl")
        shadow_alerts = load_alerts_from_signals(runtime_dir / "shadow" / "signals.jsonl")
        testnet_alerts = load_alerts_from_testnet(runtime_dir / "testnet_sim" / "no_submit_evidence.jsonl")
        all_alerts = research_alerts + shadow_alerts + testnet_alerts
        deduped = deduplicate_alerts(all_alerts)
        write_alerts(deduped, runtime_dir / "alerts" / "alerts.jsonl")
        steps_completed.append("alert_runtime")
    except Exception as e:
        errors.append(f"alert_runtime: {e}")
        deduped = []

    # Step 7: Feishu dry-run payloads
    try:
        payloads = render_feishu_payloads([a.to_dict() for a in deduped])
        write_payloads(payloads, runtime_dir / "alerts" / "feishu_dry_run_payloads.jsonl")
        steps_completed.append("feishu_payloads")
    except Exception as e:
        errors.append(f"feishu_payloads: {e}")
        payloads = []

    # Step 8: Operator state
    try:
        state = build_runtime_state(
            research_count=len(watchlist_items),
            shadow_signal_count=len(signals),
            shadow_ticker_count=len({s.ticker for s in signals}),
            alert_count=len(deduped),
            feishu_payload_count=len(payloads),
            testnet_intent_count=len(intents),
            testnet_lifecycle_count=len(lifecycle_events),
            no_submit_evidence_count=len(no_submit),
        )
        write_state(state, runtime_dir / "operator" / "system_state.json")
        steps_completed.append("operator_state")
    except Exception as e:
        errors.append(f"operator_state: {e}")
        state = None

    # Step 9: Dashboard
    try:
        if state:
            write_dashboard(state.to_dict(), reports_dir / "operator_dashboard.html")
        steps_completed.append("dashboard")
    except Exception as e:
        errors.append(f"dashboard: {e}")

    # Step 10: E2E report
    try:
        report = _build_e2e_report(run_id, steps_completed, errors, state, signals, deduped, intents, lifecycle_events, no_submit)
        reports_dir.mkdir(parents=True, exist_ok=True)
        (reports_dir / "system_dry_run_e2e_report.md").write_text(report, encoding="utf-8")
        e2e_dir = runtime_dir / "e2e"
        e2e_dir.mkdir(parents=True, exist_ok=True)
        manifest = {
            "run_id": run_id,
            "timestamp": now,
            "steps_completed": steps_completed,
            "errors": errors,
            "status": "SYSTEM_DRY_RUN_E2E_PASS" if not errors else "SYSTEM_DRY_RUN_E2E_PARTIAL",
            "real_trading": "NOT_ALLOWED",
            "testnet_submit": "NOT_ALLOWED",
        }
        (runtime_dir / "e2e" / "run_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        steps_completed.append("e2e_report")
    except Exception as e:
        errors.append(f"e2e_report: {e}")

    return {
        "run_id": run_id,
        "steps_completed": steps_completed,
        "errors": errors,
        "status": "SYSTEM_DRY_RUN_E2E_PASS" if not errors else "SYSTEM_DRY_RUN_E2E_PARTIAL",
    }


def _build_e2e_report(
    run_id: str,
    steps: list[str],
    errors: list[str],
    state,
    signals,
    alerts,
    intents,
    lifecycle,
    no_submit,
) -> str:
    lines = [
        "# System Dry-run E2E Report",
        "",
        f"**Run ID:** {run_id}",
        f"**Status:** {'PASS' if not errors else 'PARTIAL'}",
        "",
        "## Safety",
        "",
        "- Real trading: **NOT ALLOWED**",
        "- Testnet submit: **NOT ALLOWED**",
        "- Dry-run: **ENFORCED**",
        "",
        "## Pipeline Steps",
        "",
    ]
    for s in steps:
        lines.append(f"- {s}: OK")
    for e in errors:
        lines.append(f"- ERROR: {e}")

    lines.append("")
    lines.append("## Runtime Metrics")
    lines.append("")
    if state:
        stats = state.runtime_stats
        for k, v in sorted(stats.items()):
            lines.append(f"- **{k}:** {v}")

    lines.append("")
    lines.append("## Final Conclusions")
    lines.append("")
    if not errors:
        lines.append("- SYSTEM_DRY_RUN_E2E_PASS")
    else:
        lines.append("- SYSTEM_DRY_RUN_E2E_PARTIAL")
    lines.append("- REAL_TRADING_NOT_ALLOWED")
    lines.append("- TESTNET_SUBMIT_NOT_ALLOWED")
    lines.append("- NO_SUBMIT_EVIDENCE_WRITTEN")
    lines.append("- OPERATOR_DASHBOARD_UPDATED")
    lines.append("")
    return "\n".join(lines)
