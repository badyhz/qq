"""Feishu dry-run renderer. Produces Feishu webhook payloads without sending."""
from __future__ import annotations

import json
import pathlib
from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass(frozen=True)
class FeishuPayload:
    payload_id: str
    alert_id: str
    msg_type: str
    title: str
    content: str
    ticker: str | None
    severity: str
    dry_run: bool = True
    actually_sent: bool = False

    def to_dict(self) -> dict:
        return {
            "payload_id": self.payload_id,
            "alert_id": self.alert_id,
            "msg_type": self.msg_type,
            "title": self.title,
            "content": self.content,
            "ticker": self.ticker,
            "severity": self.severity,
            "dry_run": self.dry_run,
            "actually_sent": self.actually_sent,
            "feishu_card": self._build_card(),
        }

    def _build_card(self) -> dict:
        return {
            "msg_type": "interactive",
            "card": {
                "header": {
                    "title": {"tag": "plain_text", "content": f"[DRY-RUN] {self.title}"},
                    "template": "red" if self.severity == "WARNING" else "blue",
                },
                "elements": [
                    {"tag": "div", "text": {"tag": "plain_text", "content": self.content}},
                    {"tag": "hr"},
                    {"tag": "note", "elements": [
                        {"tag": "plain_text", "content": f"Severity: {self.severity} | Ticker: {self.ticker or 'N/A'} | DRY-RUN ONLY"}
                    ]},
                ],
            },
        }


def render_feishu_payloads(alerts: list[dict]) -> list[FeishuPayload]:
    """Render Feishu payloads from alert events."""
    payloads = []
    now = datetime.now(timezone.utc).isoformat()
    for alert in alerts:
        payloads.append(FeishuPayload(
            payload_id=f"feishu_{len(payloads):04d}",
            alert_id=alert.get("alert_id", "unknown"),
            msg_type="interactive",
            title=alert.get("title", "Alert"),
            content=alert.get("body", ""),
            ticker=alert.get("ticker"),
            severity=alert.get("severity", "INFO"),
        ))
    return payloads


def write_payloads(payloads: list[FeishuPayload], out_path: pathlib.Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        "\n".join(json.dumps(p.to_dict()) for p in payloads) + ("\n" if payloads else ""),
        encoding="utf-8",
    )
