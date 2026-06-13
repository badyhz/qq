#!/usr/bin/env python3
"""T18501 — Run Strategy Registry + Promotion Board.

Generates all Phase 3 reports and data files.
Dry-run only. No real trading.
"""
from __future__ import annotations

import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from core.strategy_registry import (
    build_default_registry,
    compute_registry_hash,
    render_registry_markdown,
    validate_strategy_record,
    write_json as write_registry_json,
    write_manifest as write_registry_manifest,
    write_markdown as write_registry_markdown,
)
from core.strategy_promotion_board import (
    build_promotion_board,
    compute_board_hash,
    render_board_markdown,
    render_blockers_markdown,
    render_next_actions_markdown,
    write_json as write_board_json,
    write_manifest as write_board_manifest,
    write_markdown as write_board_markdown,
)

ROOT = pathlib.Path(__file__).resolve().parents[1]
REPORTS_DIR = ROOT / "reports"
DATA_DIR = ROOT / "data" / "strategy_registry"


def main() -> None:
    release_hold = "HOLD"

    # Step 1: Build registry
    print("[1/5] Building strategy registry...")
    records = build_default_registry()
    write_registry_json(records, DATA_DIR / "strategy_registry.jsonl")
    write_registry_manifest(records, REPORTS_DIR / "strategy_registry_manifest.json", release_hold)
    write_registry_markdown(records, REPORTS_DIR / "strategy_registry_overview.md")
    print(f"  -> {len(records)} strategies registered")

    # Step 2: Validate registry
    print("[2/5] Validating registry...")
    errors_found = 0
    for r in records:
        errs = validate_strategy_record(r.to_dict())
        if errs:
            print(f"  WARNING: {r.strategy_id}: {errs}")
            errors_found += len(errs)
    print(f"  -> Validation: {errors_found} errors")

    # Step 3: Build promotion board
    print("[3/5] Building promotion board...")
    strategies = [r.to_dict() for r in records]
    decisions = build_promotion_board(strategies, release_hold)
    write_board_json(decisions, DATA_DIR / "promotion_decisions.jsonl")
    write_board_manifest(decisions, REPORTS_DIR / "strategy_promotion_board_manifest.json", release_hold)
    write_board_markdown(decisions, REPORTS_DIR / "strategy_promotion_board.md")
    print(f"  -> {len(decisions)} board decisions")

    # Step 4: Blockers report
    print("[4/5] Generating blockers report...")
    blockers_md = render_blockers_markdown(decisions)
    (REPORTS_DIR / "strategy_blockers.md").write_text(blockers_md, encoding="utf-8")
    blocked = [d for d in decisions if d.blockers]
    print(f"  -> {len(blocked)} strategies with blockers")

    # Step 5: Next actions report
    print("[5/5] Generating next actions report...")
    next_md = render_next_actions_markdown(decisions)
    (REPORTS_DIR / "strategy_next_actions.md").write_text(next_md, encoding="utf-8")

    print(f"\nDONE. {len(records)} strategies, {len(decisions)} decisions.")
    print(f"Reports: {REPORTS_DIR}")
    print(f"Data: {DATA_DIR}")


if __name__ == "__main__":
    main()
