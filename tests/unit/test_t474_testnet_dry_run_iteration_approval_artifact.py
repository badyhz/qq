import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scripts.generate_testnet_dry_run_iteration_approval_artifact_v1 import (
    REQUIRED_BLOCKED_ACTIONS,
    generate_iteration_approval_artifact,
    load_json,
    write_json,
)


def valid_t473():
    return {
        "ok": True,
        "iteration_plan_status": "NEXT_DRY_RUN_ITERATION_PLAN_READY",
        "final_decision": "READY_FOR_DRY_RUN_ITERATION_APPROVAL_ARTIFACT",
    }


def test_valid_t473_pass(tmp_path):
    r = generate_iteration_approval_artifact(valid_t473())
    assert r["ok"] is True
    assert r["approval_status"] == "NEXT_DRY_RUN_ITERATION_APPROVED"


def test_blocked_t473_blocked(tmp_path):
    t473 = valid_t473(); t473["ok"] = False
    r = generate_iteration_approval_artifact(t473)
    assert r["ok"] is False


def test_approval_scope_no_submit_only(tmp_path):
    r = generate_iteration_approval_artifact(valid_t473())
    assert r["approval_scope"] == "APPROVE_NEXT_ARTIFACT_ONLY_NO_SUBMIT_DRY_RUN_ITERATION"


def test_never_allows_blocked_actions(tmp_path):
    r = generate_iteration_approval_artifact(valid_t473())
    for b in REQUIRED_BLOCKED_ACTIONS:
        assert b not in r["allowed_actions"]
        assert b in r["blocked_actions"]


def test_invalid_json(tmp_path):
    p = str(tmp_path / "bad.json")
    with open(p, "w", encoding="utf-8") as f:
        f.write("bad")
    r = generate_iteration_approval_artifact(load_json(p))
    assert r["ok"] is False


def test_missing_file(tmp_path):
    p = str(tmp_path / "missing.json")
    r = generate_iteration_approval_artifact(load_json(p))
    assert r["ok"] is False


def test_cli_smoke(tmp_path):
    p = str(tmp_path / "t473.json")
    out = str(tmp_path / "out.json")
    write_json(p, valid_t473())
    proc = subprocess.Popen([
        sys.executable,
        str(Path(__file__).parent.parent.parent / "scripts" / "generate_testnet_dry_run_iteration_approval_artifact_v1.py"),
        "--iteration-plan", p,
        "--output", out,
        "--json",
    ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    proc.communicate()
    assert proc.returncode in [0, 1]
    assert os.path.exists(out)
