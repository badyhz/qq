import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scripts.verify_human_copy_paste_dry_run_command_v1 import verify_command


EXPECTED = "python3 scripts/run_testnet_submit_execution_wrapper_v1.py --env testnet --symbol BTCUSDT --side BUY --quantity 0.01 --dry-run"


def readiness():
    return {"verdict": "PASS", "dry_run_command": EXPECTED, "submit_allowed": False}


def test_exact_dry_run_pass():
    r = verify_command(readiness(), EXPECTED)
    assert r["verdict"] == "PASS"
    assert r["command_provided"] is True
    assert r["command_matches_expected"] is True
    assert r["command_safety_status"] == "SAFE_DRY_RUN_ONLY"
    assert r["submit_allowed"] is False


def test_no_command_partial():
    r = verify_command(readiness(), None)
    assert r["verdict"] == "PARTIAL"
    assert r["command_provided"] is False


def test_submit_flag_fail():
    r = verify_command(readiness(), EXPECTED + " --allow-testnet-submit")
    assert r["verdict"] == "FAIL"
    assert "--allow-testnet-submit" in r["forbidden_flags_detected"]


def test_mainnet_fail():
    bad_cmd = "python3 scripts/run.py --env mainnet --dry-run"
    r = verify_command(readiness(), bad_cmd)
    assert r["verdict"] == "FAIL"


def test_mismatch_fail():
    r = verify_command(readiness(), "python3 something else")
    assert r["verdict"] == "FAIL"
    assert r["command_matches_expected"] is False
