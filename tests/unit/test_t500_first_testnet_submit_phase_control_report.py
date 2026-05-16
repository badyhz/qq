import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scripts.generate_first_testnet_submit_phase_control_report_v1 import generate_phase_control, write_json


SCRIPT = Path(__file__).parent.parent.parent / "scripts" / "generate_first_testnet_submit_phase_control_report_v1.py"


def t496(v="PASS"):
    return {"verdict": v}


def t497(v="PASS"):
    return {"verdict": v}


def t498(v="DRY_RUN", attempted=False, executed=False):
    return {"verdict": v, "submit_attempted": attempted, "submit_executed": executed}


def t499(v="PARTIAL"):
    return {"verdict": v}


def test_t500_pass_ready_for_manual_not_submitted():
    r = generate_phase_control(t496("PASS"), t497("PASS"), t498("DRY_RUN", False, False), t499("PARTIAL"))
    assert r["ok"] is True
    assert r["verdict"] == "PASS"
    assert r["submit_executed"] is False
    assert "ready_for_manual_testnet_submit" in r["allowed_next_actions"]


def test_t500_pass_when_submitted_requires_t499_pass():
    r = generate_phase_control(t496("PASS"), t497("PASS"), t498("SUBMITTED", True, True), t499("PASS"))
    assert r["ok"] is True
    assert r["verdict"] == "PASS"


def test_t500_fail_submitted_but_t499_not_pass():
    r = generate_phase_control(t496("PASS"), t497("PASS"), t498("SUBMITTED", True, True), t499("PARTIAL"))
    assert r["ok"] is False
    assert r["verdict"] == "FAIL"
    assert "T499_NOT_PASS_FOR_SUBMITTED_FLOW" in r["blockers"]


def test_t500_fail_mainnet_evidence():
    r = generate_phase_control({"verdict": "PASS", "note": "api.binance.com"}, t497("PASS"), t498("DRY_RUN", False, False), t499("PARTIAL"))
    assert r["ok"] is False
    assert r["verdict"] == "FAIL"
    assert "MAINNET_OR_LIVE_EVIDENCE_DETECTED" in r["blockers"]


def test_t500_cli_smoke(tmp_path):
    p1 = tmp_path / "t496.json"
    p2 = tmp_path / "t497.json"
    p3 = tmp_path / "t498.json"
    p4 = tmp_path / "t499.json"
    out = tmp_path / "out.json"
    write_json(str(p1), t496("PASS"))
    write_json(str(p2), t497("PASS"))
    write_json(str(p3), t498("DRY_RUN", False, False))
    write_json(str(p4), t499("PARTIAL"))
    proc = subprocess.Popen(
        [sys.executable, str(SCRIPT), "--inputs", str(p1), str(p2), str(p3), str(p4), "--output", str(out), "--json"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    proc.communicate()
    assert proc.returncode in [0, 1]
    assert os.path.exists(out)
