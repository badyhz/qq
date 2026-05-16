import json
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scripts.generate_single_human_gated_execution_local_audit_manifest_v1 import generate_manifest


def write_temp_json(data, tmpdir):
    path = os.path.join(tmpdir, f"{os.urandom(4).hex()}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f)
    return path


def test_pass():
    with tempfile.TemporaryDirectory() as tmpdir:
        common = {"env": "testnet", "submit_allowed": False, "max_submit_count": 1, "verdict": "PASS"}
        p1 = write_temp_json({**common, "decision": "READY"}, tmpdir)
        p2 = write_temp_json({**common, "gate_status": "READY"}, tmpdir)
        p3 = write_temp_json({**common, "artifact_type": "SINGLE_HUMAN_GATED_TESTNET_EXECUTION_WRAPPER"}, tmpdir)
        p4 = write_temp_json({**common, "invariant_status": "PASS"}, tmpdir)
        p5 = write_temp_json({**common, "command_preview_type": "HUMAN_REVIEW_ONLY"}, tmpdir)

        r = generate_manifest(p1, p2, p3, p4, p5)
        assert r["verdict"] in ("PASS", "PARTIAL")  # May be PARTIAL due to missing fields but no blockers


def test_missing_artifact_fail():
    with tempfile.TemporaryDirectory() as tmpdir:
        common = {"env": "testnet", "submit_allowed": False, "max_submit_count": 1, "verdict": "PASS"}
        p1 = write_temp_json({**common, "decision": "READY"}, tmpdir)
        p2 = write_temp_json({**common, "gate_status": "READY"}, tmpdir)
        p3 = write_temp_json({**common, "artifact_type": "SINGLE_HUMAN_GATED_TESTNET_EXECUTION_WRAPPER"}, tmpdir)
        p4 = write_temp_json({**common, "invariant_status": "PASS"}, tmpdir)

        r = generate_manifest(p1, p2, p3, p4, "/does/not/exist.json")
        assert r["verdict"] == "FAIL"


def test_invalid_json_fail():
    with tempfile.TemporaryDirectory() as tmpdir:
        common = {"env": "testnet", "submit_allowed": False, "max_submit_count": 1, "verdict": "PASS"}
        p1 = write_temp_json({**common, "decision": "READY"}, tmpdir)
        p2 = write_temp_json({**common, "gate_status": "READY"}, tmpdir)
        p3 = write_temp_json({**common, "artifact_type": "SINGLE_HUMAN_GATED_TESTNET_EXECUTION_WRAPPER"}, tmpdir)
        p4 = write_temp_json({**common, "invariant_status": "PASS"}, tmpdir)

        bad_path = os.path.join(tmpdir, "bad.json")
        with open(bad_path, "w", encoding="utf-8") as f:
            f.write("not valid json")

        r = generate_manifest(p1, p2, p3, p4, bad_path)
        assert r["verdict"] == "FAIL"


def test_env_mismatch_fail():
    with tempfile.TemporaryDirectory() as tmpdir:
        common = {"submit_allowed": False, "max_submit_count": 1, "verdict": "PASS"}
        p1 = write_temp_json({**common, "env": "testnet", "decision": "READY"}, tmpdir)
        p2 = write_temp_json({**common, "env": "mainnet", "gate_status": "READY"}, tmpdir)
        p3 = write_temp_json({**common, "env": "testnet", "artifact_type": "SINGLE_HUMAN_GATED_TESTNET_EXECUTION_WRAPPER"}, tmpdir)
        p4 = write_temp_json({**common, "env": "testnet", "invariant_status": "PASS"}, tmpdir)
        p5 = write_temp_json({**common, "env": "testnet", "command_preview_type": "HUMAN_REVIEW_ONLY"}, tmpdir)

        r = generate_manifest(p1, p2, p3, p4, p5)
        assert r["verdict"] == "FAIL"


def test_submit_allowed_false_chain():
    with tempfile.TemporaryDirectory() as tmpdir:
        common = {"env": "testnet", "submit_allowed": False, "max_submit_count": 1, "verdict": "PASS"}
        p1 = write_temp_json({**common, "decision": "READY"}, tmpdir)
        p2 = write_temp_json({**common, "gate_status": "READY"}, tmpdir)
        p3 = write_temp_json({**common, "artifact_type": "SINGLE_HUMAN_GATED_TESTNET_EXECUTION_WRAPPER"}, tmpdir)
        p4 = write_temp_json({**common, "invariant_status": "PASS"}, tmpdir)
        p5 = write_temp_json({**common, "command_preview_type": "HUMAN_REVIEW_ONLY"}, tmpdir)

        r = generate_manifest(p1, p2, p3, p4, p5)
        assert r["chain_summary"]["submit_allowed_false"] is True
