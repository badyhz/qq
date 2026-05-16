import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scripts.compare_repeat_small_batch_dry_run_plans_v1 import compare_plans


def plan(cmds, submit_allowed=False):
    return {"dry_run_commands": cmds, "submit_allowed": submit_allowed}


def test_t523_pass():
    c = ["python3 run.py --env testnet --dry-run"]
    r = compare_plans(plan(c), plan(c))
    assert r["verdict"] == "PASS"


def test_t523_command_count_drift_partial():
    r = compare_plans(plan(["a"]), plan(["a", "b"]))
    assert r["verdict"] == "PARTIAL"


def test_t523_submit_flag_fail():
    r = compare_plans(plan(["python3 run.py --allow-testnet-submit"]), plan(["python3 run.py"]))
    assert r["verdict"] == "FAIL"


def test_t523_mainnet_fail():
    r = compare_plans(plan(["python3 run.py --env mainnet"]), plan(["python3 run.py --env testnet"]))
    assert r["verdict"] == "FAIL"


def test_t523_malformed_fail():
    r = compare_plans(None, plan(["a"]))
    assert r["verdict"] == "FAIL"
