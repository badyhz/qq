"""Test exchange sandbox adapter stub."""
import pytest
from src.runtime_integrations.testnet_presubmit.exchange_sandbox_adapter_stub import run_all_stubs
from src.runtime_integrations.testnet_presubmit.exchange_adapter_contract_review import review_contract
from src.runtime_integrations.testnet_presubmit import exchange_sandbox_adapter_stub as mod

def test_all_stubs_simulated():
    results = run_all_stubs()
    for r in results:
        assert r.stub_only is True
        assert r.network_called is False
        assert r.real_submit is False
        assert r.testnet_submit is False
        assert r.no_submit_enforced is True

def test_contract_all_present():
    reviews = review_contract(mod)
    for r in reviews:
        assert r.present is True

def test_stubs_cover_methods():
    results = run_all_stubs()
    methods = {r.method for r in results}
    required = {"load_connection_profile_stub", "validate_permissions_stub", "build_signed_request_stub", "simulate_network_submit", "simulate_network_cancel", "simulate_fetch_order_status", "simulate_fetch_balance", "simulate_fetch_positions"}
    assert required.issubset(methods)
