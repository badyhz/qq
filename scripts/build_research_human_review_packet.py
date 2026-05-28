#!/usr/bin/env python3
"""Build research human review packet — full offline review workflow.

Usage:
    python3 scripts/build_research_human_review_packet.py \
        --quality-dir /tmp/multi_strategy_research_quality_gate \
        --artifact-browser-dir /tmp/research_artifact_browser \
        --comparison-dir /tmp/research_comparison_analytics \
        --output-dir /tmp/research_human_review_packet \
        --strict \
        --release-hold HOLD

Safety: offline only. No network. No exchange. No runtime. No planner.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.research_review_packet import (
    build_review_packet,
    compute_source_hashes,
    validate_review_packet_safety,
)
from core.research_review_checklist import (
    build_review_checklist,
    render_checklist_markdown,
)
from core.research_review_signoff import (
    build_signoff_template,
    render_signoff_markdown,
)
from core.research_review_blocker_ledger import (
    build_blocker_ledger,
    render_blocker_ledger_markdown,
)
from core.research_review_audit_trail import (
    build_audit_trail,
    render_audit_trail_markdown,
)
from core.research_review_report import (
    render_review_html,
    render_review_markdown,
)
from core.research_review_manifest import (
    build_review_manifest,
    validate_review_manifest_safety,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Build research human review packet")
    parser.add_argument("--quality-dir", required=True, help="Quality gate output directory")
    parser.add_argument("--artifact-browser-dir", required=True, help="Artifact browser output directory")
    parser.add_argument("--comparison-dir", required=True, help="Comparison analytics output directory")
    parser.add_argument("--output-dir", required=True, help="Output directory for review packet")
    parser.add_argument("--strict", action="store_true", help="Strict mode")
    parser.add_argument("--release-hold", default="HOLD", help="Expected release_hold value")
    args = parser.parse_args()

    if args.release_hold != "HOLD":
        print(f"FAIL: release_hold must be HOLD, got {args.release_hold}", file=sys.stderr)
        return 2

    quality_dir = Path(args.quality_dir)
    browser_dir = Path(args.artifact_browser_dir)
    comparison_dir = Path(args.comparison_dir)
    output_dir = Path(args.output_dir)

    # Validate source dirs exist
    missing_dirs = []
    if not quality_dir.exists():
        missing_dirs.append(str(quality_dir))
    if not browser_dir.exists():
        missing_dirs.append(str(browser_dir))
    if not comparison_dir.exists():
        missing_dirs.append(str(comparison_dir))

    if missing_dirs:
        print(f"FAIL: missing source directories: {missing_dirs}", file=sys.stderr)
        return 2

    # Check for corrupted JSON in required artifacts
    corrupted = []
    for d, label in [(quality_dir, "quality"), (browser_dir, "browser"), (comparison_dir, "comparison")]:
        for f in d.glob("*.json"):
            try:
                json.loads(f.read_text())
            except (json.JSONDecodeError, ValueError):
                corrupted.append(f"{label}/{f.name}")

    if corrupted:
        print(f"FAIL: corrupted JSON files: {corrupted}", file=sys.stderr)
        return 2

    output_dir.mkdir(parents=True, exist_ok=True)

    # Compute source hashes
    source_dirs = {
        "quality_gate": quality_dir,
        "artifact_browser": browser_dir,
        "comparison_analytics": comparison_dir,
    }
    source_hashes = compute_source_hashes(source_dirs)

    # Build review packet
    packet = build_review_packet(
        quality_dir=quality_dir,
        browser_dir=browser_dir,
        comparison_dir=comparison_dir,
        source_hashes=source_hashes,
        strict_mode=args.strict,
    )

    # Validate packet safety
    valid, safety_errors = validate_review_packet_safety(packet)
    if not valid:
        print(f"FAIL: packet safety errors: {safety_errors}", file=sys.stderr)
        return 2

    # Build checklist
    checklist = build_review_checklist()

    # Build signoff template
    signoff_template = build_signoff_template(packet_id=packet.get("packet_id", ""))

    # Build blocker ledger
    blocker_ledger = build_blocker_ledger(packet.get("blockers", []))

    # Build audit trail
    output_names = (
        "review_packet.json",
        "review_checklist.json",
        "review_checklist.md",
        "review_signoff_template.json",
        "review_signoff_template.md",
        "blocker_resolution_ledger.json",
        "blocker_resolution_ledger.md",
        "review_audit_trail.json",
        "review_audit_trail.md",
        "human_review_report.md",
        "human_review_report.html",
        "review_manifest.json",
    )

    audit_trail = build_audit_trail(
        input_artifact_hashes=source_hashes,
        output_artifact_hashes={},
        command_args=[
            "--quality-dir", str(quality_dir),
            "--artifact-browser-dir", str(browser_dir),
            "--comparison-dir", str(comparison_dir),
            "--output-dir", str(output_dir),
            "--strict" if args.strict else "--no-strict",
            "--release-hold", args.release_hold,
        ],
    )

    # Build manifest
    manifest = build_review_manifest(
        source_hashes=source_hashes,
        output_hashes={},
        strict_mode=args.strict,
    )

    # Write all artifacts
    _write_json(output_dir, "review_packet.json", packet)
    _write_json(output_dir, "review_checklist.json", checklist)
    (output_dir / "review_checklist.md").write_text(render_checklist_markdown(checklist))
    _write_json(output_dir, "review_signoff_template.json", signoff_template)
    (output_dir / "review_signoff_template.md").write_text(render_signoff_markdown(signoff_template))
    _write_json(output_dir, "blocker_resolution_ledger.json", blocker_ledger)
    (output_dir / "blocker_resolution_ledger.md").write_text(render_blocker_ledger_markdown(blocker_ledger))
    _write_json(output_dir, "review_audit_trail.json", audit_trail)
    (output_dir / "review_audit_trail.md").write_text(render_audit_trail_markdown(audit_trail))

    # Render reports
    md_report = render_review_markdown(packet, checklist, signoff_template, blocker_ledger, audit_trail)
    (output_dir / "human_review_report.md").write_text(md_report)

    html_report = render_review_html(packet, checklist, signoff_template, blocker_ledger, audit_trail)
    (output_dir / "human_review_report.html").write_text(html_report)

    # Now compute output hashes after all files written
    output_hashes = {}
    for name in output_names:
        p = output_dir / name
        if p.exists():
            import hashlib
            output_hashes[name] = hashlib.sha256(p.read_bytes()).hexdigest()

    # Rebuild manifest and audit trail with actual output hashes
    manifest = build_review_manifest(
        source_hashes=source_hashes,
        output_hashes=output_hashes,
        strict_mode=args.strict,
    )
    _write_json(output_dir, "review_manifest.json", manifest)

    # Validate manifest safety
    valid, manifest_errors = validate_review_manifest_safety(manifest)
    if not valid:
        print(f"FAIL: manifest safety errors: {manifest_errors}", file=sys.stderr)
        return 2

    # Summary
    blockers = packet.get("blockers", [])
    critical = sum(1 for b in blockers if b.get("severity") == "CRITICAL")
    warnings = sum(1 for b in blockers if b.get("severity") == "WARNING")

    if critical:
        overall = "FAIL"
    elif warnings:
        overall = "PARTIAL"
    else:
        overall = "PASS"

    print(f"{overall}: blockers={len(blockers)} critical={critical} warnings={warnings} "
          f"recommended={packet.get('recommended_decision', 'UNKNOWN')}")

    return 0 if overall == "PASS" else (1 if overall == "FAIL" else 0)


def _write_json(output_dir: Path, name: str, data: dict) -> None:
    """Write JSON artifact."""
    (output_dir / name).write_text(json.dumps(data, sort_keys=True, indent=2))


if __name__ == "__main__":
    sys.exit(main())
