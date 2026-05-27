from __future__ import annotations

from pathlib import Path

import pytest

INVENTORY = Path("docs/dev_prd/dirty_workspace_high_risk_freeze_inventory.md")

NINE_HIGH_RISK_PATHS = [
    "core/live_runner.py",
    "scripts/live_playbook.py",
    "scripts/submit_approved_candidates.py",
    "scripts/run_testnet_order_smoke.py",
    "scripts/run_signal_testnet_trial.py",
    "scripts/run_spot_testnet_acceptance.py",
    "scripts/safe_flatten_testnet_symbol.py",
    "scripts/replay_shadow_order_plans_as_testnet_dry.py",
    "scripts/submit_replayed_testnet_payload.py",
]


def _read_inventory() -> str:
    return INVENTORY.read_text(encoding="utf-8")


def test_inventory_doc_exists() -> None:
    assert INVENTORY.exists(), f"Missing: {INVENTORY}"


@pytest.mark.parametrize("path", NINE_HIGH_RISK_PATHS)
def test_each_high_risk_path_present(path: str) -> None:
    text = _read_inventory()
    assert path in text, f"Path not found in inventory: {path}"


def test_inventory_has_exactly_nine_entries() -> None:
    text = _read_inventory()
    found = [p for p in NINE_HIGH_RISK_PATHS if p in text]
    assert len(found) == 9, f"Expected 9 paths, found {len(found)}: {found}"


def test_inventory_risk_level_high() -> None:
    text = _read_inventory()
    assert text.count("risk level: **HIGH**") >= 9
