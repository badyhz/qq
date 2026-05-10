import pytest
import json
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from scripts.interpret_manual_pre_dry_run_checklist_v1 import (
    interpret_checklist,
    load_json,
    write_json
)


def test_approved_all_true_gives_pass(tmp_path):
    review_packet = {
        "ok": True,
        "task": "T431",
        "phase": "MANUAL_PRE_DRY_RUN_REVIEW",
        "review_packet_status": "READY_FOR_MANUAL_PRE_DRY_RUN_REVIEW",
        "final_decision": "READY_FOR_MANUAL_PRE_DRY_RUN_CHECKLIST"
    }

    checklist_result = {
        "reviewer": "test_operator",
        "approved": True,
        "checklist": {
            "REVIEW_T426_INPUT_PACKET": True,
            "REVIEW_T427_SAFETY_GATES": True,
            "REVIEW_T428_DATA_LINEAGE_LEDGER": True,
            "REVIEW_T429_READINESS_SCORE": True,
            "REVIEW_T430_PHASE_CONTROL": True,
            "CONFIRM_TESTNET_DRY_RUN_STILL_BLOCKED": True,
            "CONFIRM_NO_SUBMIT_CANCEL_FLATTEN": True
        },
        "notes": "All looks good"
    }

    result = interpret_checklist(review_packet, checklist_result)

    assert result["ok"] is True
    assert result["task"] == "T432"
    assert result["checklist_status"] == "MANUAL_PRE_DRY_RUN_CHECKLIST_APPROVED"
    assert result["final_decision"] == "READY_FOR_MANUAL_PRE_DRY_RUN_APPROVAL_ARTIFACT"
    assert result["reviewer"] == "test_operator"
    assert len(result["missing_items"]) == 0
    assert len(result["failed_items"]) == 0


def test_approved_false_gives_reject(tmp_path):
    review_packet = {
        "ok": True,
        "task": "T431",
        "final_decision": "READY_FOR_MANUAL_PRE_DRY_RUN_CHECKLIST"
    }

    checklist_result = {
        "reviewer": "test_operator",
        "approved": False,
        "checklist": {
            "REVIEW_T426_INPUT_PACKET": True,
            "REVIEW_T427_SAFETY_GATES": True,
            "REVIEW_T428_DATA_LINEAGE_LEDGER": True,
            "REVIEW_T429_READINESS_SCORE": True,
            "REVIEW_T430_PHASE_CONTROL": True,
            "CONFIRM_TESTNET_DRY_RUN_STILL_BLOCKED": True,
            "CONFIRM_NO_SUBMIT_CANCEL_FLATTEN": True
        }
    }

    result = interpret_checklist(review_packet, checklist_result)

    assert result["ok"] is False
    assert result["checklist_status"] == "MANUAL_PRE_DRY_RUN_CHECKLIST_REJECTED_OR_INCOMPLETE"
    assert result["final_decision"] == "CONTINUE_MANUAL_PRE_DRY_RUN_REVIEW"


def test_missing_item_gives_fail(tmp_path):
    review_packet = {
        "ok": True,
        "task": "T431",
        "final_decision": "READY_FOR_MANUAL_PRE_DRY_RUN_CHECKLIST"
    }

    checklist_result = {
        "reviewer": "test_operator",
        "approved": True,
        "checklist": {
            "REVIEW_T426_INPUT_PACKET": True,
            "REVIEW_T427_SAFETY_GATES": True,
            "REVIEW_T428_DATA_LINEAGE_LEDGER": True,
            "REVIEW_T429_READINESS_SCORE": True,
            "REVIEW_T430_PHASE_CONTROL": True,
            "CONFIRM_TESTNET_DRY_RUN_STILL_BLOCKED": True
            # Missing CONFIRM_NO_SUBMIT_CANCEL_FLATTEN
        }
    }

    result = interpret_checklist(review_packet, checklist_result)

    assert result["ok"] is False
    assert "CONFIRM_NO_SUBMIT_CANCEL_FLATTEN" in result["missing_items"]


def test_one_false_item_gives_fail(tmp_path):
    review_packet = {
        "ok": True,
        "task": "T431",
        "final_decision": "READY_FOR_MANUAL_PRE_DRY_RUN_CHECKLIST"
    }

    checklist_result = {
        "reviewer": "test_operator",
        "approved": True,
        "checklist": {
            "REVIEW_T426_INPUT_PACKET": True,
            "REVIEW_T427_SAFETY_GATES": True,
            "REVIEW_T428_DATA_LINEAGE_LEDGER": True,
            "REVIEW_T429_READINESS_SCORE": True,
            "REVIEW_T430_PHASE_CONTROL": True,
            "CONFIRM_TESTNET_DRY_RUN_STILL_BLOCKED": True,
            "CONFIRM_NO_SUBMIT_CANCEL_FLATTEN": False
        }
    }

    result = interpret_checklist(review_packet, checklist_result)

    assert result["ok"] is False
    assert "CONFIRM_NO_SUBMIT_CANCEL_FLATTEN" in result["failed_items"]


def test_t431_blocked_gives_fail(tmp_path):
    review_packet = {
        "ok": False,
        "task": "T431",
        "final_decision": "CONTINUE_PRE_DRY_RUN_READINESS_REVIEW"
    }

    checklist_result = {
        "reviewer": "test_operator",
        "approved": True,
        "checklist": {
            "REVIEW_T426_INPUT_PACKET": True,
            "REVIEW_T427_SAFETY_GATES": True,
            "REVIEW_T428_DATA_LINEAGE_LEDGER": True,
            "REVIEW_T429_READINESS_SCORE": True,
            "REVIEW_T430_PHASE_CONTROL": True,
            "CONFIRM_TESTNET_DRY_RUN_STILL_BLOCKED": True,
            "CONFIRM_NO_SUBMIT_CANCEL_FLATTEN": True
        }
    }

    result = interpret_checklist(review_packet, checklist_result)

    assert result["ok"] is False
    assert result["final_decision"] == "CONTINUE_MANUAL_PRE_DRY_RUN_REVIEW"


def test_safety_invariants(tmp_path):
    review_packet = {
        "ok": True,
        "task": "T431",
        "final_decision": "READY_FOR_MANUAL_PRE_DRY_RUN_CHECKLIST"
    }

    checklist_result = {
        "reviewer": "test_operator",
        "approved": True,
        "checklist": {
            "REVIEW_T426_INPUT_PACKET": True,
            "REVIEW_T427_SAFETY_GATES": True,
            "REVIEW_T428_DATA_LINEAGE_LEDGER": True,
            "REVIEW_T429_READINESS_SCORE": True,
            "REVIEW_T430_PHASE_CONTROL": True,
            "CONFIRM_TESTNET_DRY_RUN_STILL_BLOCKED": True,
            "CONFIRM_NO_SUBMIT_CANCEL_FLATTEN": True
        }
    }

    result = interpret_checklist(review_packet, checklist_result)

    sf = result["safety_flags"]
    assert sf["shadow_only"] is True
    assert sf["testnet_dry_run_allowed"] is False
    assert sf["testnet_submit_allowed"] is False
    assert sf["real_submit_allowed"] is False
    assert sf["submit_attempted"] is False
    assert sf["cancel_attempted"] is False
    assert sf["flatten_attempted"] is False

    blocked = result["blocked_actions"]
    assert "TESTNET_DRY_RUN_ONLY" in blocked
    assert "TESTNET_DRY_RUN_ONLY" not in result["allowed_actions"]


def test_missing_checklist_result_gives_fail(tmp_path):
    review_packet = {
        "ok": True,
        "task": "T431",
        "final_decision": "READY_FOR_MANUAL_PRE_DRY_RUN_CHECKLIST"
    }

    result = interpret_checklist(review_packet, None)

    assert result["ok"] is False
    assert result["checklist_status"] == "MANUAL_PRE_DRY_RUN_CHECKLIST_REJECTED_OR_INCOMPLETE"


def test_load_json_functions(tmp_path):
    assert load_json(str(tmp_path / "nonexistent.json")) is None

    invalid_path = tmp_path / "invalid.json"
    with open(invalid_path, "w") as f:
        f.write("not json")
    assert load_json(str(invalid_path)) is None

    data = {"ok": True}
    out_path = tmp_path / "out.json"
    assert write_json(str(out_path), data) is True
    loaded = load_json(str(out_path))
    assert loaded["ok"] is True


def test_cli_smoke(tmp_path):
    review_packet_path = tmp_path / "t431.json"
    checklist_path = tmp_path / "checklist.json"

    review_packet = {
        "ok": True,
        "task": "T431",
        "final_decision": "READY_FOR_MANUAL_PRE_DRY_RUN_CHECKLIST"
    }

    checklist_result = {
        "reviewer": "test_operator",
        "approved": True,
        "checklist": {
            "REVIEW_T426_INPUT_PACKET": True,
            "REVIEW_T427_SAFETY_GATES": True,
            "REVIEW_T428_DATA_LINEAGE_LEDGER": True,
            "REVIEW_T429_READINESS_SCORE": True,
            "REVIEW_T430_PHASE_CONTROL": True,
            "CONFIRM_TESTNET_DRY_RUN_STILL_BLOCKED": True,
            "CONFIRM_NO_SUBMIT_CANCEL_FLATTEN": True
        }
    }

    with open(review_packet_path, "w") as f:
        json.dump(review_packet, f)
    with open(checklist_path, "w") as f:
        json.dump(checklist_result, f)

    proc = subprocess.Popen(
        [
            sys.executable,
            str(Path(__file__).parent.parent.parent / "scripts" / "interpret_manual_pre_dry_run_checklist_v1.py"),
            "--review-packet", str(review_packet_path),
            "--checklist-result", str(checklist_path),
            "--json"
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=str(tmp_path)
    )
    stdout, stderr = proc.communicate()

    assert proc.returncode == 0
    result_json = json.loads(stdout)
    assert result_json["task"] == "T432"
