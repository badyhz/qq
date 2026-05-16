import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scripts.generate_first_testnet_submit_rollback_recommendation_v1 import generate_recommendation


def incident(level):
    return {"incident_level": level}


def evidence():
    return {"symbol": "BTCUSDT"}


def test_t503_none_no_action():
    r = generate_recommendation(incident("NONE"), evidence())
    assert r["recommendation"] == "NO_ACTION"


def test_t503_high_dry_run_recommendation():
    r = generate_recommendation(incident("HIGH"), evidence())
    assert r["recommendation"] == "GENERATE_SAFE_FLATTEN_DRY_RUN"
    assert any("DRY_TEMPLATE_ONLY" in x for x in r["safe_commands"])


def test_t503_critical_includes_dry_run_template_only():
    r = generate_recommendation(incident("CRITICAL"), evidence())
    assert r["recommendation"] == "MANUAL_CONFIRM_FLATTEN_REQUIRED"
    assert any("DRY_TEMPLATE_ONLY" in x for x in r["safe_commands"])
    assert all("--confirm" not in x for x in r["safe_commands"])


def test_t503_default_never_executable_confirm():
    for level in ["NONE", "LOW", "MEDIUM", "HIGH", "CRITICAL"]:
        r = generate_recommendation(incident(level), evidence())
        assert all("EXECUTE_" not in x for x in r["safe_commands"])


def test_t503_malformed_incident_fails():
    r = generate_recommendation(None, evidence())
    assert r["ok"] is False
    assert r["verdict"] == "FAIL"
