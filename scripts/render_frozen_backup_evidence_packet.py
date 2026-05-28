#!/usr/bin/env python3
"""Render frozen backup evidence packet.

Complete human-review packet. No actual backup/archive/delete operations.

Usage:
    PYTHONPATH=. python3 scripts/render_frozen_backup_evidence_packet.py \
        --backup-evidence-checklist-dir /tmp/frozen_backup_evidence_checklist \
        --manual-approval-forms-dir /tmp/frozen_manual_approval_forms \
        --approval-validation-dir /tmp/frozen_approval_validation \
        --backup-manifest-dir /tmp/frozen_backup_manifest \
        --archive-simulation-dir /tmp/frozen_archive_simulation \
        --output-dir /tmp/frozen_backup_evidence_packet \
        --strict \
        --release-hold HOLD
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys

from core.frozen_backup_evidence_packet import (
    RELEASE_HOLD_REQUIRED,
    build_packet,
    write_html,
    write_json,
    write_manifest,
    write_markdown,
)


def _load_json(path: pathlib.Path) -> dict | list:
    return json.loads(path.read_text(encoding="utf-8"))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Render frozen backup evidence packet")
    parser.add_argument("--backup-evidence-checklist-dir", required=True)
    parser.add_argument("--manual-approval-forms-dir", required=True)
    parser.add_argument("--approval-validation-dir", required=True)
    parser.add_argument("--backup-manifest-dir", required=True)
    parser.add_argument("--archive-simulation-dir", required=True)
    parser.add_argument("--output-dir", default="/tmp/frozen_backup_evidence_packet")
    parser.add_argument("--release-hold", default=RELEASE_HOLD_REQUIRED)
    parser.add_argument("--strict", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    if args.strict and args.release_hold != RELEASE_HOLD_REQUIRED:
        print(f"FAIL: release_hold={args.release_hold!r} != {RELEASE_HOLD_REQUIRED!r}", file=sys.stderr)
        return 1

    checklist_path = pathlib.Path(args.backup_evidence_checklist_dir) / "backup_evidence_checklist.json"
    forms_path = pathlib.Path(args.manual_approval_forms_dir) / "manual_approval_forms.json"
    validation_path = pathlib.Path(args.approval_validation_dir) / "approval_validation.json"
    manifest_path = pathlib.Path(args.backup_manifest_dir) / "backup_manifest.json"
    sim_path = pathlib.Path(args.archive_simulation_dir) / "archive_simulation.json"

    for p in [checklist_path, forms_path, validation_path, manifest_path, sim_path]:
        if not p.exists():
            print(f"FAIL: {p} not found.", file=sys.stderr)
            return 1

    checklist_data = _load_json(checklist_path)
    forms_data = _load_json(forms_path)
    validation_data = _load_json(validation_path)
    manifest_data = _load_json(manifest_path)
    sim_data = _load_json(sim_path)

    # Normalize to lists
    checklist_items = checklist_data if isinstance(checklist_data, list) else checklist_data.get("items", [])
    forms_items = forms_data if isinstance(forms_data, list) else forms_data.get("items", [])
    manifest_items = manifest_data if isinstance(manifest_data, list) else manifest_data.get("items", [])
    sim_items = sim_data if isinstance(sim_data, list) else sim_data.get("items", [])

    packet = build_packet(
        checklist_items=checklist_items,
        approval_forms=forms_items,
        validation_report=validation_data,
        backup_manifest=manifest_items,
        archive_simulation=sim_items,
        release_hold=args.release_hold,
    )

    out_dir = pathlib.Path(args.output_dir)
    write_json(packet, out_dir / "backup_evidence_packet.json")
    write_manifest(packet, out_dir / "backup_evidence_packet_manifest.json")
    write_markdown(packet, out_dir / "backup_evidence_packet.md")
    write_html(packet, out_dir / "backup_evidence_packet.html")

    print(f"OK: evidence packet rendered with {packet.metadata['total_sections']} sections")
    print(f"    manifest release_hold={args.release_hold}")
    print(f"    output: {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
