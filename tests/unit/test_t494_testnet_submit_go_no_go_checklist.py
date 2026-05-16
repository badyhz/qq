import json
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scripts.generate_testnet_submit_go_no_go_checklist_v1 import generate_checklist, write_json


SCRIPT = Path(__file__).parent.parent.parent / "scripts" / "generate_testnet_submit_go_no_go_checklist_v1.py"


def t491(verdict="PASS"):
    return {"verdict": verdict}


def t492(verdict="PASS"):
    return {"verdict": verdict}


def t493(verdict="PASS", safe_partial=False):
    return {"verdict": verdict, "safe_partial": safe_partial}


def test_t494_go():
    report = generate_checklist(t491("PASS"), t492("PASS"), t493("PASS"))
    assert report["ok"] is True
    assert report["verdict"] == "GO"


def test_t494_go_safe_partial_delta():
    report = generate_checklist(t491("PASS"), t492("PASS"), t493("PARTIAL", True))
    assert report["verdict"] == "GO"
    assert "RISK_DELTA_PARTIAL_REQUIRES_HUMAN_EXPLANATION" in report["warnings"]


def test_t494_wait_on_unsafe_partial_delta():
    report = generate_checklist(t491("PASS"), t492("PASS"), t493("PARTIAL", False))
    assert report["ok"] is False
    assert report["verdict"] == "WAIT"


def test_t494_no_go_on_failures():
    report = generate_checklist(t491("FAIL"), t492("PASS"), t493("PASS"))
    assert report["ok"] is False
    assert report["verdict"] == "NO_GO"


def test_t494_template_is_dry_only():
    report = generate_checklist(t491("PASS"), t492("PASS"), t493("PASS"))
    assert "DRY_TEMPLATE_ONLY" in report["next_command_template"]
    assert "API_KEY" not in report["next_command_template"]


def test_t494_cli_smoke(tmp_path):
    p1 = tmp_path / "t491.json"
    p2 = tmp_path / "t492.json"
    p3 = tmp_path / "t493.json"
    out = tmp_path / "out.json"
    write_json(str(p1), t491("PASS"))
    write_json(str(p2), t492("PASS"))
    write_json(str(p3), t493("PASS"))
    proc = subprocess.Popen(
        [sys.executable, str(SCRIPT), "--inputs", str(p1), str(p2), str(p3), "--output", str(out), "--json"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    proc.communicate()
    assert proc.returncode in [0, 1]
    assert os.path.exists(out)
    loaded = json.loads(out.read_text(encoding="utf-8"))
    assert "checklist" in loaded
