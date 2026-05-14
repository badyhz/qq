import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scripts.build_next_testnet_dry_run_no_submit_payload_plan_v1 import (
    REQUIRED_BLOCKED_ACTIONS,
    build_payload_plan,
    load_json,
    write_json,
)


def valid_t477():
    return {
        "ok": True,
        "candidate_artifact_status": "NEXT_DRY_RUN_CANDIDATE_INPUT_READY",
        "candidate_input": {
            "candidate_id": "next-dryrun-candidate-001",
            "symbol": "BTCUSDT",
            "side": "BUY",
            "quantity": "0.001",
            "order_type": "MARKET",
            "dry_run_only": True,
            "artifact_only": True,
        },
    }


def test_valid_candidate_pass(tmp_path):
    r = build_payload_plan(valid_t477())
    assert r["ok"] is True
    assert r["payload_plan_status"] == "NEXT_NO_SUBMIT_PAYLOAD_PLAN_READY"


def test_t477_blocked_fail(tmp_path):
    t477 = valid_t477(); t477["ok"] = False
    r = build_payload_plan(t477)
    assert r["ok"] is False
    assert "CANDIDATE_ARTIFACT_NOT_READY" in r["violations"]


def test_dry_run_only_false_fail(tmp_path):
    t477 = valid_t477(); t477["candidate_input"]["dry_run_only"] = False
    r = build_payload_plan(t477)
    assert "CANDIDATE_NOT_DRY_RUN_ONLY" in r["violations"]


def test_artifact_only_false_fail(tmp_path):
    t477 = valid_t477(); t477["candidate_input"]["artifact_only"] = False
    r = build_payload_plan(t477)
    assert "CANDIDATE_NOT_ARTIFACT_ONLY" in r["violations"]


def test_missing_symbol_fail(tmp_path):
    t477 = valid_t477(); t477["candidate_input"]["symbol"] = ""
    r = build_payload_plan(t477)
    assert "SYMBOL_MISSING" in r["violations"]


def test_invalid_side_fail(tmp_path):
    t477 = valid_t477(); t477["candidate_input"]["side"] = "HOLD"
    r = build_payload_plan(t477)
    assert "INVALID_SIDE" in r["violations"]


def test_never_allows_blocked_actions(tmp_path):
    r = build_payload_plan(valid_t477())
    for b in REQUIRED_BLOCKED_ACTIONS:
        assert b not in r["allowed_actions"]
        assert b in r["blocked_actions"]


def test_invalid_json(tmp_path):
    p = str(tmp_path / "bad.json")
    with open(p, "w", encoding="utf-8") as f:
        f.write("bad")
    r = build_payload_plan(load_json(p))
    assert r["ok"] is False


def test_missing_file(tmp_path):
    p = str(tmp_path / "missing.json")
    r = build_payload_plan(load_json(p))
    assert r["ok"] is False


def test_cli_smoke(tmp_path):
    p = str(tmp_path / "t477.json")
    out = str(tmp_path / "out.json")
    write_json(p, valid_t477())
    proc = subprocess.Popen([
        sys.executable,
        str(Path(__file__).parent.parent.parent / "scripts" / "build_next_testnet_dry_run_no_submit_payload_plan_v1.py"),
        "--candidate-artifact", p,
        "--output", out,
        "--json",
    ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    proc.communicate()
    assert proc.returncode in [0, 1]
    assert os.path.exists(out)
