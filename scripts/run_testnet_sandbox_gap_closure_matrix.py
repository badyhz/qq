#!/usr/bin/env python3
"""Wave 8: Testnet sandbox gap closure matrix."""
import sys, pathlib
ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

def main():
    from src.runtime_integrations.testnet_sandbox.gap_closure_matrix import get_gaps, write_gaps, render_closure_matrix, render_next_stage_blockers

    gaps = get_gaps()
    write_gaps(gaps, ROOT / "data" / "runtime" / "testnet_sandbox" / "gap_closure_matrix.json")
    (ROOT / "reports" / "testnet_sandbox_gap_closure_matrix.md").write_text(render_closure_matrix(), encoding="utf-8")
    (ROOT / "reports" / "testnet_sandbox_next_stage_blockers.md").write_text(render_next_stage_blockers(), encoding="utf-8")

    # Must remain NOT_READY
    blocking_missing = [g for g in gaps if g.blocking and g.status in ("MISSING", "BLOCKED")]
    ok = len(blocking_missing) > 0  # gaps exist = not ready = correct
    print(f"Gap closure matrix: {'PASS' if ok else 'FAIL'} (blocking gaps: {len(blocking_missing)})")
    return 0 if ok else 1

if __name__ == "__main__":
    sys.exit(main())
