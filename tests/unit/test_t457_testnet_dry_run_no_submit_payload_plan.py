import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scripts.build_testnet_dry_run_no_submit_payload_plan_v1 import (
    REQUIRED_BLOCKED_ACTIONS,
    build_payload_plan,
    load_json,
    write_json,
)


def valid_t456() -> dict:
    return {
        "ok": True,
        "final_decision": "READY_FOR_TESTNET_DRY_RUN_NO_SUBMIT_PAYLOAD_PLAN",
    }


def valid_candidate() -> dict:
    return {
        "candidate_id": "dryrun-candidate-001",
        "symbol": "BTCUSDT",
        "side": "BUY",
        "quantity": "0.001",
        "order_type": "MARKET",
        "dry_run_only": True,
    }


def test_valid_candidate_pass(tmp_path):
    report = build_payload_plan(valid_t456(), valid_candidate())
    assert report["ok"] is True
    assert report["payload_plan_status"] == "NO_SUBMIT_PAYLOAD_PLAN_READY"
    assert report["final_decision"] == "READY_FOR_TESTNET_DRY_RUN_NO_SUBMIT_RUNNER_GUARD"


def test_t456_blocked_fail(tmp_path):
    t456 = valid_t456()
    t456["ok"] = False
    report = build_payload_plan(t456, valid_candidate())
    assert report["ok"] is False
    assert "MODE_PACKET_NOT_READY" in report["violations"]


def test_dry_run_only_false_fail(tmp_path):
    c = valid_candidate()
    c["dry_run_only"] = False
    report = build_payload_plan(valid_t456(), c)
    assert report["ok"] is False
    assert "CANDIDATE_NOT_DRY_RUN_ONLY" in report["violations"]


def test_missing_symbol_fail(tmp_path):
    c = valid_candidate()
    c["symbol"] = ""
    report = build_payload_plan(valid_t456(), c)
    assert report["ok"] is False
    assert "SYMBOL_MISSING" in report["violations"]


def test_invalid_side_fail(tmp_path):
    c = valid_candidate()
    c["side"] = "HOLD"
    report = build_payload_plan(valid_t456(), c)
    assert report["ok"] is False
    assert "INVALID_SIDE" in report["violations"]


def test_missing_quantity_fail(tmp_path):
    c = valid_candidate()
    c["quantity"] = ""
    report = build_payload_plan(valid_t456(), c)
    assert report["ok"] is False
    assert "QUANTITY_MISSING" in report["violations"]


def test_never_allows_submit_cancel_flatten(tmp_path):
    report = build_payload_plan(valid_t456(), valid_candidate())
    for blocked in REQUIRED_BLOCKED_ACTIONS:
        assert blocked not in report["allowed_actions"]
        assert blocked in report["blocked_actions"]


def test_invalid_json(tmp_path):
    p1 = str(tmp_path / "t456.json")
    p2 = str(tmp_path / "candidate.json")
    write_json(p1, valid_t456())
    with open(p2, "w", encoding="utf-8") as f:
        f.write("invalid json")

    report = build_payload_plan(load_json(p1), load_json(p2))
    assert report["ok"] is False


def test_missing_file(tmp_path):
    p1 = str(tmp_path / "t456.json")
    p2 = str(tmp_path / "missing_candidate.json")
    write_json(p1, valid_t456())

    report = build_payload_plan(load_json(p1), load_json(p2))
    assert report["ok"] is False


def test_cli_smoke(tmp_path):
    p1 = str(tmp_path / "t456.json")
    p2 = str(tmp_path / "candidate.json")
    out = str(tmp_path / "out.json")
    write_json(p1, valid_t456())
    write_json(p2, valid_candidate())

    proc = subprocess.Popen(
        [
            sys.executable,
            str(Path(__file__).parent.parent.parent / "scripts" / "build_testnet_dry_run_no_submit_payload_plan_v1.py"),
            "--mode-packet",
            p1,
            "--candidate-input",
            p2,
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
