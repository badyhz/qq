import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scripts.generate_single_human_gated_testnet_execution_wrapper_artifact_v1 import generate_artifact


def phase(v="PASS", decision="READY_FOR_SINGLE_HUMAN_GATED_TESTNET_EXECUTION"):
    return {"verdict": v, "decision": decision, "submit_allowed": False}


def gate(v="PASS", status="READY_FOR_HUMAN_EXECUTION"):
    return {"verdict": v, "gate_status": status, "submit_allowed": False}


def plan(v="PASS"):
    return {
        "verdict": v,
        "submit_allowed": False,
        "dry_run_command": "python3 scripts/run_testnet_submit_execution_wrapper_v1.py --env testnet --symbol BTCUSDT --side BUY --quantity 0.01 --dry-run",
        "execution_command_template": "python3 scripts/run_testnet_submit_execution_wrapper_v1.py --allow-testnet-submit --confirm-token <TOKEN> --env testnet --symbol BTCUSDT --side BUY --quantity 0.01",
    }


def packet(v="PASS"):
    return {
        "verdict": v,
        "env": "testnet",
        "symbol": "BTCUSDT",
        "side": "BUY",
        "quantity": "0.01",
        "submit_allowed": False,
        "max_submit_count": 1,
    }


def token(v="PASS"):
    return {"verdict": v, "submit_allowed": False, "max_submit_count": 1}


def test_pass():
    r = generate_artifact(phase("PASS"), gate("PASS"), plan("PASS"), packet("PASS"), token("PASS"))
    assert r["verdict"] == "PASS"
    assert r["artifact_type"] == "SINGLE_HUMAN_GATED_TESTNET_EXECUTION_WRAPPER"
    assert r["wrapper_mode"] == "HUMAN_GATED_SINGLE_TESTNET_SUBMIT"
    assert r["env"] == "testnet"
    assert r["submit_allowed"] is False
    assert r["max_submit_count"] == 1
    assert "--allow-testnet-submit" in r["required_runtime_inputs"]
    assert "--confirm-token" in str(r["required_runtime_inputs"])
    assert "--env testnet" in r["required_runtime_inputs"]


def test_phase_not_ready_fail():
    r = generate_artifact(phase("PASS", "REVIEW"), gate("PASS"), plan("PASS"), packet("PASS"), token("PASS"))
    assert r["verdict"] == "FAIL"


def test_final_gate_blocked_fail():
    r = generate_artifact(phase("PASS"), gate("PASS", "BLOCKED"), plan("PASS"), packet("PASS"), token("PASS"))
    assert r["verdict"] == "FAIL"


def test_env_not_testnet_fail():
    p = packet("PASS")
    p["env"] = "mainnet"
    r = generate_artifact(phase("PASS"), gate("PASS"), plan("PASS"), p, token("PASS"))
    assert r["verdict"] == "FAIL"


def test_live_marker_fail():
    pl = plan("PASS")
    pl["execution_command_template"] = "python3 script.py --env mainnet"
    r = generate_artifact(phase("PASS"), gate("PASS"), pl, packet("PASS"), token("PASS"))
    assert r["verdict"] == "FAIL"


def test_missing_token_gate_fail():
    pl = plan("PASS")
    pl["execution_command_template"] = "python3 script.py --no-gate"
    r = generate_artifact(phase("PASS"), gate("PASS"), pl, packet("PASS"), token("PASS"))
    assert r["verdict"] == "FAIL"


def test_submit_allowed_remains_false():
    r = generate_artifact(phase("PASS"), gate("PASS"), plan("PASS"), packet("PASS"), token("PASS"))
    assert r["submit_allowed"] is False
