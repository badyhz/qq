import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scripts.generate_single_human_gated_execution_command_preview_packet_v1 import generate_preview


def artifact(v="PASS"):
    return {
        "verdict": v,
        "dry_run_command": "python3 scripts/run_testnet_submit_execution_wrapper_v1.py --env testnet --symbol BTCUSDT --side BUY --quantity 0.01 --dry-run",
        "human_execution_command_template": "python3 scripts/run_testnet_submit_execution_wrapper_v1.py --allow-testnet-submit --confirm-token <TOKEN> --env testnet --symbol BTCUSDT --side BUY --quantity 0.01",
    }


def invariant(v="PASS"):
    return {"verdict": v}


def test_pass():
    r = generate_preview(artifact("PASS"), invariant("PASS"))
    assert r["verdict"] == "PASS"
    assert r["command_preview_type"] == "HUMAN_REVIEW_ONLY"
    assert r["execution_locked"] is True
    assert r["submit_allowed"] is False
    assert r["max_submit_count"] == 1


def test_invariant_partial():
    r = generate_preview(artifact("PASS"), invariant("PARTIAL"))
    assert r["verdict"] == "PARTIAL"


def test_invariant_fail():
    r = generate_preview(artifact("PASS"), invariant("FAIL"))
    assert r["verdict"] == "FAIL"


def test_execution_locked_always_true():
    r = generate_preview(artifact("PASS"), invariant("PASS"))
    assert r["execution_locked"] is True


def test_submit_allowed_always_false():
    r = generate_preview(artifact("PASS"), invariant("PASS"))
    assert r["submit_allowed"] is False


def test_unlock_requirements_present():
    r = generate_preview(artifact("PASS"), invariant("PASS"))
    reqs = r["unlock_requirements"]
    assert "EXACT_CONFIRM_TOKEN" in reqs
    assert "--allow-testnet-submit" in reqs
    assert "--env testnet" in reqs
    assert "HUMAN_CONFIRMATION" in reqs
    assert "MAX_SUBMIT_COUNT=1" in reqs
