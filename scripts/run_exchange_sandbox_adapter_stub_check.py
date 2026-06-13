#!/usr/bin/env python3
"""Wave 2: Exchange sandbox adapter stub check."""
import sys, pathlib
ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

def main():
    from src.runtime_integrations.testnet_presubmit.exchange_sandbox_adapter_stub import run_all_stubs, write_results
    from src.runtime_integrations.testnet_presubmit.exchange_adapter_contract_review import review_contract, write_reviews
    from src.runtime_integrations.testnet_presubmit import exchange_sandbox_adapter_stub as stub_mod

    results = run_all_stubs()
    write_results(results, ROOT / "data" / "runtime" / "testnet_presubmit" / "exchange_adapter_stub_check.json")

    reviews = review_contract(stub_mod)
    write_reviews(reviews, ROOT / "data" / "runtime" / "testnet_presubmit" / "exchange_adapter_contract_review.json")

    # Report
    lines = ["# Exchange Sandbox Adapter Stub Report", "", "## Stub Results", "", "| Method | Stub Only | Network Called | Real Submit |", "|--------|-----------|---------------|-------------|"]
    for r in results:
        lines.append(f"| {r.method} | {r.stub_only} | {r.network_called} | {r.real_submit} |")
    lines.extend(["", "## Contract Review", ""]
    )
    for rv in reviews:
        lines.append(f"- {rv.method}: present={rv.present}, simulation_only={rv.simulation_only}")
    lines.extend(["", "## Conclusion", "", "EXCHANGE_SANDBOX_ADAPTER_STUB_VALID", ""])
    (ROOT / "reports" / "exchange_sandbox_adapter_stub_report.md").write_text("\n".join(lines), encoding="utf-8")

    ok = all(r.stub_only and not r.network_called and not r.real_submit for r in results) and all(rv.present for rv in reviews)
    print(f"Exchange adapter stub: {'PASS' if ok else 'FAIL'}")
    return 0 if ok else 1

if __name__ == "__main__":
    sys.exit(main())
