"""Phase 10J Shadow Sample Gate runner.

Reads shadow run registry, evaluates sample collection gate status.
No orders, no accounts, no secrets, no testnet, no live.
"""
from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core.paper_trading.shadow_run_registry import (
    compute_sample_gate, read_registry, ShadowSampleGateResult,
    GATE_BLOCKED_INSUFFICIENT, GATE_BLOCKED_LOW, GATE_READY_FOR_REVIEW,
    validate_report_date,
)

REPO_ROOT = os.path.join(os.path.dirname(__file__), "..")
REPORT_DIR = os.path.join(REPO_ROOT, "reports", "strategies")


def _validate_scorecard_date(report_dir: str, report_date: str) -> dict:
    """Require Gate's scorecard input to match the authoritative report date."""
    path = os.path.join(report_dir, f"{report_date}_paper_performance_scorecard.json")
    try:
        with open(path) as f:
            scorecard = json.load(f)
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"scorecard for report_date={report_date} is unavailable: {exc}") from exc
    scorecard_date = validate_report_date(scorecard.get("date"))
    if scorecard_date != report_date:
        raise ValueError(
            "report_date conflict: "
            f"requested={report_date}, scorecard={scorecard_date}"
        )
    return scorecard


def _net_friction_gate(scorecard: dict) -> dict:
    """Return additive fail-closed Net evidence; never promote testnet/live."""
    net = scorecard.get("net_friction")
    blockers: list[str] = []
    if not isinstance(net, dict) or net.get("model_configuration_status") != "CONFIGURED":
        blockers.append("NET_FRICTION_MODEL_UNCONFIGURED")
        net = net if isinstance(net, dict) else {}
    activation = net.get("p1_03_activation") or {}
    configured_hash = net.get("friction_assumptions_hash")
    activated_hash = activation.get("net_friction_assumptions_hash")
    if configured_hash and activated_hash and configured_hash != activated_hash:
        blockers.append("NET_FRICTION_ASSUMPTIONS_MISMATCH")
    trusted = net.get("trusted_metrics") or {}
    integrity = net.get("integrity") or {}
    if integrity.get("symbol_mapping_invalid_count", 0) > 0:
        blockers.append("NET_FRICTION_SYMBOL_MAPPING_INVALID")
    if integrity.get("notional_boundary_exceeded_count", 0) > 0:
        blockers.append("NET_FRICTION_NOTIONAL_BOUNDARY_EXCEEDED")
    if integrity.get("funding_not_trusted_count", 0) > 0:
        blockers.append("NET_FRICTION_FUNDING_NOT_TRUSTED")
    if integrity.get("gap_evidence_incomplete_count", 0) > 0:
        blockers.append("NET_FRICTION_GAP_EVIDENCE_INCOMPLETE")
    if trusted.get("net_complete_closed_count", 0) == 0:
        blockers.append("NET_FRICTION_SAMPLE_EMPTY")
    if trusted.get("net_metrics_status") == "INCOMPLETE_COVERAGE":
        blockers.append("NET_FRICTION_INCOMPLETE_COVERAGE")
    if trusted.get("outcome_selection_bias") is True:
        blockers.append("NET_FRICTION_OUTCOME_SELECTION_BIAS")
    return {
        "net_friction_gate_status": "BLOCKED" if blockers else "EVIDENCE_AVAILABLE_REVIEW_REQUIRED",
        "net_friction_gate_blockers": blockers,
        "testnet_ready": False,
        "live_ready": False,
        "automatic_promotion": False,
    }


def render_markdown(
    gate: ShadowSampleGateResult,
    registry: list[dict],
    net_gate: dict | None = None,
) -> str:
    lines = [
        "# Shadow Sample Collection Gate",
        "",
        f"**Date:** {gate.date}",
        f"**Total runs:** {gate.total_runs}",
        f"**Latest run:** {gate.latest_run_id}",
        "",
        "## Gate Status",
        "",
        f"- closed_clean_positions: {gate.closed_clean_positions}",
        f"- cumulative_closed_clean: {gate.cumulative_closed_clean}",
        f"- sample_status: {gate.sample_status}",
        f"- testnet_gate_status: {gate.testnet_gate_status}",
        "",
    ]

    if gate.testnet_gate_reasons:
        lines.extend(["## Gate Reasons", ""])
        for r in gate.testnet_gate_reasons:
            lines.append(f"- {r}")
        lines.append("")

    if net_gate is not None:
        lines.extend([
            "## Net Friction Evidence",
            "",
            f"- status: {net_gate.get('net_friction_gate_status')}",
            "- testnet_ready: NO",
            "- live_ready: NO",
        ])
        for blocker in net_gate.get("net_friction_gate_blockers", []):
            lines.append(f"- blocker: {blocker}")
        lines.append("")

    if gate.testnet_gate_status == GATE_BLOCKED_INSUFFICIENT:
        lines.extend([
            "## Conclusion",
            "",
            "样本收集门禁",
            "",
            f"当前 clean closed trades：{gate.closed_clean_positions}",
            f"当前 sample_status：{gate.sample_status}",
            f"当前 testnet gate：{gate.testnet_gate_status}",
            "",
            "结论：",
            "样本不足，继续 shadow 收集。",
            "不允许 testnet/live。",
            "",
        ])
    elif gate.testnet_gate_status == GATE_BLOCKED_LOW:
        lines.extend([
            "## Conclusion",
            "",
            f"样本偏少（closed={gate.closed_clean_positions}），继续 shadow 收集。",
            f"testnet gate：{gate.testnet_gate_status}",
            "",
        ])
    elif gate.testnet_gate_status == GATE_READY_FOR_REVIEW:
        lines.extend([
            "## Conclusion",
            "",
            f"样本已达到人工审查门槛（closed={gate.closed_clean_positions}）。",
            "注意：PAPER_SAMPLE_READY_FOR_HUMAN_REVIEW 不等于 testnet_ready。",
            "需要人工审查后才能决定是否进入 testnet。",
            "",
        ])

    # Run history
    if registry:
        lines.extend(["## Run History", ""])
        lines.append("| # | run_id | date | mode | status | clean | closed | gate |")
        lines.append("|---|--------|------|------|--------|-------|--------|------|")
        for i, rec in enumerate(registry[-20:], 1):  # last 20
            lines.append(
                f"| {i} | {rec.get('run_id', '')[:20]} "
                f"| {rec.get('date', '')} | {rec.get('mode', '')} "
                f"| {rec.get('pipeline_status', '')} "
                f"| {rec.get('clean_positions', 0)} "
                f"| {rec.get('closed_clean_positions', 0)} "
                f"| {rec.get('testnet_gate_status', '')[:25]} |"
            )
        lines.append("")

    lines.extend([
        "## Safety",
        "",
        "- Paper-only: YES",
        "- Shadow-only: YES",
        "- No order: YES",
        "- No account: YES",
        "- No testnet/live: YES",
        "- No secret: YES",
        "- Gate is readonly: YES",
        "",
    ])
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Phase 10J shadow sample collection gate",
    )
    parser.add_argument("--date", type=str, default=None)
    parser.add_argument("--registry-dir", type=str, default=REPORT_DIR)
    parser.add_argument("--output-dir", type=str, default=REPORT_DIR)
    args = parser.parse_args()

    registry_dir = args.registry_dir
    output_dir = args.output_dir

    registry = read_registry(registry_dir)
    print(f"Registry records: {len(registry)}")

    try:
        gate = compute_sample_gate(registry_dir, report_date=args.date)
        date_str = gate.date
        scorecard = _validate_scorecard_date(registry_dir, date_str)
    except ValueError as exc:
        print(f"Gate FAILED: {exc}", file=sys.stderr)
        return 1
    gate_dict = gate.to_dict()
    gate_dict.update(_net_friction_gate(scorecard))

    os.makedirs(output_dir, exist_ok=True)

    # JSON
    json_path = os.path.join(output_dir, f"{date_str}_shadow_sample_gate.json")
    with open(json_path, "w") as f:
        json.dump(gate_dict, f, indent=2)
    print(f"Gate JSON: {json_path}")

    # Markdown
    md_path = os.path.join(output_dir, f"{date_str}_shadow_sample_gate.md")
    with open(md_path, "w") as f:
        f.write(render_markdown(gate, registry, gate_dict))
    print(f"Gate Markdown: {md_path}")

    print(f"\n=== Sample Gate ===")
    print(f"Total runs: {gate.total_runs}")
    print(f"Closed clean positions: {gate.closed_clean_positions}")
    print(f"Sample status: {gate.sample_status}")
    print(f"Testnet gate: {gate.testnet_gate_status}")
    for r in gate.testnet_gate_reasons:
        print(f"  Reason: {r}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
