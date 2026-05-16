import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scripts.generate_human_copy_paste_dry_run_readiness_packet_v1 import generate_readiness


def phase(v="PASS"):
    return {"verdict": v, "submit_allowed": False}


def preview(v="PASS"):
    return {
        "verdict": v,
        "submit_allowed": False,
        "dry_run_command": "python3 scripts/run_testnet_submit_execution_wrapper_v1.py --env testnet --symbol BTCUSDT --side BUY --quantity 0.01 --dry-run",
    }


def invariant(v="PASS"):
    return {"verdict": v, "submit_allowed": False}


def manifest(v="PASS"):
    return {"verdict": v, "submit_allowed": False}


def test_pass():
    r = generate_readiness(phase("PASS"), preview("PASS"), invariant("PASS"), manifest("PASS"))
    assert r["verdict"] == "PASS"
    assert r["readiness_type"] == "HUMAN_COPY_PASTE_DRY_RUN_ONLY"
    assert r["dry_run_ready"] is True
    assert r["submit_allowed"] is False
    assert r["max_submit_count"] == 1


def test_missing_dry_run_command_fail():
    p = preview("PASS")
    p["dry_run_command"] = ""
    r = generate_readiness(phase("PASS"), p, invariant("PASS"), manifest("PASS"))
    assert r["verdict"] == "FAIL"


def test_invariant_partial_partial():
    r = generate_readiness(phase("PASS"), preview("PASS"), invariant("PARTIAL"), manifest("PASS"))
    assert r["verdict"] == "FAIL"  # Invariant must be PASS for readiness


def test_audit_fail_fail():
    r = generate_readiness(phase("PASS"), preview("PASS"), invariant("PASS"), manifest("FAIL"))
    assert r["verdict"] == "FAIL"


def test_submit_allowed_remains_false():
    r = generate_readiness(phase("PASS"), preview("PASS"), invariant("PASS"), manifest("PASS"))
    assert r["submit_allowed"] is False
