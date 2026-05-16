import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scripts.generate_repo_untracked_artifact_inventory_report_v1 import generate_inventory_report


def test_normal_inventory():
    status = """?? scripts/generate_new_v1.py
?? tests/unit/test_t576_new_feature.py
?? core/new_module.py
?? docs/notes.md
?? logs/output.log
?? data.csv
?? temp.tmp
?? unknown.xyz
"""
    r = generate_inventory_report(status)
    assert r["ok"] is True
    assert r["verdict"] == "PASS"
    assert "scripts/generate_new_v1.py" in r["categories"]["scripts"]
    assert "tests/unit/test_t576_new_feature.py" in r["categories"]["tests"]
    assert "core/new_module.py" in r["categories"]["core"]
    assert "docs/notes.md" in r["categories"]["docs"]
    assert "logs/output.log" in r["categories"]["logs_reports"]
    assert "data.csv" in r["categories"]["csv_data"]
    assert "temp.tmp" in r["categories"]["temp_misc"]
    assert "unknown.xyz" in r["categories"]["unknown"]


def test_secret_risk_fail():
    status = """?? scripts/generate_new_v1.py
?? .env
?? certs/key.pem
"""
    r = generate_inventory_report(status)
    assert r["ok"] is False
    assert r["verdict"] == "FAIL"
    assert len(r["likely_config_or_secret_risk"]) >= 2
    assert "SECRET_RISK_FILES_DETECTED" in r["blockers"]


def test_csv_classification():
    status = """?? data/candidates.csv
?? reports/observations.txt
"""
    r = generate_inventory_report(status)
    assert "data/candidates.csv" in r["categories"]["csv_data"]
    assert "reports/observations.txt" in r["categories"]["logs_reports"]


def test_scripts_tests_classification():
    status = """?? scripts/generate_t571_v1.py
?? scripts/verify_t572_v1.py
?? scripts/aggregate_t573_v1.py
?? scripts/classify_t574_v1.py
?? scripts/compare_t575_v1.py
?? scripts/parse_t576_v1.py
?? scripts/simulate_t577_v1.py
?? tests/unit/test_t571.py
?? tests/unit/test_t572.py
"""
    r = generate_inventory_report(status)
    assert len(r["categories"]["scripts"]) == 7
    assert len(r["categories"]["tests"]) == 2
    assert len(r["important_new_code_files"]) == 9


def test_empty_status():
    r = generate_inventory_report("")
    assert r["ok"] is True
    assert r["verdict"] == "PASS"
    assert r["total_untracked"] == 0
