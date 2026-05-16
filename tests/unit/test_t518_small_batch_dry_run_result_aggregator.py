import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scripts.aggregate_small_batch_dry_run_results_v1 import aggregate


def write_json(path: Path, payload):
    path.write_text(json.dumps(payload), encoding="utf-8")


def result(verdict="PASS", env="testnet", submit_executed=False, submit_allowed=False):
    return {
        "verdict": verdict,
        "env": env,
        "submit_executed": submit_executed,
        "submit_allowed": submit_allowed,
    }


def test_t518_all_pass(tmp_path):
    p1 = tmp_path / "r1.json"
    p2 = tmp_path / "r2.json"
    write_json(p1, result())
    write_json(p2, result())
    r = aggregate([str(p1), str(p2)])
    assert r["verdict"] == "PASS"


def test_t518_partial_result(tmp_path):
    p1 = tmp_path / "r1.json"
    p2 = tmp_path / "r2.json"
    write_json(p1, result("PASS"))
    write_json(p2, result("PARTIAL"))
    r = aggregate([str(p1), str(p2)])
    assert r["verdict"] == "PARTIAL"


def test_t518_submit_executed_fail(tmp_path):
    p1 = tmp_path / "r1.json"
    write_json(p1, result("PASS", submit_executed=True))
    r = aggregate([str(p1)])
    assert r["verdict"] == "FAIL"


def test_t518_wrong_env_fail(tmp_path):
    p1 = tmp_path / "r1.json"
    write_json(p1, result("PASS", env="mainnet"))
    r = aggregate([str(p1)])
    assert r["verdict"] == "FAIL"


def test_t518_malformed_json_fail(tmp_path):
    p1 = tmp_path / "r1.json"
    p1.write_text("{bad", encoding="utf-8")
    r = aggregate([str(p1)])
    assert r["verdict"] == "FAIL"
