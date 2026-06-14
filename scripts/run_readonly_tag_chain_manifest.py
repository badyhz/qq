"""Runner: readonly tag chain manifest."""
from __future__ import annotations
import importlib, pathlib, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

OUT_DIR = ROOT / "data" / "runtime" / "testnet_readonly_checkpoint"
REPORT_DIR = ROOT / "reports" / "testnet_readonly_checkpoint"

def main() -> int:
    mod = importlib.import_module("src.runtime_integrations.testnet_readonly_checkpoint.tag_chain_manifest")
    manifest = mod.create_manifest()
    mod.write_manifest(manifest, OUT_DIR / "tag_chain_manifest.json")
    report = mod.render_report(manifest)
    (REPORT_DIR / "tag_chain_manifest_report.md").parent.mkdir(parents=True, exist_ok=True)
    (REPORT_DIR / "tag_chain_manifest_report.md").write_text(report, encoding="utf-8")
    print(f"tag_chain_manifest: {manifest.total_tags} tags, all_present={manifest.all_present}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
