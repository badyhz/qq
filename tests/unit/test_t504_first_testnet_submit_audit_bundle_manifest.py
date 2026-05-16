import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scripts.generate_first_testnet_submit_audit_bundle_manifest_v1 import generate_manifest


REQUIRED_KEYS = [
    "manual_approval_packet",
    "single_command_packet",
    "confirmation_gate",
    "execution_wrapper_result",
    "post_submit_verification",
    "evidence",
    "incident",
    "rollback_recommendation",
]


def _write(path: Path, payload):
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def _make_paths(tmp_path: Path):
    paths = {}
    for key in REQUIRED_KEYS:
        paths[key] = str(tmp_path / f"{key}.json")
    return paths


def _artifact_payload(name: str, env="testnet", symbol="BTCUSDT", submit_executed=True):
    base = {"env": env, "symbol": symbol, "submit_executed": submit_executed}
    if name == "execution_wrapper_result":
        base = {"request_plan": {"env": env, "symbol": symbol}, "submit_executed": submit_executed}
    if name == "evidence":
        base = {"env": env, "symbol": symbol, "submit_executed": submit_executed}
    return base


def test_t504_pass(tmp_path):
    paths = _make_paths(tmp_path)
    for name, p in paths.items():
        _write(Path(p), _artifact_payload(name))
    r = generate_manifest(paths)
    assert r["ok"] is True
    assert r["verdict"] == "PASS"


def test_t504_missing_artifact_fail(tmp_path):
    paths = _make_paths(tmp_path)
    for name, p in paths.items():
        if name != "incident":
            _write(Path(p), _artifact_payload(name))
    r = generate_manifest(paths)
    assert r["ok"] is False
    assert r["verdict"] == "FAIL"


def test_t504_invalid_json_fail(tmp_path):
    paths = _make_paths(tmp_path)
    for name, p in paths.items():
        _write(Path(p), _artifact_payload(name))
    Path(paths["incident"]).write_text("{bad json", encoding="utf-8")
    r = generate_manifest(paths)
    assert r["ok"] is False
    assert r["verdict"] == "FAIL"


def test_t504_env_mismatch_fail(tmp_path):
    paths = _make_paths(tmp_path)
    for name, p in paths.items():
        env = "mainnet" if name == "incident" else "testnet"
        _write(Path(p), _artifact_payload(name, env=env))
    r = generate_manifest(paths)
    assert r["ok"] is False
    assert r["verdict"] == "FAIL"


def test_t504_partial_missing_optional_fields(tmp_path):
    paths = _make_paths(tmp_path)
    for _, p in paths.items():
        _write(Path(p), {"only": "minimal"})
    r = generate_manifest(paths)
    assert r["ok"] is True
    assert r["verdict"] == "PARTIAL"
