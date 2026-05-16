import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scripts.generate_repo_hygiene_git_add_dry_run_plan_v1 import generate_git_add_plan


def tracking(track, hold):
    return {
        "recommended_track_files": track,
        "recommended_hold_files": hold,
    }


def test_safe_plan():
    tr = tracking(
        ["scripts/generate_t500_v1.py", "tests/unit/test_t500.py"],
        ["logs/output.log", "data.csv"],
    )
    r = generate_git_add_plan(tr)
    assert r["ok"] is True
    assert r["verdict"] == "PASS"
    assert r["dry_run_only"] is True
    assert "scripts/generate_t500_v1.py" in r["safe_files"]
    assert "tests/unit/test_t500.py" in r["safe_files"]
    assert len(r["git_add_commands"]) > 0
    assert "--dry-run" in r["git_add_commands"][0]


def test_blocked_csv():
    tr = tracking(
        ["scripts/generate_t500_v1.py", "data.csv"],
        [],
    )
    r = generate_git_add_plan(tr)
    assert r["ok"] is False
    assert r["verdict"] == "FAIL"
    assert "data.csv" in r["blocked_files"]


def test_blocked_secret():
    tr = tracking(
        ["scripts/generate_t500_v1.py", ".env", "certs/key.pem"],
        [],
    )
    r = generate_git_add_plan(tr)
    assert r["ok"] is False
    assert r["verdict"] == "FAIL"
    assert ".env" in r["blocked_files"]
    assert "certs/key.pem" in r["blocked_files"]


def test_empty_partial():
    tr = tracking([], ["logs/output.log"])
    r = generate_git_add_plan(tr)
    assert r["ok"] is False
    assert r["verdict"] == "PARTIAL"


def test_dry_run_only():
    tr = tracking(["scripts/generate_t500_v1.py"], [])
    r = generate_git_add_plan(tr)
    assert r["dry_run_only"] is True
    assert "--dry-run" in str(r["git_add_commands"])
