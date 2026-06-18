"""Feishu alert send gate — controlled send with dry-run default. No secrets, no orders, no auto-send."""
from __future__ import annotations

import json
import urllib.request
import urllib.error
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional


SEND_GATE_SAFETY_FLAGS = [
    "PAPER_ONLY",
    "FEISHU_SEND_GATE",
    "NO_SECRET",
    "NO_ENV_READ",
    "NO_ACCOUNT",
    "NO_ORDER",
    "NO_REAL_ORDER",
    "NO_TESTNET",
    "NO_LIVE",
    "NO_AUTO_SEND",
    "REQUIRES_EXPLICIT_ALLOW_SEND",
    "REQUIRES_EXPLICIT_WEBHOOK_URL",
]


@dataclass(frozen=True)
class SendResult:
    date: str
    payload_count: int
    dry_run: bool
    allow_send: bool
    webhook_url_provided: bool
    send_attempted: bool
    sent_count: int
    failed_count: int
    errors: list[dict[str, str]]
    safety_passed: bool
    actually_sent: bool
    safety_flags: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "date": self.date,
            "payload_count": self.payload_count,
            "dry_run": self.dry_run,
            "allow_send": self.allow_send,
            "webhook_url_provided": self.webhook_url_provided,
            "send_attempted": self.send_attempted,
            "sent_count": self.sent_count,
            "failed_count": self.failed_count,
            "errors": list(self.errors),
            "safety_passed": self.safety_passed,
            "actually_sent": self.actually_sent,
            "safety_flags": list(self.safety_flags),
        }


def validate_payload_file(payload_data: dict[str, Any]) -> tuple[bool, list[str]]:
    """Validate a payload file has required fields and safety flags."""
    issues = []

    if not isinstance(payload_data, dict):
        return False, ["payload_data is not a dict"]

    # Check required top-level fields
    for field in ["date", "payload_count", "payloads", "safety_flags"]:
        if field not in payload_data:
            issues.append(f"missing field: {field}")

    # Check safety flags
    payload_flags = payload_data.get("safety_flags", [])
    required_flags = {"PAPER_ONLY", "NO_ORDER", "NO_REAL_ORDER", "NO_SECRET"}
    missing = required_flags - set(payload_flags)
    if missing:
        issues.append(f"missing safety flags: {missing}")

    # Check dry_run_only
    if payload_data.get("dry_run_only") is not True:
        issues.append("dry_run_only must be True")

    # Check not_order_payload
    if payload_data.get("not_order_payload") is not True:
        issues.append("not_order_payload must be True")

    # Check actually_sent is False
    if payload_data.get("actually_sent") is not False:
        issues.append("actually_sent must be False before gate send")

    # Check webhook_send_attempted is False
    if payload_data.get("webhook_send_attempted") is not False:
        issues.append("webhook_send_attempted must be False before gate send")

    # Validate payloads list
    payloads = payload_data.get("payloads", [])
    if not isinstance(payloads, list):
        issues.append("payloads must be a list")
    elif len(payloads) == 0:
        issues.append("payloads list is empty")

    return len(issues) == 0, issues


def validate_safety_flags(payload_data: dict[str, Any]) -> tuple[bool, list[str]]:
    """Check that all required safety flags are present in the payload."""
    payload_flags = set(payload_data.get("safety_flags", []))
    gate_flags = set(SEND_GATE_SAFETY_FLAGS)
    # Payload must have at least PAPER_ONLY, NO_ORDER, NO_SECRET
    required = {"PAPER_ONLY", "NO_ORDER", "NO_REAL_ORDER", "NO_SECRET"}
    missing = required - payload_flags
    if missing:
        return False, [f"missing required safety flags: {missing}"]
    return True, []


def build_feishu_request_body(payload: dict[str, Any]) -> dict[str, Any]:
    """Extract the feishu_payload from a payload entry for webhook POST."""
    return payload.get("feishu_payload", {})


def send_payloads_to_webhook(
    payloads: list[dict[str, Any]],
    webhook_url: str,
) -> tuple[int, int, list[dict[str, str]]]:
    """Send payloads to Feishu webhook. Returns (sent_count, failed_count, errors)."""
    sent = 0
    failed = 0
    errors = []

    for i, payload in enumerate(payloads):
        body = build_feishu_request_body(payload)
        if not body:
            failed += 1
            errors.append({"index": str(i), "error": "empty feishu_payload"})
            continue

        try:
            data = json.dumps(body).encode("utf-8")
            req = urllib.request.Request(
                webhook_url,
                data=data,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                resp_body = resp.read().decode("utf-8")
                resp_json = json.loads(resp_body)
                if resp_json.get("code") == 0 or resp_json.get("StatusCode") == 0:
                    sent += 1
                else:
                    failed += 1
                    errors.append({"index": str(i), "error": f"feishu error: {resp_body}"})
        except Exception as e:
            failed += 1
            errors.append({"index": str(i), "error": str(e)})

    return sent, failed, errors


def run_send_gate(
    payload_file_path: str,
    allow_send: bool = False,
    webhook_url: Optional[str] = None,
) -> SendResult:
    """Run the send gate. Default dry-run. Only sends when allow_send=True and webhook_url provided."""
    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    errors: list[dict[str, str]] = []

    # Load payload file
    try:
        with open(payload_file_path) as f:
            payload_data = json.load(f)
    except Exception as e:
        return SendResult(
            date=date_str, payload_count=0,
            dry_run=True, allow_send=allow_send,
            webhook_url_provided=webhook_url is not None,
            send_attempted=False, sent_count=0, failed_count=0,
            errors=[{"error": f"failed to load payload file: {e}"}],
            safety_passed=False, actually_sent=False,
            safety_flags=list(SEND_GATE_SAFETY_FLAGS),
        )

    # Validate payload
    valid, issues = validate_payload_file(payload_data)
    if not valid:
        return SendResult(
            date=date_str, payload_count=0,
            dry_run=True, allow_send=allow_send,
            webhook_url_provided=webhook_url is not None,
            send_attempted=False, sent_count=0, failed_count=0,
            errors=[{"error": f"payload validation failed: {iss}"} for iss in issues],
            safety_passed=False, actually_sent=False,
            safety_flags=list(SEND_GATE_SAFETY_FLAGS),
        )

    # Validate safety flags
    safety_ok, safety_issues = validate_safety_flags(payload_data)
    if not safety_ok:
        return SendResult(
            date=date_str, payload_count=0,
            dry_run=True, allow_send=allow_send,
            webhook_url_provided=webhook_url is not None,
            send_attempted=False, sent_count=0, failed_count=0,
            errors=[{"error": f"safety flag check failed: {iss}"} for iss in safety_issues],
            safety_passed=False, actually_sent=False,
            safety_flags=list(SEND_GATE_SAFETY_FLAGS),
        )

    payloads = payload_data.get("payloads", [])
    payload_count = len(payloads)

    # Check if send is allowed
    if not allow_send:
        return SendResult(
            date=date_str, payload_count=payload_count,
            dry_run=True, allow_send=False,
            webhook_url_provided=webhook_url is not None,
            send_attempted=False, sent_count=0, failed_count=0,
            errors=[],
            safety_passed=True, actually_sent=False,
            safety_flags=list(SEND_GATE_SAFETY_FLAGS),
        )

    if not webhook_url:
        return SendResult(
            date=date_str, payload_count=payload_count,
            dry_run=True, allow_send=True,
            webhook_url_provided=False,
            send_attempted=False, sent_count=0, failed_count=0,
            errors=[{"error": "webhook_url not provided"}],
            safety_passed=True, actually_sent=False,
            safety_flags=list(SEND_GATE_SAFETY_FLAGS),
        )

    # Send
    sent, failed, send_errors = send_payloads_to_webhook(payloads, webhook_url)

    return SendResult(
        date=date_str, payload_count=payload_count,
        dry_run=False, allow_send=True,
        webhook_url_provided=True,
        send_attempted=True, sent_count=sent, failed_count=failed,
        errors=send_errors,
        safety_passed=True, actually_sent=sent > 0,
        safety_flags=list(SEND_GATE_SAFETY_FLAGS),
    )
