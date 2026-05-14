import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scripts.generate_testnet_dry_run_enablement_phase_control_report_v1 import (
    REQUIRED_BLOCKED_ACTIONS,
    generate_enablement_phase_control_report,
    load_json,
    write_json,
)


def safe_flags(dry_run_allowed=False):
    return {
        "shadow_only": True,
        "testnet_dry_run_allowed": dry_run_allowed,
        "testnet_submit_allowed": False,
        "real_submit_allowed": False,
        "submit_attempted": False,
        "cancel_attempted": False,
        "flatten_attempted": False,
    }


def base_allowed():
    return ["READ_REPORTS"]


def base_blocked():
    return list(REQUIRED_BLOCKED_ACTIONS)


def valid_t451():
    return {
        "final_decision": "READY_FOR_TESTNET_DRY_RUN_ENABLEMENT_SAFETY_SWITCH_REVIEW",
        "safety_flags": safe_flags(False),
        "allowed_actions": base_allowed(),
        "blocked_actions": base_blocked(),
    }


def valid_t452():
    return {
        "final_decision": "READY_FOR_TESTNET_DRY_RUN_OPERATOR_CONFIRMATION",
        "safety_flags": safe_flags(False),
        "allowed_actions": base_allowed(),
        "blocked_actions": base_blocked(),
    }


def valid_t453():
    return {
        "final_decision": "READY_FOR_TESTNET_DRY_RUN_ENABLEMENT_FINAL_GATE",
        "safety_flags": safe_flags(False),
        "allowed_actions": base_allowed(),
        "blocked_actions": base_blocked(),
    }


def valid_t454():
    return {
        "final_decision": "READY_FOR_TESTNET_DRY_RUN_ONLY_MODE",
        "safety_flags": safe_flags(False),
        "allowed_actions": base_allowed(),
        "blocked_actions": base_blocked(),
    }


def run_report(t451, t452, t453, t454, tmp_path):
    p451 = str(tmp_path / "t451.json")
    p452 = str(tmp_path / "t452.json")
    p453 = str(tmp_path / "t453.json")
    p454 = str(tmp_path / "t454.json")
    write_json(p451, t451)
    write_json(p452, t452)
    write_json(p453, t453)
    write_json(p454, t454)

    return generate_enablement_phase_control_report(
        t451, t452, t453, t454, p451, p452, p453, p454
    )


def test_all_pass_ready_for_dry_run_only_mode(tmp_path):
    report = run_report(valid_t451(), valid_t452(), valid_t453(), valid_t454(), tmp_path)

    assert report["ok"] is True
    assert report["phase_completion_status"] == "COMPLETED_READY_FOR_TESTNET_DRY_RUN_ONLY_MODE"
    assert report["next_phase"] == "TESTNET_DRY_RUN_ONLY_MODE"
    assert report["safety_flags"]["testnet_dry_run_allowed"] is True
    assert report["final_decision"] == "READY_FOR_TESTNET_DRY_RUN_ONLY_MODE"


def test_each_component_fail_exact_blockers(tmp_path):
    t451 = valid_t451()
    t451["final_decision"] = "BAD"
    report = run_report(t451, valid_t452(), valid_t453(), valid_t454(), tmp_path)
    assert "T451_ENABLEMENT_PACKET_NOT_READY" in report["blockers"]

    t452 = valid_t452()
    t452["final_decision"] = "BAD"
    report = run_report(valid_t451(), t452, valid_t453(), valid_t454(), tmp_path)
    assert "T452_SAFETY_SWITCH_NOT_VERIFIED" in report["blockers"]

    t453 = valid_t453()
    t453["final_decision"] = "BAD"
    report = run_report(valid_t451(), valid_t452(), t453, valid_t454(), tmp_path)
    assert "T453_OPERATOR_CONFIRMATION_NOT_READY" in report["blockers"]

    t454 = valid_t454()
    t454["final_decision"] = "BAD"
    report = run_report(valid_t451(), valid_t452(), valid_t453(), t454, tmp_path)
    assert "T454_FINAL_GATE_NOT_PASSED" in report["blockers"]


def test_submit_cancel_flatten_violation_blocker(tmp_path):
    t454 = valid_t454()
    t454["safety_flags"]["submit_attempted"] = True
    report = run_report(valid_t451(), valid_t452(), valid_t453(), t454, tmp_path)

    assert report["ok"] is False
    assert "SUBMIT_CANCEL_FLATTEN_BLOCK_NOT_CONFIRMED" in report["blockers"]


def test_blocked_actions_missing_flatten_position_blocker(tmp_path):
    t454 = valid_t454()
    t454["blocked_actions"].remove("FLATTEN_POSITION")
    report = run_report(valid_t451(), valid_t452(), valid_t453(), t454, tmp_path)

    assert report["ok"] is False
    assert "SUBMIT_CANCEL_FLATTEN_BLOCK_NOT_CONFIRMED" in report["blockers"]


def test_output_never_allows_submit_cancel_flatten(tmp_path):
    report = run_report(valid_t451(), valid_t452(), valid_t453(), valid_t454(), tmp_path)

    for blocked in REQUIRED_BLOCKED_ACTIONS:
        assert blocked not in report["allowed_actions"]
        assert blocked in report["blocked_actions"]


def test_invalid_json(tmp_path):
    p451 = str(tmp_path / "t451.json")
    p452 = str(tmp_path / "t452.json")
    p453 = str(tmp_path / "t453.json")
    p454 = str(tmp_path / "t454.json")

    write_json(p451, valid_t451())
    write_json(p452, valid_t452())
    write_json(p453, valid_t453())
    with open(p454, "w", encoding="utf-8") as f:
        f.write("invalid json")

    report = generate_enablement_phase_control_report(
        load_json(p451), load_json(p452), load_json(p453), load_json(p454), p451, p452, p453, p454
    )
    assert report["ok"] is False


def test_missing_file(tmp_path):
    p451 = str(tmp_path / "t451.json")
    p452 = str(tmp_path / "t452.json")
    p453 = str(tmp_path / "t453.json")
    p454 = str(tmp_path / "missing_t454.json")

    write_json(p451, valid_t451())
    write_json(p452, valid_t452())
    write_json(p453, valid_t453())

    report = generate_enablement_phase_control_report(
        load_json(p451), load_json(p452), load_json(p453), load_json(p454), p451, p452, p453, p454
    )
    assert report["ok"] is False


def test_cli_smoke(tmp_path):
    p451 = str(tmp_path / "t451.json")
    p452 = str(tmp_path / "t452.json")
    p453 = str(tmp_path / "t453.json")
    p454 = str(tmp_path / "t454.json")
    out = str(tmp_path / "out.json")

    write_json(p451, valid_t451())
    write_json(p452, valid_t452())
    write_json(p453, valid_t453())
    write_json(p454, valid_t454())

    proc = subprocess.Popen(
        [
            sys.executable,
            str(
                Path(__file__).parent.parent.parent
                / "scripts"
                / "generate_testnet_dry_run_enablement_phase_control_report_v1.py"
            ),
            "--enablement-packet",
            p451,
            "--safety-switch-report",
            p452,
            "--operator-confirmation-artifact",
            p453,
            "--final-gate-report",
            p454,
            "--output",
            out,
            "--json",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    proc.communicate()

    assert proc.returncode in [0, 1]
    assert os.path.exists(out)
