import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scripts.generate_repo_hygiene_phase_control_report_v1 import generate_phase_control


def test_ready():
    inv = {"verdict": "PASS", "blockers": [], "warnings": [], "categories": {}}
    tr = {"verdict": "PASS", "blockers": [], "warnings": []}
    git = {"verdict": "PASS", "blockers": [], "warnings": []}
    cl = {"verdict": "PASS", "blockers": [], "warnings": []}
    r = generate_phase_control(inv, tr, git, cl)
    assert r["ok"] is True
    assert r["verdict"] == "PASS"
    assert r["decision"] == "READY_FOR_MANUAL_GIT_ADD_REVIEW"
    assert r["git_mutation_allowed"] is False
    assert r["delete_allowed"] is False


def test_partial_review():
    inv = {"verdict": "PARTIAL", "blockers": [], "warnings": ["SOME_WARNING"], "categories": {}}
    tr = {"verdict": "PASS", "blockers": [], "warnings": []}
    git = {"verdict": "PASS", "blockers": [], "warnings": []}
    cl = {"verdict": "PASS", "blockers": [], "warnings": []}
    r = generate_phase_control(inv, tr, git, cl)
    assert r["ok"] is False
    assert r["verdict"] == "PARTIAL"
    assert r["decision"] == "REVIEW"


def test_blocked_secret():
    inv = {"verdict": "FAIL", "blockers": ["SECRET_RISK_FILES_DETECTED"], "warnings": [], "categories": {}}
    tr = {"verdict": "PASS", "blockers": [], "warnings": []}
    git = {"verdict": "PASS", "blockers": [], "warnings": []}
    cl = {"verdict": "PASS", "blockers": [], "warnings": []}
    r = generate_phase_control(inv, tr, git, cl)
    assert r["ok"] is False
    assert r["verdict"] == "FAIL"
    assert r["decision"] == "BLOCKED"


def test_git_mutation_false():
    inv = {"verdict": "PASS", "blockers": [], "warnings": [], "categories": {}}
    tr = {"verdict": "PASS", "blockers": [], "warnings": []}
    git = {"verdict": "PASS", "blockers": [], "warnings": []}
    cl = {"verdict": "PASS", "blockers": [], "warnings": []}
    r = generate_phase_control(inv, tr, git, cl)
    assert r["git_mutation_allowed"] is False
    assert r["delete_allowed"] is False
