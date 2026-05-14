import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scripts.materialize_testnet_dry_run_no_submit_payload_v1 import (
    REQUIRED_BLOCKED_ACTIONS,
    materialize_payload,
    load_json,
    write_json,
)


def valid_t461() -> dict:
    return {
        "ok": True,
        "final_decision": "READY_FOR_TESTNET_DRY_RUN_NO_SUBMIT_PAYLOAD_MATERIALIZATION",
        "safety_flags": {
            "exchange_api_calls_allowed": False,
            "testnet_submit_allowed": False,
            "real_submit_allowed": False,
            "submit_order_allowed": False,
            "cancel_order_allowed": False,
            "flatten_position_allowed": False,
            "submit_attempted": False,
            "cancel_attempted": False,
            "flatten_attempted": False,
        },
    }


def valid_t457() -> dict:
    return {
        "ok": True,
        "payload_plan_status": "NO_SUBMIT_PAYLOAD_PLAN_READY",
        "planned_payload": {
            "candidate_id": "dryrun-candidate-001",
            "symbol": "BTCUSDT",
            "side": "BUY",
            "quantity": "0.001",
            "order_type": "MARKET",
        },
        "candidate_summary": {"candidate_id": "dryrun-candidate-001"},
        "safety_flags": {
            "exchange_api_calls_allowed": False,
            "testnet_submit_allowed": False,
            "real_submit_allowed": False,
            "submit_order_allowed": False,
            "cancel_order_allowed": False,
            "flatten_position_allowed": False,
            "submit_attempted": False,
            "cancel_attempted": False,
            "flatten_attempted": False,
        },
    }


def test_valid_inputs_materialized_with_digest(tmp_path):
    report = materialize_payload(valid_t461(), valid_t457())
    assert report["ok"] is True
    assert report["materialization_status"] == "NO_SUBMIT_PAYLOAD_MATERIALIZED"
    assert report["materialized_payload"]["artifact_only"] is True
    assert report["payload_digest"]


def test_t461_blocked_fail(tmp_path):
    t461 = valid_t461()
    t461["ok"] = False
    report = materialize_payload(t461, valid_t457())
    assert report["ok"] is False
    assert "EXECUTION_PACKET_NOT_READY" in report["violations"]


def test_t457_blocked_fail(tmp_path):
    t457 = valid_t457()
    t457["ok"] = False
    report = materialize_payload(valid_t461(), t457)
    assert report["ok"] is False
    assert "PAYLOAD_PLAN_NOT_READY" in report["violations"]


def test_missing_planned_payload_fail(tmp_path):
    t457 = valid_t457()
    t457.pop("planned_payload")
    report = materialize_payload(valid_t461(), t457)
    assert report["ok"] is False
    assert "PLANNED_PAYLOAD_MISSING" in report["violations"]


def test_digest_deterministic(tmp_path):
    r1 = materialize_payload(valid_t461(), valid_t457())
    r2 = materialize_payload(valid_t461(), valid_t457())
    assert r1["payload_digest"] == r2["payload_digest"]


def test_never_allows_blocked_actions(tmp_path):
    report = materialize_payload(valid_t461(), valid_t457())
    for b in REQUIRED_BLOCKED_ACTIONS:
        assert b not in report["allowed_actions"]
        assert b in report["blocked_actions"]


def test_invalid_json(tmp_path):
    p1 = str(tmp_path / "t461.json")
    p2 = str(tmp_path / "t457.json")
    write_json(p1, valid_t461())
    with open(p2, "w", encoding="utf-8") as f:
        f.write("invalid json")
    report = materialize_payload(load_json(p1), load_json(p2))
    assert report["ok"] is False


def test_missing_file(tmp_path):
    p1 = str(tmp_path / "t461.json")
    p2 = str(tmp_path / "missing.json")
    write_json(p1, valid_t461())
    report = materialize_payload(load_json(p1), load_json(p2))
    assert report["ok"] is False


def test_cli_smoke(tmp_path):
    p1 = str(tmp_path / "t461.json")
    p2 = str(tmp_path / "t457.json")
    out = str(tmp_path / "out.json")
    write_json(p1, valid_t461())
    write_json(p2, valid_t457())
    proc = subprocess.Popen(
        [
            sys.executable,
            str(Path(__file__).parent.parent.parent / "scripts" / "materialize_testnet_dry_run_no_submit_payload_v1.py"),
            "--execution-packet",
            p1,
            "--payload-plan",
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
