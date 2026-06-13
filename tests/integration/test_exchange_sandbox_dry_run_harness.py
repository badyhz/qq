"""Test exchange sandbox dry-run harness."""
import pytest
from src.runtime_integrations.testnet_final_gate.exchange_dry_run_harness import run_harness

def test_harness_no_network():
    r = run_harness()
    assert r.no_network is True

def test_harness_no_real_key():
    r = run_harness()
    assert r.no_real_key is True

def test_harness_no_submit():
    r = run_harness()
    assert r.no_submit is True

def test_harness_all_steps_pass():
    r = run_harness()
    for s in r.steps:
        assert s.status in ("PASS", "SIMULATED")
