"""Tests for read-only hook design contract docs — T961-T980."""

from pathlib import Path

DOCS_DIR = Path(__file__).resolve().parent.parent.parent / "docs" / "dev_prd"

REQUIRED_DOCS = [
    "read_only_hook_input_contract.md",
    "read_only_hook_output_contract.md",
    "read_only_hook_permission_adapter_design.md",
    "read_only_hook_sanitized_payload_design.md",
    "read_only_hook_invariant_plan.md",
    "read_only_hook_no_side_effect_proof_packet.md",
    "read_only_hook_failure_taxonomy_bridge.md",
    "read_only_hook_evidence_model.md",
    "read_only_hook_regression_packet_design.md",
    "read_only_hook_manual_review_checklist.md",
    "read_only_hook_rollout_hold_packet.md",
    "read_only_hook_rollback_plan.md",
    "read_only_hook_observability_design.md",
    "read_only_hook_threat_model.md",
    "read_only_hook_implementation_boundary_map.md",
    "read_only_hook_test_matrix.md",
    "read_only_hook_prompt_pack.md",
    "read_only_hook_closeout_bundle.md",
    "read_only_hook_route_recommendation.md",
    "read_only_hook_design_closeout_report.md",
]

class TestDesignContractDocsExist:
    def test_all_20_docs_exist(self):
        for name in REQUIRED_DOCS:
            assert (DOCS_DIR / name).exists(), f"Missing: {name}"

class TestDesignContractDocsSafety:
    def test_no_live_authorization(self):
        for name in REQUIRED_DOCS:
            text = (DOCS_DIR / name).read_text(encoding="utf-8")
            assert "authorized for live trading" not in text.lower(), f"{name} contains unauthorized claim"

    def test_all_have_design_only_status(self):
        for name in REQUIRED_DOCS:
            text = (DOCS_DIR / name).read_text(encoding="utf-8")
            assert "design_only" in text.lower() or "design only" in text.lower() or "DESIGN_ONLY" in text, f"{name} missing DESIGN_ONLY status"
