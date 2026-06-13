"""Tests for T23001 — Untracked Runtime Inventory and Risk Classification."""
from __future__ import annotations

import json
import hashlib
import pytest

from core.untracked_runtime_inventory import (
    VALID_RISK_CATEGORIES,
    HIGH_RISK_CATEGORIES,
    DANGER_KEYWORDS,
    RELEASE_HOLD_REQUIRED,
    UNTRACKED_FILE_INVENTORY,
    UntrackedFileRecord,
    build_file_record,
    build_inventory,
    compute_inventory_hash,
    render_inventory_markdown,
    render_risk_matrix_markdown,
    render_human_review_queue_markdown,
    render_archive_candidates_markdown,
)


# --- Category coverage ---

def test_valid_risk_categories_count():
    assert len(VALID_RISK_CATEGORIES) == 12


def test_high_risk_categories_count():
    assert len(HIGH_RISK_CATEGORIES) == 4


def test_high_risk_subset_of_valid():
    assert set(HIGH_RISK_CATEGORIES).issubset(set(VALID_RISK_CATEGORIES))


def test_all_inventory_categories_valid():
    for item in UNTRACKED_FILE_INVENTORY:
        assert item["cat"] in VALID_RISK_CATEGORIES, f"{item['path']} has invalid category {item['cat']}"


# --- Inventory completeness ---

def test_inventory_count_matches_untracked_files():
    assert len(UNTRACKED_FILE_INVENTORY) == 29


def test_all_paths_unique():
    paths = [i["path"] for i in UNTRACKED_FILE_INVENTORY]
    assert len(paths) == len(set(paths))


# --- build_file_record ---

def test_build_file_record_basic():
    r = build_file_record("test.py", "SAFE_RESEARCH", "test reason")
    assert r.path == "test.py"
    assert r.risk_category == "SAFE_RESEARCH"
    assert r.risk_reason == "test reason"
    assert r.is_high_risk is False
    assert r.no_touch_required is False


def test_build_file_record_high_risk():
    for cat in HIGH_RISK_CATEGORIES:
        r = build_file_record("x.py", cat, "reason")
        assert r.is_high_risk is True
        assert r.no_touch_required is True


def test_build_file_record_non_high_risk():
    non_high = [c for c in VALID_RISK_CATEGORIES if c not in HIGH_RISK_CATEGORIES]
    for cat in non_high:
        r = build_file_record("x.py", cat, "reason")
        assert r.is_high_risk is False
        assert r.no_touch_required is False


def test_build_file_record_id_safe():
    r = build_file_record("scripts/foo/bar.py", "SAFE_RESEARCH", "r")
    assert r.record_id == "inv_scripts__foo__bar_py"


def test_build_file_record_network_flags():
    r = build_file_record("x.py", "SAFE_RESEARCH", "r", has_network=True, has_keys=True, has_submit=True, has_adapter=True)
    assert r.has_network_calls is True
    assert r.has_api_keys is True
    assert r.has_order_submit is True
    assert r.has_exchange_adapter is True


# --- build_inventory ---

def test_build_inventory_requires_hold():
    with pytest.raises(ValueError, match="HOLD"):
        build_inventory(release_hold="NOT_HOLD")


def test_build_inventory_returns_all():
    records = build_inventory()
    assert len(records) == len(UNTRACKED_FILE_INVENTORY)


def test_build_inventory_record_types():
    records = build_inventory()
    for r in records:
        assert isinstance(r, UntrackedFileRecord)
        assert r.risk_category in VALID_RISK_CATEGORIES


# --- High-risk file classification ---

def test_high_risk_testnet_submit_files():
    records = build_inventory()
    high = [r for r in records if r.risk_category == "HIGH_RISK_TESTNET_SUBMIT"]
    assert len(high) == 8
    for r in high:
        assert r.is_high_risk is True
        assert r.no_touch_required is True


def test_high_risk_live_runtime_files():
    records = build_inventory()
    live = [r for r in records if r.risk_category == "HIGH_RISK_LIVE_RUNTIME"]
    assert len(live) == 1
    assert live[0].path == "scripts/live_playbook.py"


def test_high_risk_flatten_files():
    records = build_inventory()
    flat = [r for r in records if r.risk_category == "HIGH_RISK_FLATTEN"]
    assert len(flat) == 1
    assert flat[0].path == "scripts/safe_flatten_testnet_symbol.py"


def test_needs_human_review_files():
    records = build_inventory()
    review = [r for r in records if r.risk_category == "NEEDS_HUMAN_REVIEW"]
    assert len(review) == 2
    paths = {r.path for r in review}
    assert "core/live_runner.py" in paths
    assert "scripts/run_remediation_shadow_only_loop.py" in paths


# --- Safe file counts ---

def test_safe_research_count():
    records = build_inventory()
    safe = [r for r in records if r.risk_category == "SAFE_RESEARCH"]
    assert len(safe) == 8  # 4 scripts + 3 tests + 1 doc


def test_safe_importer_count():
    records = build_inventory()
    imp = [r for r in records if r.risk_category == "SAFE_IMPORTER"]
    assert len(imp) == 2


def test_safe_report_count():
    records = build_inventory()
    rep = [r for r in records if r.risk_category == "SAFE_REPORT"]
    assert len(rep) == 1


def test_shadow_pipeline_count():
    records = build_inventory()
    sp = [r for r in records if r.risk_category == "SHADOW_PIPELINE"]
    assert len(sp) == 4


def test_testnet_dry_run_only_count():
    records = build_inventory()
    td = [r for r in records if r.risk_category == "TESTNET_DRY_RUN_ONLY"]
    assert len(td) == 2


# --- High-risk flags ---

def test_high_risk_count():
    records = build_inventory()
    high = [r for r in records if r.is_high_risk]
    assert len(high) == 10  # 8 testnet_submit + 1 live + 1 flatten


def test_no_touch_required_matches_high_risk():
    records = build_inventory()
    for r in records:
        assert r.no_touch_required == r.is_high_risk


# --- compute_inventory_hash ---

def test_hash_deterministic():
    records = build_inventory()
    h1 = compute_inventory_hash(records)
    h2 = compute_inventory_hash(records)
    assert h1 == h2


def test_hash_is_sha256():
    records = build_inventory()
    h = compute_inventory_hash(records)
    assert len(h) == 64
    assert all(c in "0123456789abcdef" for c in h)


def test_hash_changes_on_different_input():
    records = build_inventory()
    r1 = build_file_record("different.py", "SAFE_RESEARCH", "x")
    h_orig = compute_inventory_hash(records)
    h_mod = compute_inventory_hash(records + [r1])
    assert h_orig != h_mod


# --- to_dict ---

def test_to_dict_keys():
    r = build_file_record("x.py", "SAFE_RESEARCH", "r")
    d = r.to_dict()
    expected = {
        "record_id", "path", "risk_category", "risk_reason",
        "has_network_calls", "has_api_keys", "has_order_submit",
        "has_exchange_adapter", "integration_recommendation",
        "is_high_risk", "no_touch_required",
    }
    assert set(d.keys()) == expected


def test_to_dict_json_serializable():
    records = build_inventory()
    for r in records:
        json.dumps(r.to_dict())


# --- Markdown renderers ---

def test_render_inventory_markdown_has_header():
    records = build_inventory()
    md = render_inventory_markdown(records)
    assert "# Untracked Runtime Inventory" in md
    assert "Total files:" in md
    assert "High-risk files:" in md


def test_render_inventory_markdown_has_all_files():
    records = build_inventory()
    md = render_inventory_markdown(records)
    for r in records:
        assert r.path in md


def test_render_risk_matrix_markdown_has_table():
    records = build_inventory()
    md = render_risk_matrix_markdown(records)
    assert "| File | Category |" in md
    lines = [l for l in md.split("\n") if l.startswith("|") and not l.startswith("| File") and not l.startswith("|---")]
    assert len(lines) == 29


def test_render_human_review_queue_markdown():
    records = build_inventory()
    md = render_human_review_queue_markdown(records)
    assert "Human Review Queue" in md
    assert "core/live_runner.py" in md
    assert "run_remediation_shadow_only_loop.py" in md


def test_render_archive_candidates_markdown_no_candidates():
    records = build_inventory()
    md = render_archive_candidates_markdown(records)
    assert "No archive candidates" in md


# --- JSONL output parseable ---

def test_json_output_parseable():
    records = build_inventory()
    raw = json.dumps([r.to_dict() for r in records], indent=2)
    parsed = json.loads(raw)
    assert len(parsed) == 29
    for item in parsed:
        assert "risk_category" in item
        assert item["risk_category"] in VALID_RISK_CATEGORIES


# --- Frozen dataclass ---

def test_record_is_frozen():
    r = build_file_record("x.py", "SAFE_RESEARCH", "r")
    with pytest.raises(AttributeError):
        r.path = "y.py"


# --- Integration recommendations ---

def test_all_categories_have_recommendations():
    from core.untracked_runtime_inventory import _integration_rec
    for cat in VALID_RISK_CATEGORIES:
        rec = _integration_rec(cat)
        assert isinstance(rec, str)
        assert len(rec) > 0


def test_high_risk_recommendations_contain_isolate():
    from core.untracked_runtime_inventory import _integration_rec
    for cat in HIGH_RISK_CATEGORIES:
        rec = _integration_rec(cat)
        assert "ISOLATE" in rec or "denylist" in rec
