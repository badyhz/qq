import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scripts.generate_testnet_dry_run_readiness_score_v1 import (
    load_json,
    write_json,
    generate_readiness_score,
    REQUIRED_BLOCKED_ACTIONS,
    _grade,
)


def safety_flags() -> dict:
    return {
        "shadow_only": True,
        "testnet_dry_run_allowed": False,
        "testnet_submit_allowed": False,
        "real_submit_allowed": False,
        "submit_attempted": False,
        "cancel_attempted": False,
        "flatten_attempted": False,
    }


def create_valid_t441() -> dict:
    return {
        "ok": True,
        "final_decision": "READY_FOR_TESTNET_DRY_RUN_READINESS_SAFETY_CONSTRAINT_REVIEW",
        "safety_flags": safety_flags(),
        "allowed_actions": [],
        "blocked_actions": list(REQUIRED_BLOCKED_ACTIONS),
    }


def create_valid_t442() -> dict:
    return {
        "ok": True,
        "final_decision": "READY_FOR_TESTNET_DRY_RUN_ARTIFACT_DEPENDENCY_REVIEW",
        "safety_flags": safety_flags(),
        "allowed_actions": [],
        "blocked_actions": list(REQUIRED_BLOCKED_ACTIONS),
    }


def create_valid_t443() -> dict:
    return {
        "ok": True,
        "final_decision": "READY_FOR_TESTNET_DRY_RUN_READINESS_SCORE",
        "safety_flags": safety_flags(),
        "allowed_actions": [],
        "blocked_actions": list(REQUIRED_BLOCKED_ACTIONS),
    }


def run_report(t441: dict, t442: dict, t443: dict, tmp_path):
    t441_path = str(tmp_path / "t441.json")
    t442_path = str(tmp_path / "t442.json")
    t443_path = str(tmp_path / "t443.json")
    write_json(t441_path, t441)
    write_json(t442_path, t442)
    write_json(t443_path, t443)

    return generate_readiness_score(
        t441,
        t442,
        t443,
        t441_path,
        t442_path,
        t443_path,
    )


def test_all_pass_score_100_grade_a(tmp_path):
    report = run_report(create_valid_t441(), create_valid_t442(), create_valid_t443(), tmp_path)
    assert report["ok"] is True
    assert report["readiness_score"] == 100
    assert report["readiness_grade"] == "A"
    assert report["final_decision"] == "READY_FOR_MANUAL_TESTNET_DRY_RUN_APPROVAL_REVIEW"


def test_t441_fail_score_75(tmp_path):
    t441 = create_valid_t441()
    t441["ok"] = False
    report = run_report(t441, create_valid_t442(), create_valid_t443(), tmp_path)
    assert report["ok"] is False
    assert report["readiness_score"] == 75
    assert "READINESS_INPUT_NOT_READY" in report["blockers"]


def test_t442_fail_score_75(tmp_path):
    t442 = create_valid_t442()
    t442["ok"] = False
    report = run_report(create_valid_t441(), t442, create_valid_t443(), tmp_path)
    assert report["ok"] is False
    assert report["readiness_score"] == 75
    assert "SAFETY_CONSTRAINTS_NOT_VERIFIED" in report["blockers"]


def test_t443_fail_score_75(tmp_path):
    t443 = create_valid_t443()
    t443["ok"] = False
    report = run_report(create_valid_t441(), create_valid_t442(), t443, tmp_path)
    assert report["ok"] is False
    assert report["readiness_score"] == 75
    assert "ARTIFACT_DEPENDENCIES_NOT_VERIFIED" in report["blockers"]


def test_execution_violation_blocker(tmp_path):
    t443 = create_valid_t443()
    t443["safety_flags"]["submit_attempted"] = True
    report = run_report(create_valid_t441(), create_valid_t442(), t443, tmp_path)
    assert report["ok"] is False
    assert "EXECUTION_BLOCK_NOT_CONFIRMED" in report["blockers"]


def test_allowed_contains_testnet_dry_run_only_blocker(tmp_path):
    t443 = create_valid_t443()
    t443["allowed_actions"].append("TESTNET_DRY_RUN_ONLY")
    report = run_report(create_valid_t441(), create_valid_t442(), t443, tmp_path)
    assert report["ok"] is False
    assert "EXECUTION_BLOCK_NOT_CONFIRMED" in report["blockers"]


def test_blocked_missing_real_submit_blocker(tmp_path):
    t443 = create_valid_t443()
    t443["blocked_actions"].remove("REAL_SUBMIT")
    report = run_report(create_valid_t441(), create_valid_t442(), t443, tmp_path)
    assert report["ok"] is False
    assert "EXECUTION_BLOCK_NOT_CONFIRMED" in report["blockers"]


def test_grade_mapping():
    assert _grade(99) == "B"
    assert _grade(74) == "C"
    assert _grade(49) == "D"
    assert _grade(0) == "F"


def test_output_safety_invariants(tmp_path):
    report = run_report(create_valid_t441(), create_valid_t442(), create_valid_t443(), tmp_path)
    assert report["safety_flags"]["testnet_dry_run_allowed"] is False
    assert report["safety_flags"]["testnet_submit_allowed"] is False
    assert report["safety_flags"]["real_submit_allowed"] is False
    assert report["safety_flags"]["submit_attempted"] is False
    assert report["safety_flags"]["cancel_attempted"] is False
    assert report["safety_flags"]["flatten_attempted"] is False

    for blocked in REQUIRED_BLOCKED_ACTIONS:
        assert blocked not in report["allowed_actions"]
        assert blocked in report["blocked_actions"]


def test_invalid_json(tmp_path):
    t441_path = str(tmp_path / "t441.json")
    t442_path = str(tmp_path / "t442.json")
    t443_path = str(tmp_path / "t443.json")

    write_json(t441_path, create_valid_t441())
    write_json(t442_path, create_valid_t442())
    with open(t443_path, "w", encoding="utf-8") as f:
        f.write("invalid json")

    report = generate_readiness_score(
        load_json(t441_path),
        load_json(t442_path),
        load_json(t443_path),
        t441_path,
        t442_path,
        t443_path,
    )
    assert report["ok"] is False


def test_missing_file(tmp_path):
    t441_path = str(tmp_path / "t441.json")
    t442_path = str(tmp_path / "t442.json")
    t443_path = str(tmp_path / "missing_t443.json")

    write_json(t441_path, create_valid_t441())
    write_json(t442_path, create_valid_t442())

    report = generate_readiness_score(
        load_json(t441_path),
        load_json(t442_path),
        load_json(t443_path),
        t441_path,
        t442_path,
        t443_path,
    )
    assert report["ok"] is False


def test_cli_smoke(tmp_path):
    t441_path = str(tmp_path / "t441.json")
    t442_path = str(tmp_path / "t442.json")
    t443_path = str(tmp_path / "t443.json")
    output_path = str(tmp_path / "out.json")

    write_json(t441_path, create_valid_t441())
    write_json(t442_path, create_valid_t442())
    write_json(t443_path, create_valid_t443())

    proc = subprocess.Popen(
        [
            sys.executable,
            str(
                Path(__file__).parent.parent.parent
                / "scripts"
                / "generate_testnet_dry_run_readiness_score_v1.py"
            ),
            "--readiness-input-packet",
            t441_path,
            "--safety-constraint-report",
            t442_path,
            "--artifact-dependency-report",
            t443_path,
            "--output",
            output_path,
            "--json",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    proc.communicate()

    assert proc.returncode in [0, 1]
    assert os.path.exists(output_path)
