import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scripts.generate_next_testnet_dry_run_iteration_plan_v1 import (
    NEXT_ITERATION_STEPS,
    REQUIRED_BLOCKED_ACTIONS,
    generate_iteration_plan,
    load_json,
    write_json,
)


def valid_t472():
    return {
        "ok": True,
        "blocker_analysis_status": "DRY_RUN_RESULT_BLOCKER_ANALYSIS_COMPLETED",
        "final_decision": "READY_FOR_NEXT_DRY_RUN_ITERATION_PLAN",
    }


def test_valid_t472_pass(tmp_path):
    r = generate_iteration_plan(valid_t472())
    assert r["ok"] is True
    assert r["iteration_plan_status"] == "NEXT_DRY_RUN_ITERATION_PLAN_READY"


def test_blocked_t472_blocked(tmp_path):
    t472 = valid_t472(); t472["ok"] = False
    r = generate_iteration_plan(t472)
    assert r["ok"] is False


def test_next_steps_present(tmp_path):
    r = generate_iteration_plan(valid_t472())
    for step in NEXT_ITERATION_STEPS:
        assert step in r["next_iteration_steps"]


def test_scope_artifact_only_no_submit(tmp_path):
    r = generate_iteration_plan(valid_t472())
    assert r["next_iteration_scope"] == "NEXT_ARTIFACT_ONLY_NO_SUBMIT_DRY_RUN_ITERATION"


def test_never_allows_blocked_actions(tmp_path):
    r = generate_iteration_plan(valid_t472())
    for b in REQUIRED_BLOCKED_ACTIONS:
        assert b not in r["allowed_actions"]
        assert b in r["blocked_actions"]


def test_invalid_json(tmp_path):
    p = str(tmp_path / "bad.json")
    with open(p, "w", encoding="utf-8") as f:
        f.write("bad")
    r = generate_iteration_plan(load_json(p))
    assert r["ok"] is False


def test_missing_file(tmp_path):
    p = str(tmp_path / "missing.json")
    r = generate_iteration_plan(load_json(p))
    assert r["ok"] is False


def test_cli_smoke(tmp_path):
    p = str(tmp_path / "t472.json")
    out = str(tmp_path / "out.json")
    write_json(p, valid_t472())
    proc = subprocess.Popen([
        sys.executable,
        str(Path(__file__).parent.parent.parent / "scripts" / "generate_next_testnet_dry_run_iteration_plan_v1.py"),
        "--blocker-analysis-report", p,
        "--output", out,
        "--json",
    ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    proc.communicate()
    assert proc.returncode in [0, 1]
    assert os.path.exists(out)
