"""Mock field-test evidence bundle."""
from __future__ import annotations
import json, pathlib, uuid
from dataclasses import dataclass
from datetime import datetime, timezone

@dataclass(frozen=True)
class EvidenceItem:
    item_id: str
    category: str
    title: str
    content: str
    def to_dict(self) -> dict:
        return {"item_id": self.item_id, "category": self.category, "title": self.title, "content": self.content}

@dataclass(frozen=True)
class EvidenceBundle:
    bundle_id: str
    created_at: str
    items: tuple[EvidenceItem, ...]
    def to_dict(self) -> dict:
        return {"bundle_id": self.bundle_id, "created_at": self.created_at, "items": [i.to_dict() for i in self.items]}

def create_bundle(scenario_count: int, passed_count: int, failed_count: int) -> EvidenceBundle:
    items = (
        EvidenceItem(f"EV_{uuid.uuid4().hex[:8]}", "replay_summary", "Replay Summary", f"Total scenarios: {scenario_count}, Passed: {passed_count}, Failed: {failed_count}"),
        EvidenceItem(f"EV_{uuid.uuid4().hex[:8]}", "scenario_matrix", "Scenario Matrix Result", f"All {scenario_count} scenarios executed in mock mode"),
        EvidenceItem(f"EV_{uuid.uuid4().hex[:8]}", "request_envelope", "Request Envelope Sample", "All requests use X-Mock-Transport=true header"),
        EvidenceItem(f"EV_{uuid.uuid4().hex[:8]}", "response_fixture", "Response Fixture Sample", "All responses from local mock fixtures"),
        EvidenceItem(f"EV_{uuid.uuid4().hex[:8]}", "vault_stub", "Vault Stub Report", "vault_mode=STUB_ONLY, real_credentials_enabled=false, placeholder credentials only"),
        EvidenceItem(f"EV_{uuid.uuid4().hex[:8]}", "signing_fixture", "Signing Fixture Report", "signing_mode=FIXTURE_ONLY, real_secret_used=false, dummy signing only"),
        EvidenceItem(f"EV_{uuid.uuid4().hex[:8]}", "governance_checklist", "Governance Checklist Report", "All governance checks documented, blockers present"),
        EvidenceItem(f"EV_{uuid.uuid4().hex[:8]}", "unlock_decision", "Unlock Dry-Run Decision", "All unlock requests DENY, no gate unlocked"),
        EvidenceItem(f"EV_{uuid.uuid4().hex[:8]}", "safety_report", "No-Submit Safety Report", "No forbidden imports, no real credentials, no gate unlock"),
        EvidenceItem(f"EV_{uuid.uuid4().hex[:8]}", "limitations", "Final Limitations", "THIS_IS_MOCK_EVIDENCE_ONLY, REAL_TESTNET_SUBMIT_NOT_ALLOWED, REAL_TRADING_NOT_ALLOWED"),
    )
    return EvidenceBundle(
        bundle_id=f"BUNDLE_{uuid.uuid4().hex[:12]}",
        created_at=datetime.now(timezone.utc).isoformat(),
        items=items,
    )

def write_bundle(bundle: EvidenceBundle, out: pathlib.Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(bundle.to_dict(), indent=2), encoding="utf-8")

def render_report(bundle: EvidenceBundle) -> str:
    lines = ["# Mock Field-Test Evidence Bundle", "",
        f"**bundle_id={bundle.bundle_id}**",
        "**THIS_IS_MOCK_EVIDENCE_ONLY**",
        "**REAL_TESTNET_SUBMIT_NOT_ALLOWED**",
        "**REAL_TRADING_NOT_ALLOWED**", ""]
    for item in bundle.items:
        lines.extend([f"## {item.title}", "", item.content, ""])
    lines.extend(["## Conclusion", "", "MOCK_FIELD_TEST_EVIDENCE_BUNDLE_READY", "TESTNET_SUBMIT_NOT_ALLOWED", ""])
    return "\n".join(lines)
