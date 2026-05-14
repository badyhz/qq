import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scripts.verify_testnet_dry_run_materialized_payload_consistency_v1 import (
    REQUIRED_BLOCKED_ACTIONS,
    verify_payload_consistency,
    load_json,
    write_json,
)


def digest(payload):
    return hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()


def valid_t466():
    return {"ok": True, "final_decision": "READY_FOR_TESTNET_DRY_RUN_MATERIALIZED_PAYLOAD_CONSISTENCY_REVIEW"}


def valid_t462():
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
        "materialization_status": "NO_SUBMIT_PAYLOAD_MATERIALIZED",
        "materialized_payload": payload,
        "payload_digest": digest(payload),
    }


def test_valid_t466_t462_pass(tmp_path):
    r = verify_payload_consistency(valid_t466(), valid_t462())
    assert r["ok"] is True
    assert r["consistency_status"] == "MATERIALIZED_PAYLOAD_CONSISTENCY_VERIFIED"


def test_digest_mismatch_fail(tmp_path):
    t462 = valid_t462(); t462["payload_digest"] = "bad"
    r = verify_payload_consistency(valid_t466(), t462)
    assert r["ok"] is False
    assert "PAYLOAD_DIGEST_MISMATCH" in r["violations"]


def test_missing_digest_fail(tmp_path):
    t462 = valid_t462(); t462["payload_digest"] = ""
    r = verify_payload_consistency(valid_t466(), t462)
    assert r["ok"] is False
    assert "PAYLOAD_DIGEST_MISSING" in r["violations"]


def test_dry_run_only_false_fail(tmp_path):
    t462 = valid_t462(); t462["materialized_payload"]["dry_run_only"] = False
    r = verify_payload_consistency(valid_t466(), t462)
    assert r["ok"] is False
    assert "DRY_RUN_ONLY_NOT_CONFIRMED" in r["violations"]


def test_artifact_only_false_fail(tmp_path):
    t462 = valid_t462(); t462["materialized_payload"]["artifact_only"] = False
    r = verify_payload_consistency(valid_t466(), t462)
    assert r["ok"] is False
    assert "ARTIFACT_ONLY_NOT_CONFIRMED" in r["violations"]


def test_submit_attempted_true_fail(tmp_path):
    t462 = valid_t462(); t462["materialized_payload"]["submit_attempted"] = True
    r = verify_payload_consistency(valid_t466(), t462)
    assert r["ok"] is False
    assert "EXCHANGE_OR_SUBMIT_ATTEMPT_DETECTED" in r["violations"]


def test_t466_blocked_fail(tmp_path):
    t466 = valid_t466(); t466["ok"] = False
    r = verify_payload_consistency(t466, valid_t462())
    assert r["ok"] is False
    assert "REVIEW_PACKET_NOT_READY" in r["violations"]


def test_t462_blocked_fail(tmp_path):
    t462 = valid_t462(); t462["ok"] = False
    r = verify_payload_consistency(valid_t466(), t462)
    assert r["ok"] is False
    assert "MATERIALIZED_PAYLOAD_NOT_READY" in r["violations"]


def test_never_allows_blocked_actions(tmp_path):
    r = verify_payload_consistency(valid_t466(), valid_t462())
    for b in REQUIRED_BLOCKED_ACTIONS:
        assert b not in r["allowed_actions"]
        assert b in r["blocked_actions"]


def test_invalid_json(tmp_path):
    p1 = str(tmp_path / "t466.json")
    p2 = str(tmp_path / "t462.json")
    write_json(p1, valid_t466())
    with open(p2, "w", encoding="utf-8") as f:
        f.write("bad")
    r = verify_payload_consistency(load_json(p1), load_json(p2))
    assert r["ok"] is False


def test_missing_file(tmp_path):
    p1 = str(tmp_path / "t466.json")
    p2 = str(tmp_path / "missing.json")
    write_json(p1, valid_t466())
    r = verify_payload_consistency(load_json(p1), load_json(p2))
    assert r["ok"] is False


def test_cli_smoke(tmp_path):
    p1 = str(tmp_path / "t466.json")
    p2 = str(tmp_path / "t462.json")
    out = str(tmp_path / "out.json")
    write_json(p1, valid_t466())
    write_json(p2, valid_t462())
    proc = subprocess.Popen([
        sys.executable,
        str(Path(__file__).parent.parent.parent / "scripts" / "verify_testnet_dry_run_materialized_payload_consistency_v1.py"),
        "--review-packet", p1,
        "--materialized-payload", p2,
        "--output", out,
        "--json",
    ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    proc.communicate()
    assert proc.returncode in [0, 1]
    assert os.path.exists(out)
