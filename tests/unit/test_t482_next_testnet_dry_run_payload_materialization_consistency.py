import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scripts.verify_next_testnet_dry_run_payload_materialization_consistency_v1 import (
    REQUIRED_BLOCKED_ACTIONS,
    verify_consistency,
    load_json,
    write_json,
)


def sha(payload):
    return hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()


def valid_t481():
    return {"ok": True, "final_decision": "READY_FOR_NEXT_TESTNET_DRY_RUN_PAYLOAD_MATERIALIZATION_CONSISTENCY_REVIEW"}


def valid_t479():
    payload = {
        "dry_run_only": True,
        "artifact_only": True,
        "exchange_api_call_attempted": False,
        "submit_attempted": False,
        "cancel_attempted": False,
        "flatten_attempted": False,
    }
    return {
        "ok": True,
        "materialization_status": "NEXT_ARTIFACT_ONLY_MATERIALIZATION_REPORTED",
        "materialized_payload": payload,
        "payload_digest": sha(payload),
        "artifact_report": {
            "status": "NEXT_ARTIFACT_ONLY_NO_SUBMIT_MATERIALIZED",
            "exchange_api_call_attempted": False,
            "submit_attempted": False,
            "cancel_attempted": False,
            "flatten_attempted": False,
        },
    }


def test_valid_t481_t479_pass(tmp_path):
    r = verify_consistency(valid_t481(), valid_t479())
    assert r["ok"] is True
    assert r["consistency_status"] == "NEXT_PAYLOAD_MATERIALIZATION_CONSISTENCY_VERIFIED"


def test_digest_mismatch_fail(tmp_path):
    t479 = valid_t479(); t479["payload_digest"] = "bad"
    r = verify_consistency(valid_t481(), t479)
    assert "PAYLOAD_DIGEST_MISMATCH" in r["violations"]


def test_missing_digest_fail(tmp_path):
    t479 = valid_t479(); t479["payload_digest"] = ""
    r = verify_consistency(valid_t481(), t479)
    assert "PAYLOAD_DIGEST_MISSING" in r["violations"]


def test_dry_run_only_false_fail(tmp_path):
    t479 = valid_t479(); t479["materialized_payload"]["dry_run_only"] = False
    r = verify_consistency(valid_t481(), t479)
    assert "DRY_RUN_ONLY_NOT_CONFIRMED" in r["violations"]


def test_artifact_only_false_fail(tmp_path):
    t479 = valid_t479(); t479["materialized_payload"]["artifact_only"] = False
    r = verify_consistency(valid_t481(), t479)
    assert "ARTIFACT_ONLY_NOT_CONFIRMED" in r["violations"]


def test_artifact_report_status_wrong_fail(tmp_path):
    t479 = valid_t479(); t479["artifact_report"]["status"] = "BAD"
    r = verify_consistency(valid_t481(), t479)
    assert "ARTIFACT_REPORT_NOT_CONFIRMED" in r["violations"]


def test_submit_attempted_true_fail(tmp_path):
    t479 = valid_t479(); t479["materialized_payload"]["submit_attempted"] = True
    r = verify_consistency(valid_t481(), t479)
    assert "EXCHANGE_OR_SUBMIT_ATTEMPT_DETECTED" in r["violations"]


def test_t481_blocked_fail(tmp_path):
    t481 = valid_t481(); t481["ok"] = False
    r = verify_consistency(t481, valid_t479())
    assert "REVIEW_PACKET_NOT_READY" in r["violations"]


def test_t479_blocked_fail(tmp_path):
    t479 = valid_t479(); t479["ok"] = False
    r = verify_consistency(valid_t481(), t479)
    assert "MATERIALIZATION_REPORT_NOT_READY" in r["violations"]


def test_never_allows_blocked_actions(tmp_path):
    r = verify_consistency(valid_t481(), valid_t479())
    for b in REQUIRED_BLOCKED_ACTIONS:
        assert b not in r["allowed_actions"]
        assert b in r["blocked_actions"]


def test_invalid_json(tmp_path):
    p1 = str(tmp_path / "t481.json")
    p2 = str(tmp_path / "t479.json")
    write_json(p1, valid_t481())
    with open(p2, "w", encoding="utf-8") as f:
        f.write("bad")
    r = verify_consistency(load_json(p1), load_json(p2))
    assert r["ok"] is False


def test_missing_file(tmp_path):
    p1 = str(tmp_path / "t481.json")
    p2 = str(tmp_path / "missing.json")
    write_json(p1, valid_t481())
    r = verify_consistency(load_json(p1), load_json(p2))
    assert r["ok"] is False


def test_cli_smoke(tmp_path):
    p1 = str(tmp_path / "t481.json")
    p2 = str(tmp_path / "t479.json")
    out = str(tmp_path / "out.json")
    write_json(p1, valid_t481())
    write_json(p2, valid_t479())
    proc = subprocess.Popen([
        sys.executable,
        str(Path(__file__).parent.parent.parent / "scripts" / "verify_next_testnet_dry_run_payload_materialization_consistency_v1.py"),
        "--review-packet", p1,
        "--materialization-report", p2,
        "--output", out,
        "--json",
    ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    proc.communicate()
    assert proc.returncode in [0, 1]
    assert os.path.exists(out)
