"""Runner: readonly remediation backlog."""
from __future__ import annotations
import importlib, pathlib, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

OUT_DIR = ROOT / "data" / "runtime" / "testnet_readonly_scope_audit"
REPORT_DIR = ROOT / "reports" / "testnet_readonly_scope_audit"

def main() -> int:
    mod = importlib.import_module("src.runtime_integrations.testnet_readonly_scope_audit.remediation_backlog")
    backlog = mod.create_backlog()
    mod.write_backlog(backlog, OUT_DIR / "remediation_backlog.json")
    report = mod.render_report(backlog)
    (REPORT_DIR / "remediation_backlog_report.md").parent.mkdir(parents=True, exist_ok=True)
    (REPORT_DIR / "remediation_backlog_report.md").write_text(report, encoding="utf-8")
    print(f"remediation_backlog: {len(backlog.items)} items")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
