"""Runner: final no-submit archive."""
from __future__ import annotations
import importlib, pathlib, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

OUT_DIR = ROOT / "data" / "runtime" / "testnet_mock_closeout"
REPORT_DIR = ROOT / "reports" / "testnet_mock_closeout"

def main() -> int:
    mod = importlib.import_module("src.runtime_integrations.testnet_mock_closeout.final_no_submit_archive")
    archive = mod.create_archive()
    mod.write_archive(archive, OUT_DIR / "final_no_submit_archive.json")
    report = mod.render_report(archive)
    (REPORT_DIR / "final_no_submit_archive_report.md").parent.mkdir(parents=True, exist_ok=True)
    (REPORT_DIR / "final_no_submit_archive_report.md").write_text(report, encoding="utf-8")
    print(f"final_no_submit_archive: {len(archive.entries)} entries")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
