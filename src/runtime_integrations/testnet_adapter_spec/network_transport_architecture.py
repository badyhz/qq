"""Network transport architecture specification."""
from __future__ import annotations
import json, pathlib
from dataclasses import dataclass

@dataclass(frozen=True)
class TransportSection:
    section_id: str
    title: str
    content: str
    def to_dict(self) -> dict:
        return {"section_id": self.section_id, "title": self.title, "content": self.content}

SECTIONS = (
    TransportSection("abstraction", "Transport Abstraction", "Abstract HTTP client interface. Architecture-only — no implementation."),
    TransportSection("timeout_policy", "Timeout Policy", "Connect timeout: 5s. Read timeout: 10s. Total timeout: 30s."),
    TransportSection("retry_policy", "Retry Policy", "Exponential backoff: 1s, 2s, 4s, 8s. Max 4 retries. Only on 5xx and timeout."),
    TransportSection("rate_limit_policy", "Rate Limit Policy", "Per-endpoint rate limits. Order: 10/s. Cancel: 10/s. General: 1200/min. Backoff on 429."),
    TransportSection("circuit_breaker", "Circuit Breaker Policy", "Open after 5 consecutive failures. Half-open after 30s. Closed after 3 successes."),
    TransportSection("idempotency", "Idempotency Key Policy", "UUID v4 idempotency key per order request. Server-side dedup recommended."),
    TransportSection("response_validation", "Response Validation", "Validate HTTP status, content-type, JSON schema. Reject malformed responses."),
    TransportSection("malformed_response", "Malformed Response Handling", "Log error, reject response, increment error counter. No retry on malformed."),
    TransportSection("partial_response", "Partial Response Handling", "Detect partial JSON, log error, reject. No partial processing."),
    TransportSection("duplicate_response", "Duplicate Response Handling", "Idempotency key dedup. Log warning on duplicate detection."),
    TransportSection("out_of_order", "Out-of-Order Response Handling", "Sequence number tracking. Reject out-of-order. Log warning."),
    TransportSection("stale_response", "Stale Response Handling", "Timestamp comparison. Reject responses older than 30s. Log warning."),
    TransportSection("audit_event", "Audit Event Emission", "Every request/response logged: method, path, status, latency, error. Tamper-evident."),
    TransportSection("kill_switch_dep", "Kill Switch Dependency", "Kill switch blocks all outbound requests when armed. Not implemented."),
)

def get_sections() -> tuple[TransportSection, ...]:
    return SECTIONS

def write_architecture(sections: tuple[TransportSection, ...], out: pathlib.Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps([s.to_dict() for s in sections], indent=2), encoding="utf-8")

def render_report(sections: tuple[TransportSection, ...]) -> str:
    lines = ["# Network Transport Architecture", "",
        "**transport_mode=ARCHITECTURE_ONLY**",
        "**network_client_implemented=false**",
        "**network_called=false**",
        "**submit_allowed=false**", ""]
    for s in sections:
        lines.extend([f"## {s.title}", "", s.content, ""])
    lines.extend(["## Conclusion", "", "NETWORK_TRANSPORT_ARCHITECTURE_READY", "TESTNET_SUBMIT_NOT_ALLOWED", ""])
    return "\n".join(lines)
