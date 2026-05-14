import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scripts.generate_testnet_dry_run_stability_review_phase_control_report_v1 import (
    REQUIRED_BLOCKED_ACTIONS,
    generate_phase_control_report,
    load_json,
    write_json,
)


def safe_flags():
    return {
        "testnet_dry_run_allowed": True,
        "exchange_api_calls_allowed": False,
        "testnet_submit_allowed": False,
        "real_submit_allowed": False,
        "submit_order_allowed": False,
        "cancel_order_allowed": False,
        "flatten_position_allowed": False,
        "submit_attempted": False,
        "cancel_attempted": False,
        "flatten_attempted": False,
    }


def allowed():
    return ["READ_REPORTS", "TESTNET_DRY_RUN_ONLY", "REVIEW_DRY_RUN_STABILITY"]


def blocked():
    return list(REQUIRED_BLOCKED_ACTIONS)


def valid_t486():
    return {
        "final_decision": "READY_FOR_TWO_ROUND_DRY_RUN_REPEATABILITY_SUMMARY",
        "safety_flags": safe_flags(),
        "allowed_actions": allowed(),
        "blocked_actions": blocked(),
    }


def valid_t487():
    return {
        "final_decision": "READY_FOR_TESTNET_DRY_RUN_STABILITY_SCORE",
        "safety_flags": safe_flags(),
        "allowed_actions": allowed(),
        "blocked_actions": blocked(),
    }


def valid_t488():
    return {
        "final_decision": "READY_FOR_DRY_RUN_TO_TESTNET_SUBMIT_READINESS_RECOMMENDATION",
        "safety_flags": safe_flags(),
        "allowed_actions": allowed(),
        "blocked_actions": blocked(),
    }


def valid_t489():
    return {
        "final_decision": "READY_FOR_TESTNET_SUBMIT_READINESS_REVIEW_PHASE_CONTROL",
        "safety_flags": safe_flags(),
        "allowed_actions": allowed(),
        "blocked_actions": blocked(),
    }


def run_report(t486, t487, t488, t489, tmp_path):
    p486 = str(tmp_path / "t486.json")
    p487 = str(tmp_path / "t487.json")
    p488 = str(tmp_path / "t488.json")
    p489 = str(tmp_path / "t489.json")
    write_json(p486, t486)
    write_json(p487, t487)
    write_json(p488, t488)
    write_json(p489, t489)
    return generate_phase_control_report(t486, t487, t488, t489, p486, p487, p488, p489)


def test_all_pass_ready_for_testnet_submit_readiness_review(tmp_path):
    r = run_report(valid_t486(), valid_t487(), valid_t488(), valid_t489(), tmp_path)
    assert r["ok"] is True
    assert r["final_decision"] == "READY_FOR_TESTNET_SUBMIT_READINESS_REVIEW"


def test_each_component_fail_exact_blocker(tmp_path):
    t486 = valid_t486(); t486["final_decision"] = "BAD"
    r = run_report(t486, valid_t487(), valid_t488(), valid_t489(), tmp_path)
    assert "T486_STABILITY_REVIEW_PACKET_NOT_READY" in r["blockers"]

    t487 = valid_t487(); t487["final_decision"] = "BAD"
    r = run_report(valid_t486(), t487, valid_t488(), valid_t489(), tmp_path)
    assert "T487_REPEATABILITY_NOT_CONFIRMED" in r["blockers"]

    t488 = valid_t488(); t488["final_decision"] = "BAD"
    r = run_report(valid_t486(), valid_t487(), t488, valid_t489(), tmp_path)
    assert "T488_STABILITY_SCORE_NOT_READY" in r["blockers"]

    t489 = valid_t489(); t489["final_decision"] = "BAD"
    r = run_report(valid_t486(), valid_t487(), valid_t488(), t489, tmp_path)
    assert "T489_READINESS_RECOMMENDATION_NOT_READY" in r["blockers"]


def test_exchange_submit_cancel_flatten_violation_blocker(tmp_path):
    t489 = valid_t489()
    t489["safety_flags"]["flatten_attempted"] = True
    r = run_report(valid_t486(), valid_t487(), valid_t488(), t489, tmp_path)
    assert "NO_SUBMIT_NO_EXCHANGE_BLOCK_NOT_CONFIRMED" in r["blockers"]


def test_allowed_actions_never_contains_blocked(tmp_path):
    r = run_report(valid_t486(), valid_t487(), valid_t488(), valid_t489(), tmp_path)
    for b in REQUIRED_BLOCKED_ACTIONS:
        assert b not in r["allowed_actions"]


def test_blocked_actions_includes_all(tmp_path):
    r = run_report(valid_t486(), valid_t487(), valid_t488(), valid_t489(), tmp_path)
    for b in REQUIRED_BLOCKED_ACTIONS:
        assert b in r["blocked_actions"]


def test_invalid_json(tmp_path):
    p486 = str(tmp_path / "t486.json")
    p487 = str(tmp_path / "t487.json")
    p488 = str(tmp_path / "t488.json")
    p489 = str(tmp_path / "bad.json")
    write_json(p486, valid_t486())
    write_json(p487, valid_t487())
    write_json(p488, valid_t488())
    with open(p489, "w", encoding="utf-8") as f:
        f.write("bad")
    r = generate_phase_control_report(load_json(p486), load_json(p487), load_json(p488), load_json(p489), p486, p487, p488, p489)
    assert r["ok"] is False


def test_missing_file(tmp_path):
    p486 = str(tmp_path / "t486.json")
    p487 = str(tmp_path / "t487.json")
    p488 = str(tmp_path / "t488.json")
    p489 = str(tmp_path / "missing.json")
    write_json(p486, valid_t486())
    write_json(p487, valid_t487())
    write_json(p488, valid_t488())
    r = generate_phase_control_report(load_json(p486), load_json(p487), load_json(p488), load_json(p489), p486, p487, p488, p489)
    assert r["ok"] is False


def test_cli_smoke(tmp_path):
    p486 = str(tmp_path / "t486.json")
    p487 = str(tmp_path / "t487.json")
    p488 = str(tmp_path / "t488.json")
    p489 = str(tmp_path / "t489.json")
    out = str(tmp_path / "out.json")
    write_json(p486, valid_t486())
    write_json(p487, valid_t487())
    write_json(p488, valid_t488())
    write_json(p489, valid_t489())
    proc = subprocess.Popen([
        sys.executable,
        str(Path(__file__).parent.parent.parent / "scripts" / "generate_testnet_dry_run_stability_review_phase_control_report_v1.py"),
        "--stability-review-packet", p486,
        "--repeatability-report", p487,
        "--stability-score-report", p488,
        "--readiness-recommendation", p489,
        "--output", out,
        "--json",
    ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    proc.communicate()
    assert proc.returncode in [0, 1]
    assert os.path.exists(out)
