#!/usr/bin/env python3
"""Wave 5: Cancel gate final lock check."""
import sys, pathlib
ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

def main():
    from src.runtime_integrations.testnet_final_gate.cancel_gate_final_lock import default_locked, validate_gate, write_state, render_report
    state = default_locked()
    valid, errors = validate_gate(state)
    write_state(state, ROOT / "data" / "runtime" / "testnet_final_gate" / "cancel_gate_final_lock.json")
    (ROOT / "reports" / "cancel_gate_final_lock_report.md").write_text(render_report(state, valid), encoding="utf-8")
    ok = valid and state.simulated_cancel_only and not state.real_cancel_allowed
    print(f"Cancel gate: {'PASS' if ok else 'FAIL'}")
    return 0 if ok else 1

if __name__ == "__main__":
    sys.exit(main())
