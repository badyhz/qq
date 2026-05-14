import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scripts.verify_testnet_dry_run_artifact_dependencies_v1 import (
    load_json,
    write_json,
    verify_artifact_dependencies,
    REQUIRED_BLOCKED_ACTIONS,
)


def create_valid_t441() -> dict:
    return {
        "ok": True,
        "final_decision": "READY_FOR_TESTNET_DRY_RUN_READINESS_SAFETY_CONSTRAINT_REVIEW",
        "safety_flags": {
            "shadow_only": True,
            "testnet_dry_run_allowed": False,
            "testnet_submit_allowed": False,
            "real_submit_allowed": False,
            "submit_attempted": False,
            "cancel_attempted": False,
            "flatten_attempted": False,
        },
        "allowed_actions": [],
        "blocked_actions": list(REQUIRED_BLOCKED_ACTIONS),
    }


def create_valid_t442() -> dict:
    return {
        "ok": True,
        "final_decision": "READY_FOR_TESTNET_DRY_RUN_ARTIFACT_DEPENDENCY_REVIEW",
        "safety_flags": {
            "shadow_only": True,
            "testnet_dry_run_allowed": False,
            "testnet_submit_allowed": False,
            "real_submit_allowed": False,
            "submit_attempted": False,
            "cancel_attempted": False,
            "flatten_attempted": False,
        },
        "allowed_actions": [],
        "blocked_actions": list(REQUIRED_BLOCKED_ACTIONS),
    }


def create_valid_manifest() -> dict:
    return {
        "input_artifacts": [f"T{i}" for i in range(426, 441)],
        "output_artifacts": [f"T{i}" for i in range(441, 446)],
        "operator_review_required": True,
        "manual_approval_required": True,
    }


def run_report(t441: dict, t442: dict, manifest: dict, tmp_path):
    t441_path = str(tmp_path / "t441.json")
    t442_path = str(tmp_path / "t442.json")
    manifest_path = str(tmp_path / "manifest.json")
    write_json(t441_path, t441)
    write_json(t442_path, t442)
    write_json(manifest_path, manifest)

    return verify_artifact_dependencies(
        t441,
        t442,
        manifest,
        t441_path,
        t442_path,
        manifest_path,
    )


def test_valid_manifest_pass(tmp_path):
    report = run_report(create_valid_t441(), create_valid_t442(), create_valid_manifest(), tmp_path)
    assert report["ok"] is True
    assert report["dependency_status"] == "TESTNET_DRY_RUN_ARTIFACT_DEPENDENCIES_VERIFIED"
    assert report["final_decision"] == "READY_FOR_TESTNET_DRY_RUN_READINESS_SCORE"


def test_missing_t426_fail(tmp_path):
    manifest = create_valid_manifest()
    manifest["input_artifacts"].remove("T426")
    report = run_report(create_valid_t441(), create_valid_t442(), manifest, tmp_path)
    assert report["ok"] is False
    assert "INPUT_ARTIFACT_T426_MISSING" in report["missing_dependencies"]


def test_missing_t440_fail(tmp_path):
    manifest = create_valid_manifest()
    manifest["input_artifacts"].remove("T440")
    report = run_report(create_valid_t441(), create_valid_t442(), manifest, tmp_path)
    assert report["ok"] is False
    assert "INPUT_ARTIFACT_T440_MISSING" in report["missing_dependencies"]


def test_missing_t445_output_fail(tmp_path):
    manifest = create_valid_manifest()
    manifest["output_artifacts"].remove("T445")
    report = run_report(create_valid_t441(), create_valid_t442(), manifest, tmp_path)
    assert report["ok"] is False
    assert "OUTPUT_ARTIFACT_T445_MISSING" in report["missing_dependencies"]


def test_operator_review_false_fail(tmp_path):
    manifest = create_valid_manifest()
    manifest["operator_review_required"] = False
    report = run_report(create_valid_t441(), create_valid_t442(), manifest, tmp_path)
    assert report["ok"] is False
    assert "OPERATOR_REVIEW_NOT_REQUIRED" in report["missing_dependencies"]


def test_manual_approval_false_fail(tmp_path):
    manifest = create_valid_manifest()
    manifest["manual_approval_required"] = False
    report = run_report(create_valid_t441(), create_valid_t442(), manifest, tmp_path)
    assert report["ok"] is False
    assert "MANUAL_APPROVAL_NOT_REQUIRED" in report["missing_dependencies"]


def test_t441_fail(tmp_path):
    t441 = create_valid_t441()
    t441["ok"] = False
    report = run_report(t441, create_valid_t442(), create_valid_manifest(), tmp_path)
    assert report["ok"] is False
    assert "READINESS_INPUT_PACKET_NOT_READY" in report["missing_dependencies"]


def test_t442_fail(tmp_path):
    t442 = create_valid_t442()
    t442["ok"] = False
    report = run_report(create_valid_t441(), t442, create_valid_manifest(), tmp_path)
    assert report["ok"] is False
    assert "SAFETY_CONSTRAINTS_NOT_VERIFIED" in report["missing_dependencies"]


def test_safety_invariants(tmp_path):
    report = run_report(create_valid_t441(), create_valid_t442(), create_valid_manifest(), tmp_path)

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
    manifest_path = str(tmp_path / "manifest.json")
    write_json(t441_path, create_valid_t441())
    write_json(t442_path, create_valid_t442())
    with open(manifest_path, "w", encoding="utf-8") as f:
        f.write("invalid json")

    report = verify_artifact_dependencies(
        load_json(t441_path),
        load_json(t442_path),
        load_json(manifest_path),
        t441_path,
        t442_path,
        manifest_path,
    )
    assert report["ok"] is False


def test_missing_file(tmp_path):
    t441_path = str(tmp_path / "t441.json")
    t442_path = str(tmp_path / "t442.json")
    missing_manifest_path = str(tmp_path / "missing_manifest.json")
    write_json(t441_path, create_valid_t441())
    write_json(t442_path, create_valid_t442())

    report = verify_artifact_dependencies(
        load_json(t441_path),
        load_json(t442_path),
        load_json(missing_manifest_path),
        t441_path,
        t442_path,
        missing_manifest_path,
    )
    assert report["ok"] is False


def test_cli_smoke(tmp_path):
    t441_path = str(tmp_path / "t441.json")
    t442_path = str(tmp_path / "t442.json")
    manifest_path = str(tmp_path / "manifest.json")
    output_path = str(tmp_path / "out.json")

    write_json(t441_path, create_valid_t441())
    write_json(t442_path, create_valid_t442())
    write_json(manifest_path, create_valid_manifest())

    proc = subprocess.Popen(
        [
            sys.executable,
            str(
                Path(__file__).parent.parent.parent
                / "scripts"
                / "verify_testnet_dry_run_artifact_dependencies_v1.py"
            ),
            "--readiness-input-packet",
            t441_path,
            "--safety-constraint-report",
            t442_path,
            "--artifact-manifest",
            manifest_path,
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
