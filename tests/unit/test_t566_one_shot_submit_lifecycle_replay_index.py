import json
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scripts.generate_one_shot_submit_lifecycle_replay_index_v1 import generate_replay_index


REQUIRED_PHASES = [
    "SINGLE_MANUAL_SUBMIT_PACKET_GENERATION",
    "HUMAN_GATED_EXECUTION_WRAPPER_REVIEW",
    "SINGLE_HUMAN_GATED_EXECUTION_WRAPPER_ARTIFACT",
    "FINAL_HUMAN_GATED_ONE_SHOT_SUBMIT_REVIEW",
    "POST_HUMAN_SUBMIT_READONLY_VERIFICATION",
    "POST_HUMAN_SUBMIT_INCIDENT_REVIEW",
    "POST_HUMAN_SUBMIT_FINAL_CLOSEOUT",
]


def _write_temp_json(data):
    fd, path = tempfile.mkstemp(suffix=".json")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(data, f)
    return path


def _write_invalid_json():
    fd, path = tempfile.mkstemp(suffix=".json")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write("{not valid json")
    return path


def _cleanup(paths):
    for path in paths:
        try:
            os.unlink(path)
        except Exception:
            pass


def _artifact(phase, decision="OK"):
    return {
        "phase": phase,
        "verdict": "PASS",
        "decision": decision,
        "readonly": True,
        "submit_allowed": False,
        "cancel_allowed": False,
        "flatten_allowed": False,
        "max_submit_count": 0,
    }


def test_pass():
    paths = [_write_temp_json(_artifact(phase)) for phase in REQUIRED_PHASES]
    try:
        r = generate_replay_index(paths)
        assert r["ok"] is True
        assert r["verdict"] == "PASS"
        assert r["missing_phases"] == []
        assert r["duplicated_phases"] == []
        assert r["submit_allowed"] is False
        assert r["cancel_allowed"] is False
        assert r["flatten_allowed"] is False
    finally:
        _cleanup(paths)


def test_fail_missing_required_phase():
    paths = [_write_temp_json(_artifact(phase)) for phase in REQUIRED_PHASES[:-1]]
    try:
        r = generate_replay_index(paths)
        assert r["ok"] is False
        assert r["verdict"] == "FAIL"
        assert "POST_HUMAN_SUBMIT_FINAL_CLOSEOUT" in r["missing_phases"]
    finally:
        _cleanup(paths)


def test_fail_duplicate_conflicting_phase():
    paths = [_write_temp_json(_artifact(phase)) for phase in REQUIRED_PHASES]
    duplicate = _write_temp_json(_artifact("POST_HUMAN_SUBMIT_INCIDENT_REVIEW", decision="CONFLICT_DECISION"))
    paths.append(duplicate)
    try:
        r = generate_replay_index(paths)
        assert r["ok"] is False
        assert r["verdict"] == "FAIL"
        assert "POST_HUMAN_SUBMIT_INCIDENT_REVIEW" in r["duplicated_phases"]
        assert any("DUPLICATED_CONFLICTING_PHASE" in b for b in r["blockers"])
    finally:
        _cleanup(paths)


def test_fail_invalid_json():
    paths = [_write_temp_json(_artifact(phase)) for phase in REQUIRED_PHASES]
    bad = _write_invalid_json()
    paths[-1] = bad
    try:
        r = generate_replay_index(paths)
        assert r["ok"] is False
        assert r["verdict"] == "FAIL"
        assert any("INVALID_OR_UNREADABLE_JSON" in b for b in r["blockers"])
    finally:
        _cleanup(paths)


def test_fail_unsafe_marker():
    paths = [_write_temp_json(_artifact(phase)) for phase in REQUIRED_PHASES]
    unsafe = _artifact("POST_HUMAN_SUBMIT_FINAL_CLOSEOUT")
    unsafe["env"] = "mainnet"
    unsafe_path = _write_temp_json(unsafe)
    paths[-1] = unsafe_path
    try:
        r = generate_replay_index(paths)
        assert r["ok"] is False
        assert r["verdict"] == "FAIL"
        assert any("UNSAFE_MARKER_DETECTED" in b for b in r["blockers"])
    finally:
        _cleanup(paths)
