import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scripts.generate_post_submit_readonly_verification_packet_v1 import generate_verification_packet, write_json


SCRIPT = Path(__file__).parent.parent.parent / "scripts" / "generate_post_submit_readonly_verification_packet_v1.py"


def dry_run_result():
    return {"submit_attempted": False, "submit_executed": False, "verdict": "DRY_RUN"}


def submitted_result():
    return {"submit_attempted": True, "submit_executed": True, "verdict": "SUBMITTED"}


def snap(kind, healthy=True):
    base = {"snapshot_type": kind}
    if kind == "protection":
        base["protection_healthy"] = healthy
    return base


def test_t499_dry_run_partial_or_pass():
    r = generate_verification_packet(dry_run_result(), [])
    assert r["ok"] is True
    assert r["verdict"] == "PARTIAL"
    assert r["submit_result_summary"]["submit_executed"] is False


def test_t499_submitted_no_snapshots_partial():
    r = generate_verification_packet(submitted_result(), [])
    assert r["ok"] is True
    assert r["verdict"] == "PARTIAL"


def test_t499_submitted_healthy_pass():
    r = generate_verification_packet(submitted_result(), [snap("position"), snap("protection", True)])
    assert r["ok"] is True
    assert r["verdict"] == "PASS"


def test_t499_missing_protection_fail():
    r = generate_verification_packet(submitted_result(), [snap("position")])
    assert r["ok"] is False
    assert r["verdict"] == "FAIL"
    assert "PROTECTION_SNAPSHOT_MISSING" in r["blocking_reasons"]


def test_t499_cli_smoke(tmp_path):
    p1 = tmp_path / "submit.json"
    p2 = tmp_path / "protection.json"
    out = tmp_path / "out.json"
    write_json(str(p1), submitted_result())
    write_json(str(p2), snap("protection", True))
    proc = subprocess.Popen(
        [sys.executable, str(SCRIPT), "--inputs", str(p1), str(p2), "--output", str(out), "--json"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    proc.communicate()
    assert proc.returncode in [0, 1]
    assert os.path.exists(out)
