import json
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scripts.generate_testnet_submit_manual_approval_gate_packet_v1 import generate_gate_packet, write_json


SCRIPT = Path(__file__).parent.parent.parent / "scripts" / "generate_testnet_submit_manual_approval_gate_packet_v1.py"


def test_t491_pass(tmp_path):
    p = tmp_path / "t490.json"
    write_json(
        str(p),
        {
            "ok": True,
            "final_decision": "READY_FOR_TESTNET_SUBMIT_READINESS_REVIEW",
            "blockers": [],
        },
    )
    report = generate_gate_packet([str(p)])
    assert report["ok"] is True
    assert report["verdict"] == "PASS"
    assert report["submit_executed"] is False


def test_t491_partial(tmp_path):
    p = tmp_path / "a.json"
    write_json(
        str(p),
        {
            "ok": False,
            "final_decision": "READY_FOR_TESTNET_SUBMIT_READINESS_REVIEW",
            "blockers": ["X"],
        },
    )
    report = generate_gate_packet([str(p)])
    assert report["ok"] is False
    assert report["verdict"] == "PARTIAL"


def test_t491_fail(tmp_path):
    p = tmp_path / "a.json"
    write_json(str(p), {"ok": True, "final_decision": "OTHER", "blockers": []})
    report = generate_gate_packet([str(p)])
    assert report["verdict"] == "FAIL"
    assert "PRIOR_READINESS_RECOMMENDATION_NOT_PASS" in report["blocking_reasons"]


def test_t491_cli_smoke(tmp_path):
    inp = tmp_path / "in.json"
    out = tmp_path / "out.json"
    write_json(str(inp), {"ok": True, "final_decision": "READY_FOR_TESTNET_SUBMIT_READINESS_REVIEW", "blockers": []})
    proc = subprocess.Popen(
        [sys.executable, str(SCRIPT), "--inputs", str(inp), "--output", str(out), "--json"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    proc.communicate()
    assert proc.returncode in [0, 1]
    assert os.path.exists(out)
    loaded = json.loads(out.read_text(encoding="utf-8"))
    assert loaded["phase"] == "testnet_submit_manual_approval_gate"
