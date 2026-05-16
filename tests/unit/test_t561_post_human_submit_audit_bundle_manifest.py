import json
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scripts.generate_post_human_submit_audit_bundle_manifest_v1 import generate_manifest


def _write_temp_json(data, suffix=".json"):
    fd, path = tempfile.mkstemp(suffix=suffix)
    with os.fdopen(fd, "w") as f:
        json.dump(data, f)
    return path


def _cleanup_temp(path):
    try:
        os.unlink(path)
    except Exception:
        pass


def test_pass_all_valid():
    base = {
        "verdict": "PASS",
        "readonly": True,
        "submit_allowed": False,
        "cancel_allowed": False,
        "flatten_allowed": False,
        "max_submit_count": 0,
        "env": "testnet",
    }
    paths = [_write_temp_json(base) for _ in range(10)]
    try:
        r = generate_manifest(*paths)
        assert r["ok"] is True
        assert r["verdict"] == "PASS"
        assert r["submit_allowed"] is False
        assert r["cancel_allowed"] is False
        assert r["flatten_allowed"] is False
        assert len(r["missing_artifacts"]) == 0
        assert len(r["invalid_artifacts"]) == 0
        assert len(r["blockers"]) == 0
    finally:
        for p in paths:
            _cleanup_temp(p)


def test_fail_missing_required():
    base = {"verdict": "PASS", "submit_allowed": False, "cancel_allowed": False, "flatten_allowed": False}
    paths = [_write_temp_json(base) for _ in range(9)]
    try:
        r = generate_manifest(*paths, None)
        assert r["ok"] is False
        assert r["verdict"] == "FAIL"
        assert len(r["missing_artifacts"]) > 0
    finally:
        for p in paths:
            _cleanup_temp(p)


def test_partial_invalid_json():
    base = {
        "verdict": "PASS",
        "submit_allowed": False,
        "cancel_allowed": False,
        "flatten_allowed": False,
        "readonly": True,
        "env": "testnet",
        "max_submit_count": 0,
    }
    paths = [_write_temp_json(base) for _ in range(9)]
    invalid_fd, invalid_path = tempfile.mkstemp(suffix=".json")
    with os.fdopen(invalid_fd, "w") as f:
        f.write("not valid json")
    paths.append(invalid_path)
    try:
        r = generate_manifest(*paths)
        assert r["ok"] is False
        assert r["verdict"] == "PARTIAL"
        assert len(r["invalid_artifacts"]) > 0
    finally:
        for p in paths:
            _cleanup_temp(p)


def test_fail_unsafe_marker():
    safe = {"verdict": "PASS", "submit_allowed": False, "cancel_allowed": False, "flatten_allowed": False}
    unsafe = {**safe, "env": "mainnet"}
    paths = [_write_temp_json(safe) for _ in range(9)]
    paths.append(_write_temp_json(unsafe))
    try:
        r = generate_manifest(*paths)
        assert r["ok"] is False
        assert r["verdict"] == "FAIL"
        assert any("UNSAFE_MARKER" in b or "MAINNET" in b or "ENV_NOT_TESTNET" in b for b in r["blockers"])
    finally:
        for p in paths:
            _cleanup_temp(p)


def test_fail_submit_allowed_true():
    safe = {"verdict": "PASS", "submit_allowed": False, "cancel_allowed": False, "flatten_allowed": False}
    bad = {**safe, "submit_allowed": True}
    paths = [_write_temp_json(safe) for _ in range(9)]
    paths.append(_write_temp_json(bad))
    try:
        r = generate_manifest(*paths)
        assert r["ok"] is False
        assert r["verdict"] == "FAIL"
        assert any("SUBMIT_ALLOWED_TRUE" in b for b in r["blockers"])
    finally:
        for p in paths:
            _cleanup_temp(p)


def test_partial_missing_optional_summary():
    base = {
        "verdict": "PASS",
        "readonly": True,
        "submit_allowed": False,
        "cancel_allowed": False,
        "flatten_allowed": False,
        "max_submit_count": 0,
        "env": "testnet",
    }
    paths = [_write_temp_json(base) for _ in range(10)]
    # Modify one to have max_submit_count not zero on verification phase
    with open(paths[5], "w") as f:
        json.dump({**base, "max_submit_count": 1}, f)
    try:
        r = generate_manifest(*paths)
        assert r["ok"] is False
        assert r["verdict"] == "FAIL"
    finally:
        for p in paths:
            _cleanup_temp(p)
