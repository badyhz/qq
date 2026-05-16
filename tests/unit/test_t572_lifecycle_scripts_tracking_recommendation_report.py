import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scripts.generate_lifecycle_scripts_tracking_recommendation_report_v1 import generate_tracking_recommendation


def inventory(paths):
    categories = {}
    for p in paths:
        if p.startswith("scripts/"):
            categories.setdefault("scripts", []).append(p)
        elif p.startswith("tests/"):
            categories.setdefault("tests", []).append(p)
        else:
            categories.setdefault("unknown", []).append(p)
    return {"categories": categories}


def test_all_expected_present():
    inv = inventory([
        "scripts/generate_t491_v1.py",
        "scripts/verify_t492_v1.py",
        "scripts/aggregate_t493_v1.py",
        "scripts/classify_t494_v1.py",
        "scripts/compare_t495_v1.py",
        "scripts/parse_t496_v1.py",
        "scripts/simulate_t497_v1.py",
        "tests/unit/test_t491_feature.py",
    ])
    r = generate_tracking_recommendation(inv)
    assert r["ok"] is True
    assert r["verdict"] == "PASS"
    assert "scripts/generate_t491_v1.py" in r["recommended_track_files"]
    assert "tests/unit/test_t491_feature.py" in r["recommended_track_files"]


def test_temp_ignored():
    inv = inventory([
        "scripts/generate_t500_v1.py",
        "logs/output.log",
        "data.csv",
        "temp_runner.py",
        ".claude/config",
    ])
    r = generate_tracking_recommendation(inv)
    assert r["ok"] is True
    assert "scripts/generate_t500_v1.py" in r["recommended_track_files"]
    assert "logs/output.log" in r["recommended_hold_files"]
    assert "data.csv" in r["recommended_hold_files"]
    assert "temp_runner.py" in r["recommended_hold_files"]
    assert ".claude/config" in r["recommended_hold_files"]


def test_secret_risk_fail():
    inv = inventory([
        "scripts/generate_t500_v1.py",
        ".env",
        "certs/key.pem",
    ])
    r = generate_tracking_recommendation(inv)
    assert r["ok"] is False
    assert r["verdict"] == "FAIL"
    assert any("SECRET_RISK_FILE_CANNOT_BE_TRACKED" in b for b in r["blockers"])
    assert ".env" in r["recommended_hold_files"]


def test_no_git_mutation():
    inv = inventory(["scripts/generate_t500_v1.py"])
    r = generate_tracking_recommendation(inv)
    assert "git add" not in str(r).lower()
    assert "commit" not in str(r).lower()
