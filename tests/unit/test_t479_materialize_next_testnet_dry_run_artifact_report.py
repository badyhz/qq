import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scripts.materialize_next_testnet_dry_run_artifact_report_v1 import (
    REQUIRED_BLOCKED_ACTIONS,
    materialize_artifact_report,
    load_json,
    write_json,
)


def valid_t478():
    return {
        "ok": True,
        "payload_plan_status": "NEXT_NO_SUBMIT_PAYLOAD_PLAN_READY",
        "planned_payload": {
            "candidate_id": "next-dryrun-candidate-001",
            "symbol": "BTCUSDT",
            "side": "BUY",
            "quantity": "0.001",
            "order_type": "MARKET",
            "dry_run_only": True,
            "artifact_only": True,
            "payload_plan_version": "v1",
            "submit_enabled": False,
            "cancel_enabled": False,
            "flatten_enabled": False,
            "exchange_api_calls_enabled": False,
        },
    }


def test_valid_t478_materialized_with_digest(tmp_path):
    r = materialize_artifact_report(valid_t478())
    assert r["ok"] is True
    assert r["payload_digest"]


def test_t478_blocked_fail(tmp_path):
    t478 = valid_t478(); t478["ok"] = False
    r = materialize_artifact_report(t478)
    assert r["ok"] is False
    assert "PAYLOAD_PLAN_NOT_READY" in r["violations"]


def test_missing_planned_payload_fail(tmp_path):
    t478 = valid_t478(); t478.pop("planned_payload")
    r = materialize_artifact_report(t478)
    assert "PLANNED_PAYLOAD_MISSING" in r["violations"]


def test_submit_enabled_true_fail(tmp_path):
    t478 = valid_t478(); t478["planned_payload"]["submit_enabled"] = True
    r = materialize_artifact_report(t478)
    assert "SUBMIT_ENABLED" in r["violations"]


def test_digest_deterministic(tmp_path):
    r1 = materialize_artifact_report(valid_t478())
    r2 = materialize_artifact_report(valid_t478())
    assert r1["payload_digest"] == r2["payload_digest"]


def test_artifact_report_no_submit_cancel_flatten(tmp_path):
    r = materialize_artifact_report(valid_t478())
    assert r["artifact_report"]["submit_attempted"] is False
    assert r["artifact_report"]["cancel_attempted"] is False
    assert r["artifact_report"]["flatten_attempted"] is False


def test_never_allows_blocked_actions(tmp_path):
    r = materialize_artifact_report(valid_t478())
    for b in REQUIRED_BLOCKED_ACTIONS:
        assert b not in r["allowed_actions"]
        assert b in r["blocked_actions"]


def test_invalid_json(tmp_path):
    p = str(tmp_path / "bad.json")
    with open(p, "w", encoding="utf-8") as f:
        f.write("bad")
    r = materialize_artifact_report(load_json(p))
    assert r["ok"] is False


def test_missing_file(tmp_path):
    p = str(tmp_path / "missing.json")
    r = materialize_artifact_report(load_json(p))
    assert r["ok"] is False


def test_cli_smoke(tmp_path):
    p = str(tmp_path / "t478.json")
    out = str(tmp_path / "out.json")
    write_json(p, valid_t478())
    proc = subprocess.Popen([
        sys.executable,
        str(Path(__file__).parent.parent.parent / "scripts" / "materialize_next_testnet_dry_run_artifact_report_v1.py"),
        "--payload-plan", p,
        "--output", out,
        "--json",
    ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    proc.communicate()
    assert proc.returncode in [0, 1]
    assert os.path.exists(out)
