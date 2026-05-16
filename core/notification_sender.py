from __future__ import annotations

import json
import os
import re
import smtplib
from email.message import EmailMessage
from typing import Any
from urllib.error import URLError
from urllib.request import Request, urlopen

from core.risk_event_logger import log_risk_event
from core.trade_logger import read_jsonl_rows


def redact_secrets(text: str) -> str:
    safe = str(text or "")
    patterns = [
        r"(?i)(api[_-]?key\s*[:=]\s*)([^\s,;]+)",
        r"(?i)(api[_-]?secret\s*[:=]\s*)([^\s,;]+)",
        r"(?i)(binance_testnet_api_key\s*[:=]\s*)([^\s,;]+)",
        r"(?i)(binance_testnet_api_secret\s*[:=]\s*)([^\s,;]+)",
        r"(?i)(token\s*[:=]\s*)([^\s,;]+)",
        r"(?i)(password\s*[:=]\s*)([^\s,;]+)",
        r"(?i)(secret\s*[:=]\s*)([^\s,;]+)",
    ]
    for pattern in patterns:
        safe = re.sub(pattern, r"\1***", safe)
    return safe


def truncate_message(text: str, max_chars: int = 3500) -> tuple[str, bool]:
    content = str(text or "")
    if len(content) <= max_chars:
        return content, False
    return content[:max_chars] + "\n... [truncated]", True


def _load_text(path: str) -> str:
    if not path:
        return ""
    try:
        with open(path, "r", encoding="utf-8") as handle:
            return handle.read()
    except OSError:
        return ""


def _summarize_risk_events(path: str, max_events: int) -> tuple[str, dict[str, int]]:
    rows = read_jsonl_rows(path) if path else []
    severity_count: dict[str, int] = {}
    lines: list[str] = []
    for row in rows[-max(0, int(max_events)):]:
        severity = str(row.get("severity", "")).upper() or "UNKNOWN"
        severity_count[severity] = int(severity_count.get(severity, 0)) + 1
        lines.append(f"[{severity}] {row.get('event_type', '')}: {row.get('message', '')}")
    return "\n".join(lines), severity_count


def _summarize_candidates(path: str) -> dict[str, int]:
    rows = read_jsonl_rows(path) if path else []
    summary = {
        "total": len(rows),
        "pending": 0,
        "approved": 0,
        "rejected": 0,
        "expired": 0,
        "submitted": 0,
        "skipped": 0,
    }
    for row in rows:
        status = str(row.get("status", "")).strip().upper()
        key = status.lower()
        if key in summary:
            summary[key] = int(summary[key]) + 1
    return summary


def build_digest_message(
    *,
    env: str,
    title: str,
    summary_md: str = "",
    risk_events_jsonl: str = "",
    candidates_jsonl: str = "",
    acceptance_report_md: str = "",
    max_events: int = 10,
) -> dict[str, Any]:
    risk_text, severity_count = _summarize_risk_events(risk_events_jsonl, max_events=max_events)
    candidates_summary = _summarize_candidates(candidates_jsonl)
    summary_text = _load_text(summary_md)
    acceptance_text = _load_text(acceptance_report_md)

    message = "\n".join(
        [
            f"# {title}",
            f"env={env}",
            "",
            "## Candidates",
            json.dumps(candidates_summary, ensure_ascii=False),
            "",
            "## Risk Events (recent)",
            risk_text or "none",
            "",
            "## Observation Summary",
            summary_text.strip() or "none",
            "",
            "## Acceptance Report",
            acceptance_text.strip() or "none",
        ]
    )
    redacted = redact_secrets(message)
    truncated_message, truncated = truncate_message(redacted)
    return {
        "message": truncated_message,
        "truncated": truncated,
        "severity_count": severity_count,
        "candidates_summary": candidates_summary,
    }


def send_notification(
    *,
    env: str,
    channel: str,
    title: str,
    message: str,
    dry_run: bool = True,
    send: bool = False,
) -> dict[str, Any]:
    selected_channel = str(channel or "stdout").strip().lower()
    safe_message = redact_secrets(message)
    safe_message, truncated = truncate_message(safe_message)

    if dry_run or (not send):
        log_risk_event(
            env=env,
            symbol="",
            component="notification_sender",
            event_type="NOTIFICATION_DRY_RUN",
            message=f"notification dry-run channel={selected_channel}",
            context={"channel": selected_channel, "send": bool(send), "dry_run": bool(dry_run)},
            action_required="none",
            event_scope="LOCAL_DRY_RUN",
            is_test_event=True,
        )
        if selected_channel == "stdout":
            print(safe_message)
        return {
            "ok": True,
            "status": "dry_run_only",
            "channel": selected_channel,
            "truncated": truncated,
            "missing_config": False,
        }

    try:
        if selected_channel == "stdout":
            print(safe_message)
            return {"ok": True, "status": "sent_stdout", "channel": selected_channel, "truncated": truncated, "missing_config": False}

        if selected_channel == "telegram":
            token = str(os.getenv("TELEGRAM_BOT_TOKEN", "")).strip()
            chat_id = str(os.getenv("TELEGRAM_CHAT_ID", "")).strip()
            if not token or not chat_id:
                return {"ok": False, "status": "missing_config", "channel": selected_channel, "truncated": truncated, "missing_config": True}
            url = f"https://api.telegram.org/bot{token}/sendMessage"
            payload = json.dumps({"chat_id": chat_id, "text": safe_message}).encode("utf-8")
            req = Request(url, data=payload, method="POST", headers={"Content-Type": "application/json"})
            with urlopen(req, timeout=10):
                pass
            return {"ok": True, "status": "sent", "channel": selected_channel, "truncated": truncated, "missing_config": False}

        if selected_channel == "wecom":
            webhook = str(os.getenv("WECOM_WEBHOOK_URL", "")).strip()
            if not webhook:
                return {"ok": False, "status": "missing_config", "channel": selected_channel, "truncated": truncated, "missing_config": True}
            payload = json.dumps({"msgtype": "text", "text": {"content": safe_message}}).encode("utf-8")
            req = Request(webhook, data=payload, method="POST", headers={"Content-Type": "application/json"})
            with urlopen(req, timeout=10):
                pass
            return {"ok": True, "status": "sent", "channel": selected_channel, "truncated": truncated, "missing_config": False}

        if selected_channel == "email":
            host = str(os.getenv("SMTP_HOST", "")).strip()
            port = int(str(os.getenv("SMTP_PORT", "0")).strip() or "0")
            user = str(os.getenv("SMTP_USER", "")).strip()
            password = str(os.getenv("SMTP_PASSWORD", "")).strip()
            to_addr = str(os.getenv("ALERT_EMAIL_TO", "")).strip()
            from_addr = str(os.getenv("ALERT_EMAIL_FROM", "")).strip()
            if not host or not port or not to_addr or not from_addr:
                return {"ok": False, "status": "missing_config", "channel": selected_channel, "truncated": truncated, "missing_config": True}
            msg = EmailMessage()
            msg["Subject"] = title
            msg["From"] = from_addr
            msg["To"] = to_addr
            msg.set_content(safe_message)
            with smtplib.SMTP(host, port, timeout=10) as server:
                if user and password:
                    server.starttls()
                    server.login(user, password)
                server.send_message(msg)
            return {"ok": True, "status": "sent", "channel": selected_channel, "truncated": truncated, "missing_config": False}

        return {"ok": False, "status": "unsupported_channel", "channel": selected_channel, "truncated": truncated, "missing_config": False}
    except (OSError, URLError, smtplib.SMTPException) as exc:
        log_risk_event(
            env=env,
            symbol="",
            component="notification_sender",
            event_type="NOTIFICATION_SEND_FAILED",
            message=f"notification send failed channel={selected_channel}",
            context={"channel": selected_channel, "error": str(exc)},
            action_required="check_notification_config_or_network",
        )
        return {
            "ok": False,
            "status": "send_failed",
            "channel": selected_channel,
            "truncated": truncated,
            "missing_config": False,
            "error": str(exc),
        }
