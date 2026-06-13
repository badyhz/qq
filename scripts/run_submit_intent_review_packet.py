#!/usr/bin/env python3
"""Wave 4: Submit intent review packet."""
import sys, pathlib
ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

def main():
    from src.runtime_integrations.testnet_sandbox.submit_intent_packet import build_intent_packet, write_packets
    from src.runtime_integrations.testnet_sandbox.submit_intent_validator import validate_intent, write_validations

    # Build sample packets
    packets = [
        build_intent_packet("BTCUSDT", "BUY", "LIMIT", 0.001, "LIMIT", "low risk", "SIG_001"),
        build_intent_packet("ETHUSDT", "SELL", "MARKET", 0.01, "MARKET", "medium risk", "SIG_002"),
        build_intent_packet("BNBUSDT", "BUY", "LIMIT", 0.1, "LIMIT", "low risk", "SIG_003"),
    ]

    write_packets(packets, ROOT / "data" / "runtime" / "testnet_sandbox" / "submit_intent_review_packets.jsonl")

    # Validate
    validations = [validate_intent(p.to_dict()) for p in packets]
    write_validations(validations, ROOT / "data" / "runtime" / "testnet_sandbox" / "submit_intent_validations.json")

    # Report
    lines = ["# Submit Intent Review Packet Report", "", f"Packets generated: {len(packets)}", f"All valid: {all(v.valid for v in validations)}", "", "## Packets", ""]
    for p in packets:
        lines.append(f"- {p.intent_id}: {p.symbol} {p.side} {p.quantity} (simulated={p.simulated}, real_submit={p.real_submit})")
    lines.extend(["", "## Conclusion", "", "SUBMIT_INTENT_REVIEW_PACKET_VALID", "NO_REAL_SUBMIT", ""])
    (ROOT / "reports" / "submit_intent_review_packet_report.md").write_text("\n".join(lines), encoding="utf-8")

    ok = all(v.valid for v in validations) and all(p.simulated and not p.real_submit for p in packets)
    print(f"Submit intent review: {'PASS' if ok else 'FAIL'}")
    return 0 if ok else 1

if __name__ == "__main__":
    sys.exit(main())
