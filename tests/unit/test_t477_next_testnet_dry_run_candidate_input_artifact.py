import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scripts.generate_next_testnet_dry_run_candidate_input_artifact_v1 import (
    REQUIRED_BLOCKED_ACTIONS,
    generate_candidate_input_artifact,
    load_json,
    write_json,
)


def valid_t476():
    return {"ok": True, "final_decision": "READY_FOR_NEXT_DRY_RUN_CANDIDATE_INPUT_ARTIFACT"}


def valid_t473():
    return {"ok": True, "iteration_plan_status": "NEXT_DRY_RUN_ITERATION_PLAN_READY"}


def test_valid_t476_t473_pass(tmp_path):
    r = generate_candidate_input_artifact(valid_t476(), valid_t473())
    assert r["ok"] is True
    assert r["candidate_artifact_status"] == "NEXT_DRY_RUN_CANDIDATE_INPUT_READY"


def test_t476_blocked_fail(tmp_path):
    t476 = valid_t476(); t476["ok"] = False
    r = generate_candidate_input_artifact(t476, valid_t473())
    assert r["ok"] is False
    assert "EXECUTION_PACKET_NOT_READY" in r["violations"]


def test_t473_blocked_fail(tmp_path):
    t473 = valid_t473(); t473["ok"] = False
    r = generate_candidate_input_artifact(valid_t476(), t473)
    assert r["ok"] is False
    assert "ITERATION_PLAN_NOT_READY" in r["violations"]


def test_candidate_dry_run_only_true(tmp_path):
    r = generate_candidate_input_artifact(valid_t476(), valid_t473())
    assert r["candidate_input"]["dry_run_only"] is True


def test_candidate_artifact_only_true(tmp_path):
    r = generate_candidate_input_artifact(valid_t476(), valid_t473())
    assert r["candidate_input"]["artifact_only"] is True


def test_never_allows_blocked_actions(tmp_path):
    r = generate_candidate_input_artifact(valid_t476(), valid_t473())
    for b in REQUIRED_BLOCKED_ACTIONS:
        assert b not in r["allowed_actions"]
        assert b in r["blocked_actions"]


def test_invalid_json(tmp_path):
    p1 = str(tmp_path / "t476.json")
    p2 = str(tmp_path / "t473.json")
    write_json(p1, valid_t476())
    with open(p2, "w", encoding="utf-8") as f:
        f.write("bad")
    r = generate_candidate_input_artifact(load_json(p1), load_json(p2))
    assert r["ok"] is False


def test_missing_file(tmp_path):
    p1 = str(tmp_path / "t476.json")
    p2 = str(tmp_path / "missing.json")
    write_json(p1, valid_t476())
    r = generate_candidate_input_artifact(load_json(p1), load_json(p2))
    assert r["ok"] is False


def test_cli_smoke(tmp_path):
    p1 = str(tmp_path / "t476.json")
    p2 = str(tmp_path / "t473.json")
    out = str(tmp_path / "out.json")
    write_json(p1, valid_t476())
    write_json(p2, valid_t473())
    proc = subprocess.Popen([
        sys.executable,
        str(Path(__file__).parent.parent.parent / "scripts" / "generate_next_testnet_dry_run_candidate_input_artifact_v1.py"),
        "--execution-packet", p1,
        "--iteration-plan", p2,
        "--output", out,
        "--json",
    ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    proc.communicate()
    assert proc.returncode in [0, 1]
    assert os.path.exists(out)
