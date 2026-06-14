"""Integration test: read-only adapter contract."""
from __future__ import annotations
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent.parent))

from src.runtime_integrations.testnet_readonly_discovery.readonly_adapter_contract import (
    create_contract, validate_contract
)


def test_create_contract():
    contract = create_contract()
    assert contract.contract_id.startswith("ADC_")
    assert len(contract.methods) == 7


def test_validate_contract_valid():
    contract = create_contract()
    result = validate_contract(contract)
    assert result[0]["valid"] is True
    assert len(result[0]["errors"]) == 0


def test_all_methods_read_only():
    contract = create_contract()
    for m in contract.methods:
        assert m.read_only is True


def test_no_forbidden_methods():
    contract = create_contract()
    forbidden = ("submit_order", "cancel_order", "place_order", "market_order", "limit_order", "real_reconcile", "unlock_submit")
    for m in contract.methods:
        for f in forbidden:
            assert f not in m.name.lower()


def test_render_report():
    from src.runtime_integrations.testnet_readonly_discovery.readonly_adapter_contract import render_report
    contract = create_contract()
    report = render_report(contract)
    assert "READ_ONLY_ADAPTER_CONTRACT_READY" in report
    assert "REAL_ADAPTER_IMPLEMENTATION_NOT_ALLOWED" in report
