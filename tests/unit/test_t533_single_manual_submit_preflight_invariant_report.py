import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scripts.generate_single_manual_submit_preflight_invariant_report_v1 import generate_report


def packet():
    return {
        "verdict": "PASS",
        "env": "testnet",
        "symbol": "BTCUSDT",
        "side": "BUY",
        "quantity": "0.01",
        "submit_allowed": False,
        "max_submit_count": 1,
        "dry_run_command": "python3 run.py --dry-run",
        "manual_submit_command_template": "python3 run.py --allow-testnet-submit --confirm-token <TOKEN> --env testnet",
    }


def checklist(v="PASS"):
    return {"verdict": v}


def test_pass():
    r = generate_report(packet(), checklist("PASS"))
    assert r["verdict"] == "PASS"


def test_missing_token_gate_fail():
    p = packet()
    p["manual_submit_command_template"] = "python3 run.py --env testnet"
    r = generate_report(p, checklist("PASS"))
    assert r["verdict"] == "FAIL"


def test_live_marker_fail():
    p = packet()
    p["manual_submit_command_template"] = "python3 run.py --allow-testnet-submit --confirm-token x --env testnet --live"
    r = generate_report(p, checklist("PASS"))
    assert r["verdict"] == "FAIL"


def test_checklist_partial_partial():
    r = generate_report(packet(), checklist("PARTIAL"))
    assert r["verdict"] == "PARTIAL"


def test_quantity_invalid_fail():
    p = packet()
    p["quantity"] = "0"
    r = generate_report(p, checklist("PASS"))
    assert r["verdict"] == "FAIL"
