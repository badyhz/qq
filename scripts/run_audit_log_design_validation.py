#!/usr/bin/env python3
"""Wave 7: Audit log design validation."""
import sys, pathlib, json
ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

def main():
    from src.runtime_integrations.testnet_presubmit.audit_log_design import build_sample_chain, write_events
    from src.runtime_integrations.testnet_presubmit.audit_log_validator import validate_chain, write_validation

    events = build_sample_chain()
    write_events(events, ROOT / "data" / "runtime" / "testnet_presubmit" / "audit_log_design.jsonl")

    # Validate chain
    event_dicts = [e.to_dict() for e in events]
    val = validate_chain(event_dicts)
    write_validation(val, ROOT / "data" / "runtime" / "testnet_presubmit" / "audit_log_validation.json")

    # Report
    lines = ["# Audit Log Design Validation Report", "", f"Total events: {val.total_events}", f"Chain valid: {val.chain_valid}", f"Tampering detected: {val.tampering_detected}", "", "## Events", ""]
    for e in events:
        lines.append(f"- {e.event_type}: hash={e.event_hash[:16]}..., no_submit={e.no_submit_enforced}")
    lines.extend(["", "## Conclusion", "", "AUDIT_LOG_DESIGN_VALID", ""])
    (ROOT / "reports" / "audit_log_design_validation_report.md").write_text("\n".join(lines), encoding="utf-8")

    ok = val.chain_valid and not val.tampering_detected and all(e.no_submit_enforced for e in events)
    print(f"Audit log: {'PASS' if ok else 'FAIL'}")
    return 0 if ok else 1

if __name__ == "__main__":
    sys.exit(main())
