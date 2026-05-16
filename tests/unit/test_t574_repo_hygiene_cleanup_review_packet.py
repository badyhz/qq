import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scripts.generate_repo_hygiene_cleanup_review_packet_v1 import generate_cleanup_packet


def inventory_with(paths):
    categories = {}
    for p in paths:
        if p.endswith(".csv"):
            categories.setdefault("csv_data", []).append(p)
        elif p.endswith(".log") or p.endswith(".txt"):
            categories.setdefault("logs_reports", []).append(p)
        else:
            categories.setdefault("unknown", []).append(p)
    return {"categories": categories}


def test_safe_review():
    inv = inventory_with([
        "logs/output.log",
        "data.csv",
        "temp.tmp",
    ])
    r = generate_cleanup_packet(inv)
    assert r["ok"] is True
    assert r["verdict"] == "PASS"
    assert r["cleanup_mode"] == "REVIEW_ONLY"
    assert r["delete_allowed"] is False
    assert r["archive_allowed"] is False


def test_deletion_blocked():
    inv = inventory_with(["scripts/generate_t500_v1.py"])
    r = generate_cleanup_packet(inv)
    assert r["delete_allowed"] is False
    assert "core/" in r["never_delete_without_manual_review"]
    assert "scripts/" in r["never_delete_without_manual_review"]
    assert "tests/" in r["never_delete_without_manual_review"]


def test_secret_manual_review():
    inv = inventory_with(["certs/key.pem", ".env"])
    r = generate_cleanup_packet(inv)
    any_secrets_in_never = any(
        kw in str(r["never_delete_without_manual_review"]).lower()
        for kw in ["pem", "key", "secret", "env"]
    )
    assert any_secrets_in_never


def test_temp_grouping():
    inv = inventory_with([
        "data1.csv",
        "data2.csv",
        "logs/a.log",
        "logs/b.log",
        "temp.tmp",
        "another.tmp",
    ])
    r = generate_cleanup_packet(inv)
    assert len(r["suggested_archive_groups"]["csv_data"]) >= 2
    assert len(r["suggested_archive_groups"]["logs_reports"]) >= 2


def test_readonly():
    inv = inventory_with(["data.csv"])
    r = generate_cleanup_packet(inv)
    assert r["delete_allowed"] is False
    assert r["archive_allowed"] is False
    assert r["cleanup_mode"] == "REVIEW_ONLY"
