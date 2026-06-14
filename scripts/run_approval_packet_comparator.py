"""Runner: approval packet comparator."""
from __future__ import annotations
import importlib, json, pathlib, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

OUT_DIR = ROOT / "data" / "runtime" / "testnet_mock_review"
REPORT_DIR = ROOT / "reports" / "testnet_mock_review"

def main() -> int:
    comparator_mod = importlib.import_module("src.runtime_integrations.testnet_mock_review.approval_packet_comparator")
    packet_mod = importlib.import_module("src.runtime_integrations.testnet_mock_replay.human_approval_packet_v3")

    # Compare packet with itself (identical case)
    packet = packet_mod.create_packet("BUNDLE_TEST")
    packet_dict = packet.to_dict()
    result_identical = comparator_mod.compare_packets(packet_dict, packet_dict)

    # Compare with a modified version
    modified = dict(packet_dict)
    modified["packet_id"] = "APPROVAL_V3_MODIFIED"
    modified["decision"] = "APPROVAL_PACKET_REVIEWED"
    result_different = comparator_mod.compare_packets(packet_dict, modified)

    comparator_mod.write_comparison(result_different, OUT_DIR / "approval_packet_comparison.json")

    report = comparator_mod.render_report(result_different)
    (REPORT_DIR / "approval_packet_comparator_report.md").parent.mkdir(parents=True, exist_ok=True)
    (REPORT_DIR / "approval_packet_comparator_report.md").write_text(report, encoding="utf-8")

    print(f"approval_packet_comparator: identical={result_identical.identical}, diffs={len(result_different.diffs)}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
