"""Test request signing dry-run."""
import pytest
from src.runtime_integrations.testnet_final_gate.request_signing_dry_run import run_signing_dry_run, build_unsigned_envelope, simulate_canonical_string, produce_fake_signature

def test_signing_dry_run_mode():
    r = run_signing_dry_run("BTCUSDT", "BUY", 0.001)
    assert r.signing_mode == "DRY_RUN_ONLY"

def test_signing_fake_signature():
    r = run_signing_dry_run("BTCUSDT", "BUY", 0.001)
    assert r.fake_signature is True

def test_signing_redacted():
    r = run_signing_dry_run("BTCUSDT", "BUY", 0.001)
    assert r.signature_redacted is True

def test_signing_no_real_secret():
    r = run_signing_dry_run("BTCUSDT", "BUY", 0.001)
    assert r.real_secret_used is False

def test_signing_not_sendable():
    r = run_signing_dry_run("BTCUSDT", "BUY", 0.001)
    assert r.request_sendable is False

def test_envelope_fields():
    e = build_unsigned_envelope("BTCUSDT", "BUY", 0.001)
    assert e["symbol"] == "BTCUSDT"
    assert e["side"] == "BUY"

def test_canonical_string():
    e = build_unsigned_envelope("BTCUSDT", "BUY", 0.001)
    c = simulate_canonical_string(e)
    assert "BTCUSDT" in c

def test_fake_signature_deterministic():
    sig1 = produce_fake_signature("test=1")
    sig2 = produce_fake_signature("test=1")
    assert sig1 == sig2
