#!/usr/bin/env python3
"""Wave 4: Submit gate final lock check."""
import sys, pathlib
ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

def main():
    from src.runtime_integrations.testnet_final_gate.submit_gate_final_lock import default_locked, validate_gate, write_state, render_report
    state = default_locked()
    valid, errors = validate_gate(state)
    write_state(state, ROOT / "data" / "runtime" / "testnet_final_gate" / "submit_gate_final_lock.json")
    (ROOT / "reports" / "submit_gate_final_lock_report.md").write_text(render_report(state, valid), encoding="utf-8")
    ok = valid and state.submit_gate_state == "LOCKED" and not state.real_submit_allowed
    print(f"Submit gate: {'PASS' if ok else 'FAIL'}")
    return 0 if ok else 1

if __name__ == "__main__":
    sys.exit(main())
