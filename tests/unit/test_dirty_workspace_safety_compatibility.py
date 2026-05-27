from __future__ import annotations

from pathlib import Path

INVENTORY = Path("docs/dev_prd/dirty_workspace_high_risk_freeze_inventory.md")


def _read() -> str:
    return INVENTORY.read_text(encoding="utf-8")


def test_inventory_exists() -> None:
    assert INVENTORY.exists()


def test_has_global_freeze_rule() -> None:
    text = _read()
    assert "Global Freeze Rule" in text or "HUMAN_REVIEW_ONLY" in text


def test_has_human_review_checklist() -> None:
    text = _read()
    assert "Human Review Checklist" in text


def test_has_safety_statement() -> None:
    text = _read()
    assert "Safety Statement" in text
    lower = text.lower()
    assert "no runtime integration" in lower or "no live" in lower


def test_forbids_auto_commit() -> None:
    text = _read().lower()
    assert "auto-commit" in text


def test_forbids_auto_wire() -> None:
    text = _read().lower()
    assert "auto-wire" in text


def test_forbids_live_submit() -> None:
    text = _read().lower()
    assert "live-submit" in text or "live_submit" in text
