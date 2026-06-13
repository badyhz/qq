#!/usr/bin/env python3
"""Wave 6: Kill switch validation."""
import sys, pathlib
ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

def main():
    from src.runtime_integrations.testnet_sandbox.kill_switch import default_state, validate_kill_switch, write_state, render_kill_switch_report

    state = default_state()
    valid, errors = validate_kill_switch(state)
    write_state(state, ROOT / "data" / "runtime" / "testnet_sandbox" / "kill_switch_validation.json")
    (ROOT / "reports" / "kill_switch_validation_report.md").write_text(render_kill_switch_report(state, valid), encoding="utf-8")

    ok = valid and state.kill_switch_enabled and state.submit_blocked and not state.real_trading_allowed and not state.testnet_submit_allowed
    print(f"Kill switch: {'PASS' if ok else 'FAIL'}")
    return 0 if ok else 1

if __name__ == "__main__":
    sys.exit(main())
