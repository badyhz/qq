import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scripts.generate_final_one_shot_manual_submit_checklist_packet_v1 import generate_checklist


def artifact(v="PASS"):
    return {"verdict": v, "submit_allowed": False}


def preview(v="PASS"):
    return {"verdict": v, "submit_allowed": False}


def token(v="PASS"):
    return {"verdict": v, "submit_allowed": False}


def verify(v="PASS"):
    return {"verdict": v, "submit_allowed": False}


def test_ready():
    r = generate_checklist(artifact("PASS"), preview("PASS"), token("PASS"), verify("PASS"))
    assert r["verdict"] == "PASS"
    assert r["checklist_status"] == "READY_FOR_HUMAN_DECISION"
    assert r["submit_allowed"] is False
    assert r["max_submit_count"] == 1


def test_needs_review():
    r = generate_checklist(artifact("PASS"), preview("PASS"), token("PASS"), verify("PARTIAL"))
    assert r["verdict"] == "PARTIAL"
    assert r["checklist_status"] == "NEEDS_REVIEW"


def test_blocked():
    r = generate_checklist(artifact("FAIL"), preview("PASS"), token("PASS"), verify("PASS"))
    assert r["verdict"] == "FAIL"
    assert r["checklist_status"] == "BLOCKED"


def test_required_checks_present():
    r = generate_checklist(artifact("PASS"), preview("PASS"), token("PASS"), verify("PASS"))
    checks = r["required_human_checks"]
    assert "CONFIRM_DRY_RUN_COMMAND_WAS_VERIFIED_PASS" in checks
    assert "CONFIRM_ENV_IS_TESTNET" in checks
    assert "CONFIRM_SYMBOL_SIDE_QUANTITY_ARE_CORRECT" in checks
    assert "CONFIRM_TOKEN_EXACT_MATCH" in checks
    assert "CONFIRM_ALLOW_FLAG_INTENTIONAL" in checks
    assert "CONFIRM_NO_MAINNET_OR_LIVE_MARKER" in checks
    assert "CONFIRM_NO_AUTO_LOOP_OR_REPEAT_SUBMIT" in checks
    assert "CONFIRM_MAX_SUBMIT_COUNT_IS_1" in checks
    assert "CONFIRM_PROTECTIVE_SL_TP_PLAN_EXISTS" in checks
    assert "CONFIRM_POST_SUBMIT_READONLY_VERIFICATION_WILL_RUN" in checks


def test_submit_allowed_remains_false():
    r = generate_checklist(artifact("PASS"), preview("PASS"), token("PASS"), verify("PASS"))
    assert r["submit_allowed"] is False
