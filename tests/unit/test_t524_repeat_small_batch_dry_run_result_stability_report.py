import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scripts.generate_repeat_small_batch_dry_run_result_stability_report_v1 import generate_report


def agg(verdict="PASS", result_count=5, pass_count=5, unsafe_count=0, submit_executed_count=0, submit_allowed=False):
    return {
        "verdict": verdict,
        "result_count": result_count,
        "pass_count": pass_count,
        "unsafe_count": unsafe_count,
        "submit_executed_count": submit_executed_count,
        "submit_allowed": submit_allowed,
        "result_summaries": [{"env": "testnet"} for _ in range(result_count)],
    }


def risk(status="LOW"):
    return {"concentration_status": status}


def test_t524_stable_pass():
    r = generate_report(agg(), agg(), risk("LOW"), risk("LOW"))
    assert r["verdict"] == "PASS"
    assert r["stability_status"] == "STABLE"


def test_t524_pass_rate_drift_partial():
    r = generate_report(agg(pass_count=5), agg(pass_count=2), risk("LOW"), risk("LOW"))
    assert r["verdict"] == "PARTIAL"


def test_t524_unsafe_fail():
    a = agg()
    a["result_summaries"][0]["env"] = "mainnet"
    r = generate_report(a, agg(), risk("LOW"), risk("LOW"))
    assert r["verdict"] == "FAIL"


def test_t524_submit_executed_fail():
    r = generate_report(agg(submit_executed_count=1), agg(), risk("LOW"), risk("LOW"))
    assert r["verdict"] == "FAIL"


def test_t524_concentration_worsens_partial():
    r = generate_report(agg(), agg(), risk("LOW"), risk("HIGH"))
    assert r["verdict"] == "PARTIAL"
