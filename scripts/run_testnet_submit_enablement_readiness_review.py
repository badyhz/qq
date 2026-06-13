"""Runner: testnet submit enablement readiness review."""
from __future__ import annotations
import importlib, json, pathlib, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

OUT_DIR = ROOT / "data" / "runtime" / "enablement_readiness"
REPORT_DIR = ROOT / "reports" / "enablement_readiness"

def main() -> int:
    review_mod = importlib.import_module("src.runtime_integrations.testnet_enablement.enablement_readiness_review")
    policy_mod = importlib.import_module("src.runtime_integrations.testnet_enablement.enablement_readiness_policy")

    review = review_mod.run_review()
    review_mod.write_review(review, OUT_DIR / "readiness_review.json")
    report = review_mod.render_report(review)
    (REPORT_DIR / "readiness_review.md").parent.mkdir(parents=True, exist_ok=True)
    (REPORT_DIR / "readiness_review.md").write_text(report, encoding="utf-8")

    criteria = policy_mod.get_criteria()
    policy_mod.write_criteria(criteria, OUT_DIR / "readiness_policy.json")

    print(f"readiness_review: submit_allowed={review.submit_allowed}")
    print(f"readiness_policy: {len(criteria)} criteria")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
