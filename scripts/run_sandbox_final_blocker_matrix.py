#!/usr/bin/env python3
"""Wave 8: Sandbox final blocker matrix."""
import sys, pathlib
ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

def main():
    from src.runtime_integrations.testnet_final_gate.final_blocker_matrix import get_blockers, write_blockers, render_matrix, render_next_stage_blockers
    blockers = get_blockers()
    write_blockers(blockers, ROOT / "data" / "runtime" / "testnet_final_gate" / "final_blocker_matrix.json")
    (ROOT / "reports" / "sandbox_final_blocker_matrix.md").write_text(render_matrix(), encoding="utf-8")
    (ROOT / "reports" / "sandbox_final_next_stage_blockers.md").write_text(render_next_stage_blockers(), encoding="utf-8")
    blocking = [b for b in blockers if b.status == "BLOCKING"]
    ok = len(blocking) > 0  # blockers exist = not ready = correct
    print(f"Final blocker matrix: {'PASS' if ok else 'FAIL'} (blocking: {len(blocking)})")
    return 0 if ok else 1

if __name__ == "__main__":
    sys.exit(main())
