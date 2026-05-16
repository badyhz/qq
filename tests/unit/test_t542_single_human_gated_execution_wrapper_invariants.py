import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scripts.verify_single_human_gated_execution_wrapper_invariants_v1 import verify_invariants


def artifact():
    return {
        "artifact_type": "SINGLE_HUMAN_GATED_TESTNET_EXECUTION_WRAPPER",
        "wrapper_mode": "HUMAN_GATED_SINGLE_TESTNET_SUBMIT",
        "env": "testnet",
        "symbol": "BTCUSDT",
        "side": "BUY",
        "quantity": "0.01",
        "submit_allowed": False,
        "max_submit_count": 1,
        "dry_run_command": "python3 scripts/run_testnet_submit_execution_wrapper_v1.py --env testnet --symbol BTCUSDT --side BUY --quantity 0.01 --dry-run",
        "human_execution_command_template": "python3 scripts/run_testnet_submit_execution_wrapper_v1.py --allow-testnet-submit --confirm-token <TOKEN> --env testnet --symbol BTCUSDT --side BUY --quantity 0.01",
        "safety_notes": ["THIS IS A TESTNET-ONLY WRAPPER"],
    }


def test_pass():
    r = verify_invariants(artifact())
    assert r["verdict"] == "PASS"
    assert r["invariant_status"] == "INVARIANTS_PASS"
    assert r["submit_allowed"] is False
    assert r["max_submit_count"] == 1


def test_missing_token_gate_fail():
    a = artifact()
    a["human_execution_command_template"] = "python3 script.py --no-gate"
    r = verify_invariants(a)
    assert r["verdict"] == "FAIL"


def test_max_count_gt_1_fail():
    a = artifact()
    a["max_submit_count"] = 5
    r = verify_invariants(a)
    assert r["verdict"] == "FAIL"


def test_mainnet_marker_fail():
    a = artifact()
    a["env"] = "mainnet"
    r = verify_invariants(a)
    assert r["verdict"] == "FAIL"


def test_missing_safety_notes_partial():
    a = artifact()
    del a["safety_notes"]
    r = verify_invariants(a)
    assert r["verdict"] == "PARTIAL"
    assert "SAFETY_NOTES_MISSING" in r["warnings"]


def test_submit_allowed_true_fail():
    a = artifact()
    a["submit_allowed"] = True
    r = verify_invariants(a)
    assert r["verdict"] == "FAIL"


def test_submit_allowed_remains_false_in_output():
    r = verify_invariants(artifact())
    assert r["submit_allowed"] is False
