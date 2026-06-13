"""T33001 — Testnet Dry-run Adapter Registry.

Pure deterministic. No I/O. No network.
Wraps TESTNET_DRY_RUN_ONLY scripts in dry-run adapter governance.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

from core.untracked_runtime_inventory import (
    UntrackedFileRecord,
    build_inventory,
    RELEASE_HOLD_REQUIRED,
)

RELEASE_HOLD_REQUIRED_TDR = "HOLD"

ADAPTER_CONFIGS = {
    "scripts/replay_shadow_order_plans_as_testnet_dry.py": {
        "adapter_type": "dry_run_replay",
        "description": "Replays shadow order plans as testnet dry-run payloads",
        "network_access": "public_exchange_info_only",
        "submit_path": "explicitly_stubbed",
        "key_usage": "none",
    },
    "scripts/verify_testnet_repair_scenarios.py": {
        "adapter_type": "dry_run_diagnostic",
        "description": "Read-only testnet diagnostic with repair plan generation",
        "network_access": "testnet_read_only",
        "submit_path": "force_dry_run_locked",
        "key_usage": "read_only_no_secret",
    },
}


@dataclass(frozen=True)
class DryRunAdapterEntry:
    """Single dry-run adapter registry entry."""
    entry_id: str
    path: str
    adapter_type: str
    description: str
    risk_category: str
    risk_reason: str
    network_access: str
    submit_path: str
    key_usage: str
    has_network_calls: bool
    has_api_keys: bool
    dry_run_locked: bool
    no_submit: bool
    governance_tracked: bool

    def to_dict(self) -> dict:
        return {
            "entry_id": self.entry_id,
            "path": self.path,
            "adapter_type": self.adapter_type,
            "description": self.description,
            "risk_category": self.risk_category,
            "risk_reason": self.risk_reason,
            "network_access": self.network_access,
            "submit_path": self.submit_path,
            "key_usage": self.key_usage,
            "has_network_calls": self.has_network_calls,
            "has_api_keys": self.has_api_keys,
            "dry_run_locked": self.dry_run_locked,
            "no_submit": self.no_submit,
            "governance_tracked": self.governance_tracked,
        }


def _safe_id(path: str) -> str:
    return path.replace("/", "__").replace("\\", "__").replace(".", "_")


def build_adapter_entry(record: UntrackedFileRecord) -> DryRunAdapterEntry:
    """Build a dry-run adapter entry from an inventory record."""
    config = ADAPTER_CONFIGS.get(record.path, {})
    return DryRunAdapterEntry(
        entry_id=f"tdr_{_safe_id(record.path)}",
        path=record.path,
        adapter_type=config.get("adapter_type", "generic_dry_run"),
        description=config.get("description", "Testnet dry-run script"),
        risk_category=record.risk_category,
        risk_reason=record.risk_reason,
        network_access=config.get("network_access", "unknown"),
        submit_path=config.get("submit_path", "unknown"),
        key_usage=config.get("key_usage", "unknown"),
        has_network_calls=record.has_network_calls,
        has_api_keys=record.has_api_keys,
        dry_run_locked=True,
        no_submit=not record.has_order_submit,
        governance_tracked=True,
    )


def build_adapter_registry(
    release_hold: str = RELEASE_HOLD_REQUIRED_TDR,
) -> list[DryRunAdapterEntry]:
    """Build registry of all testnet dry-run adapter scripts."""
    if release_hold != RELEASE_HOLD_REQUIRED_TDR:
        raise ValueError(f"release_hold={release_hold!r} != HOLD")
    records = build_inventory(release_hold=RELEASE_HOLD_REQUIRED)
    return [
        build_adapter_entry(r)
        for r in records
        if r.risk_category == "TESTNET_DRY_RUN_ONLY"
    ]


def compute_registry_hash(entries: list[DryRunAdapterEntry]) -> str:
    raw = json.dumps([e.to_dict() for e in entries], sort_keys=True, indent=2)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def render_registry_markdown(entries: list[DryRunAdapterEntry]) -> str:
    lines = [
        "# Testnet Dry-run Adapter Registry",
        "",
        f"**Total adapters:** {len(entries)}",
        "",
        "## Adapter Details",
        "",
    ]
    for e in entries:
        lines.append(f"### {e.path}")
        lines.append("")
        lines.append(f"- **Adapter type:** {e.adapter_type}")
        lines.append(f"- **Description:** {e.description}")
        lines.append(f"- **Risk reason:** {e.risk_reason}")
        lines.append(f"- **Network access:** {e.network_access}")
        lines.append(f"- **Submit path:** {e.submit_path}")
        lines.append(f"- **Key usage:** {e.key_usage}")
        lines.append(f"- **Dry-run locked:** {e.dry_run_locked}")
        lines.append(f"- **No submit:** {e.no_submit}")
        lines.append(f"- **Governance tracked:** {e.governance_tracked}")
        lines.append("")
    return "\n".join(lines)


def write_json(entries: list[DryRunAdapterEntry], out_path) -> None:
    import pathlib
    p = pathlib.Path(out_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps([e.to_dict() for e in entries], indent=2), encoding="utf-8")


def write_manifest(entries: list[DryRunAdapterEntry], out_path, release_hold: str) -> None:
    import pathlib
    p = pathlib.Path(out_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    type_counts: dict[str, int] = {}
    for e in entries:
        type_counts[e.adapter_type] = type_counts.get(e.adapter_type, 0) + 1
    manifest = {
        "total_adapters": len(entries),
        "release_hold": release_hold,
        "registry_hash": compute_registry_hash(entries),
        "all_dry_run_locked": all(e.dry_run_locked for e in entries),
        "all_no_submit": all(e.no_submit for e in entries),
        "all_governance_tracked": all(e.governance_tracked for e in entries),
        "adapter_type_counts": dict(sorted(type_counts.items())),
    }
    p.write_text(json.dumps(manifest, indent=2), encoding="utf-8")


def write_markdown(content: str, out_path) -> None:
    import pathlib
    p = pathlib.Path(out_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
