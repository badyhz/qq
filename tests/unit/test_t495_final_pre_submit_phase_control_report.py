import json
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scripts.generate_final_pre_submit_phase_control_report_v1 import generate_phase_control, write_json


SCRIPT = Path(__file__).parent.parent.parent / "scripts" / "generate_final_pre_submit_phase_control_report_v1.py"


def t491(verdict="PASS"):
    return {"verdict": verdict}


def t492(verdict="PASS"):
    return {"verdict": verdict}


def t493(verdict="PASS", safe_partial=False):
    return {"verdict": verdict, "safe_partial": safe_partial}


def t494(verdict="GO"):
    return {"verdict": verdict}


def test_t495_pass():
    report = generate_phase_control(t491("PASS"), t492("PASS"), t493("PASS"), t494("GO"))
    assert report["ok"] is True
    assert report["verdict"] == "PASS"


def test_t495_pass_with_safe_partial_t493():
    report = generate_phase_control(t491("PASS"), t492("PASS"), t493("PARTIAL", True), t494("GO"))
    assert report["ok"] is True
    assert report["verdict"] == "PASS"
    assert "T493_SAFE_PARTIAL_ACCEPTED_WITH_HUMAN_REVIEW" in report["warnings"]


def test_t495_partial():
    report = generate_phase_control(t491("PASS"), t492("PASS"), t493("PARTIAL", False), t494("WAIT"))
    assert report["ok"] is False
    assert report["verdict"] == "PARTIAL"


def test_t495_fail():
    report = generate_phase_control(t491("FAIL"), t492("FAIL"), t493("FAIL", False), t494("NO_GO"))
    assert report["ok"] is False
    assert report["verdict"] == "FAIL"


def test_t495_forbidden_actions_present():
    report = generate_phase_control(t491("PASS"), t492("PASS"), t493("PASS"), t494("GO"))
    for action in ["TESTNET_SUBMIT", "REAL_SUBMIT", "SUBMIT_ORDER", "CANCEL_ORDER", "FLATTEN_POSITION"]:
        assert action in report["forbidden_next_actions"]


def test_t495_cli_smoke(tmp_path):
    p1 = tmp_path / "t491.json"
    p2 = tmp_path / "t492.json"
    p3 = tmp_path / "t493.json"
    p4 = tmp_path / "t494.json"
    out = tmp_path / "out.json"
    write_json(str(p1), t491("PASS"))
    write_json(str(p2), t492("PASS"))
    write_json(str(p3), t493("PASS", False))
    write_json(str(p4), t494("GO"))
    proc = subprocess.Popen(
        [sys.executable, str(SCRIPT), "--inputs", str(p1), str(p2), str(p3), str(p4), "--output", str(out), "--json"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    proc.communicate()
    assert proc.returncode in [0, 1]
    assert os.path.exists(out)
    loaded = json.loads(out.read_text(encoding="utf-8"))
    assert loaded["phase"] == "final_pre_testnet_submit_control"
