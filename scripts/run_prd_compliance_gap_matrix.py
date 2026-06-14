"""Runner: PRD compliance gap matrix."""
from __future__ import annotations
import importlib, pathlib, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

OUT_DIR = ROOT / "data" / "runtime" / "testnet_readonly_scope_audit"
REPORT_DIR = ROOT / "reports" / "testnet_readonly_scope_audit"

def main() -> int:
    mod = importlib.import_module("src.runtime_integrations.testnet_readonly_scope_audit.prd_compliance_gap_matrix")
    matrix = mod.create_matrix()
    mod.write_matrix(matrix, OUT_DIR / "prd_compliance_gap_matrix.json")
    report = mod.render_report(matrix)
    (REPORT_DIR / "prd_compliance_gap_matrix_report.md").parent.mkdir(parents=True, exist_ok=True)
    (REPORT_DIR / "prd_compliance_gap_matrix_report.md").write_text(report, encoding="utf-8")
    blocking = mod.count_blocking(matrix)
    print(f"prd_compliance_gap_matrix: {len(matrix.gaps)} gaps, {blocking} blocking")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
