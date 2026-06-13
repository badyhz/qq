#!/usr/bin/env python3
"""Wave 7: Operator approval packet v2."""
import sys, pathlib
ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

def main():
    from src.runtime_integrations.testnet_final_gate.operator_approval_packet_v2 import create_packet_v2, validate_packet, write_packet, render_report
    packet = create_packet_v2("OP_001", "RV_001")
    valid, errors = validate_packet(packet)
    write_packet(packet, ROOT / "data" / "runtime" / "testnet_final_gate" / "operator_approval_packet_v2.json")
    (ROOT / "reports" / "operator_approval_packet_v2_report.md").write_text(render_report(packet, valid), encoding="utf-8")
    ok = valid and bool(packet.reviewer_id) and bool(packet.no_submit_declaration)
    print(f"Approval packet v2: {'PASS' if ok else 'FAIL'}")
    return 0 if ok else 1

if __name__ == "__main__":
    sys.exit(main())
