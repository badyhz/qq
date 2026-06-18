"""Phase 10B smoke test — public readonly klines adapter. No secrets, no orders."""
from __future__ import annotations

import json
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core.paper_trading.data_source import DataSourceConfig
from core.paper_trading.public_market_adapter import BinancePublicKlineAdapter
from core.paper_trading.market_data_quality import validate_bars

REPO_ROOT = os.path.join(os.path.dirname(__file__), "..")
REPORT_DIR = os.path.join(REPO_ROOT, "reports")

SAFETY_FLAGS = ["PAPER_ONLY", "READONLY_ONLY", "NO_ORDER", "NO_TESTNET",
                "NO_LIVE", "NO_SECRET", "PUBLIC_REST_ONLY", "NO_WEBSOCKET"]


def run_smoke():
    """Run Phase 10B public readonly smoke test."""
    print("=== Phase 10B Public Readonly Smoke Test ===\n")
    os.makedirs(REPORT_DIR, exist_ok=True)

    results = {
        "timestamp": time.time(),
        "phase": "10B",
        "adapter": "BinancePublicKlineAdapter",
        "safety_flags": SAFETY_FLAGS,
        "tests": [],
    }

    # Test 1: offline mode (no network)
    print("[1] Offline mode (network_enabled=False)...")
    config = DataSourceConfig(mode="snapshot", network_enabled=False)
    adapter = BinancePublicKlineAdapter(config)
    bars = adapter.get_bars("BTCUSDT")
    offline_ok = bars == []
    results["tests"].append({
        "name": "offline_returns_empty",
        "pass": offline_ok,
        "detail": f"bars={len(bars)}",
    })
    print(f"    {'PASS' if offline_ok else 'FAIL'}: {len(bars)} bars")

    # Test 2: invalid symbol
    print("[2] Invalid symbol...")
    config = DataSourceConfig(mode="snapshot", network_enabled=True)
    adapter = BinancePublicKlineAdapter(config)
    bars = adapter.get_bars("invalid")
    invalid_sym_ok = bars == []
    results["tests"].append({
        "name": "invalid_symbol_empty",
        "pass": invalid_sym_ok,
        "detail": f"bars={len(bars)}",
    })
    print(f"    {'PASS' if invalid_sym_ok else 'FAIL'}: {len(bars)} bars")

    # Test 3: invalid interval
    print("[3] Invalid interval...")
    bars = adapter.get_bars("BTCUSDT", timeframe="2h")
    invalid_int_ok = bars == []
    results["tests"].append({
        "name": "invalid_interval_empty",
        "pass": invalid_int_ok,
        "detail": f"bars={len(bars)}",
    })
    print(f"    {'PASS' if invalid_int_ok else 'FAIL'}: {len(bars)} bars")

    # Test 4: adapter properties
    print("[4] Adapter properties...")
    props_ok = adapter.source_name == "binance_public" and adapter.network_enabled is True
    results["tests"].append({
        "name": "adapter_properties",
        "pass": props_ok,
        "detail": f"source={adapter.source_name}, net={adapter.network_enabled}",
    })
    print(f"    {'PASS' if props_ok else 'FAIL'}")

    # Test 5: no account/order methods
    print("[5] No account/order methods...")
    forbidden = ["get_account", "get_balance", "submit_order", "place_order", "cancel_order"]
    no_methods = not any(hasattr(adapter, m) for m in forbidden)
    results["tests"].append({
        "name": "no_order_methods",
        "pass": no_methods,
        "detail": f"checked: {forbidden}",
    })
    print(f"    {'PASS' if no_methods else 'FAIL'}")

    # Test 6: quality validator on empty
    print("[6] Quality validator on empty bars...")
    from core.paper_trading.market_data_quality import validate_bars as vb
    qr = vb([])
    empty_quality_ok = not qr.ok and "empty_bars" in qr.issues
    results["tests"].append({
        "name": "quality_empty_bars",
        "pass": empty_quality_ok,
        "detail": f"ok={qr.ok}, issues={qr.issues}",
    })
    print(f"    {'PASS' if empty_quality_ok else 'FAIL'}")

    # Summary
    all_pass = all(t["pass"] for t in results["tests"])
    results["all_pass"] = all_pass

    json_path = os.path.join(REPORT_DIR, "phase10b_smoke.json")
    with open(json_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nJSON: {json_path}")

    md_path = os.path.join(REPORT_DIR, "phase10b_smoke.md")
    with open(md_path, "w") as f:
        f.write("# Phase 10B Public Readonly Smoke Test\n\n")
        f.write(f"**All Pass:** {all_pass}\n\n")
        f.write("## Safety Flags\n\n")
        for flag in SAFETY_FLAGS:
            f.write(f"- {flag}\n")
        f.write("\n## Tests\n\n")
        for t in results["tests"]:
            status = "PASS" if t["pass"] else "FAIL"
            f.write(f"- [{status}] {t['name']}: {t['detail']}\n")
    print(f"Markdown: {md_path}")

    print(f"\n{'ALL PASS' if all_pass else 'SOME FAIL'}")
    print("\nSafety:")
    print("- No secrets")
    print("- No orders")
    print("- No testnet/live")
    print("- Public REST only (offline in this smoke)")
    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(run_smoke())
