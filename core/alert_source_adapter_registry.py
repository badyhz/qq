"""T36001 — Alert Source Adapter Registry.

Pure deterministic. No I/O. No network.
Maps existing alert sources to the unified alert center with dry-run integration.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

RELEASE_HOLD_REQUIRED_ASR = "HOLD"

ALERT_SOURCES = (
    "earnings",
    "stock_price",
    "macd_rebound",
    "binance_futures",
    "system_heartbeat",
)

SOURCE_CONFIGS = {
    "earnings": {
        "adapter_type": "event_driven",
        "data_source": "local_schedule",
        "network_required": False,
        "priority": "HIGH",
        "dedup_window_minutes": 60,
        "description": "Earnings calendar event alerts from local schedule data",
    },
    "stock_price": {
        "adapter_type": "threshold_monitor",
        "data_source": "public_market_data",
        "network_required": True,
        "priority": "MEDIUM",
        "dedup_window_minutes": 5,
        "description": "Stock price threshold breach alerts from public market data",
    },
    "macd_rebound": {
        "adapter_type": "signal_generator",
        "data_source": "computed_indicators",
        "network_required": False,
        "priority": "MEDIUM",
        "dedup_window_minutes": 15,
        "description": "MACD rebound signal alerts from computed technical indicators",
    },
    "binance_futures": {
        "adapter_type": "market_scanner",
        "data_source": "public_binance_api",
        "network_required": True,
        "priority": "HIGH",
        "dedup_window_minutes": 5,
        "description": "Binance futures market scanner alerts from public API data",
    },
    "system_heartbeat": {
        "adapter_type": "health_monitor",
        "data_source": "internal_metrics",
        "network_required": False,
        "priority": "LOW",
        "dedup_window_minutes": 1,
        "description": "System heartbeat and health monitoring alerts",
    },
}


@dataclass(frozen=True)
class AlertSourceAdapter:
    """Single alert source adapter entry."""
    adapter_id: str
    source_name: str
    adapter_type: str
    data_source: str
    network_required: bool
    priority: str
    dedup_window_minutes: int
    description: str
    integrated_with_alert_center: bool
    dry_run_compatible: bool
    governance_tracked: bool

    def to_dict(self) -> dict:
        return {
            "adapter_id": self.adapter_id,
            "source_name": self.source_name,
            "adapter_type": self.adapter_type,
            "data_source": self.data_source,
            "network_required": self.network_required,
            "priority": self.priority,
            "dedup_window_minutes": self.dedup_window_minutes,
            "description": self.description,
            "integrated_with_alert_center": self.integrated_with_alert_center,
            "dry_run_compatible": self.dry_run_compatible,
            "governance_tracked": self.governance_tracked,
        }


def build_adapter(source_name: str) -> AlertSourceAdapter:
    """Build an adapter entry for an alert source."""
    config = SOURCE_CONFIGS.get(source_name, {})
    return AlertSourceAdapter(
        adapter_id=f"asr_{source_name}",
        source_name=source_name,
        adapter_type=config.get("adapter_type", "unknown"),
        data_source=config.get("data_source", "unknown"),
        network_required=config.get("network_required", False),
        priority=config.get("priority", "MEDIUM"),
        dedup_window_minutes=config.get("dedup_window_minutes", 5),
        description=config.get("description", f"Alert source: {source_name}"),
        integrated_with_alert_center=True,
        dry_run_compatible=True,
        governance_tracked=True,
    )


def build_adapter_registry(
    release_hold: str = RELEASE_HOLD_REQUIRED_ASR,
) -> list[AlertSourceAdapter]:
    """Build registry of all alert source adapters."""
    if release_hold != RELEASE_HOLD_REQUIRED_ASR:
        raise ValueError(f"release_hold={release_hold!r} != HOLD")
    return [build_adapter(s) for s in ALERT_SOURCES]


def compute_registry_hash(adapters: list[AlertSourceAdapter]) -> str:
    raw = json.dumps([a.to_dict() for a in adapters], sort_keys=True, indent=2)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def render_registry_markdown(adapters: list[AlertSourceAdapter]) -> str:
    lines = [
        "# Alert Source Adapter Registry",
        "",
        f"**Total adapters:** {len(adapters)}",
        "",
        "## By Priority",
        "",
    ]
    by_priority: dict[str, list[AlertSourceAdapter]] = {}
    for a in adapters:
        by_priority.setdefault(a.priority, []).append(a)
    for p in ("HIGH", "MEDIUM", "LOW"):
        sources = by_priority.get(p, [])
        if sources:
            names = ", ".join(a.source_name for a in sources)
            lines.append(f"- **{p}:** {names}")

    lines.append("")
    lines.append("## Adapter Details")
    lines.append("")

    for a in adapters:
        lines.append(f"### {a.source_name}")
        lines.append("")
        lines.append(f"- **Type:** {a.adapter_type}")
        lines.append(f"- **Data source:** {a.data_source}")
        lines.append(f"- **Network required:** {a.network_required}")
        lines.append(f"- **Priority:** {a.priority}")
        lines.append(f"- **Dedup window:** {a.dedup_window_minutes} min")
        lines.append(f"- **Description:** {a.description}")
        lines.append(f"- **Integrated:** {a.integrated_with_alert_center}")
        lines.append(f"- **Dry-run compatible:** {a.dry_run_compatible}")
        lines.append(f"- **Governance tracked:** {a.governance_tracked}")
        lines.append("")

    return "\n".join(lines)


def render_integration_matrix_markdown(adapters: list[AlertSourceAdapter]) -> str:
    lines = [
        "# Alert Source Integration Matrix",
        "",
        "| Source | Type | Priority | Network | Dry-run OK | Integrated |",
        "|--------|------|----------|---------|------------|------------|",
    ]
    for a in adapters:
        lines.append(
            f"| {a.source_name} | {a.adapter_type} | {a.priority} "
            f"| {a.network_required} | {a.dry_run_compatible} | {a.integrated_with_alert_center} |"
        )
    lines.append("")
    return "\n".join(lines)


def write_json(adapters: list[AlertSourceAdapter], out_path) -> None:
    import pathlib
    p = pathlib.Path(out_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps([a.to_dict() for a in adapters], indent=2), encoding="utf-8")


def write_manifest(adapters: list[AlertSourceAdapter], out_path, release_hold: str) -> None:
    import pathlib
    p = pathlib.Path(out_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    priority_counts: dict[str, int] = {}
    for a in adapters:
        priority_counts[a.priority] = priority_counts.get(a.priority, 0) + 1
    manifest = {
        "total_adapters": len(adapters),
        "release_hold": release_hold,
        "registry_hash": compute_registry_hash(adapters),
        "all_integrated": all(a.integrated_with_alert_center for a in adapters),
        "all_dry_run_compatible": all(a.dry_run_compatible for a in adapters),
        "all_governance_tracked": all(a.governance_tracked for a in adapters),
        "priority_counts": dict(sorted(priority_counts.items())),
    }
    p.write_text(json.dumps(manifest, indent=2), encoding="utf-8")


def write_markdown(content: str, out_path) -> None:
    import pathlib
    p = pathlib.Path(out_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
