"""T18501 — Strategy Registry.

Pure deterministic. No I/O. No network.
Defines strategy registry schema and manages strategy metadata.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

RELEASE_HOLD_REQUIRED = "HOLD"

VALID_PROMOTION_STATUSES: tuple[str, ...] = (
    "RESEARCH_ONLY",
    "WATCHLIST_ONLY",
    "SHADOW_CANDIDATE",
    "SHADOW_ACTIVE",
    "TESTNET_DRY_RUN_CANDIDATE",
    "FROZEN",
    "REJECTED",
)

FORBIDDEN_PROMOTION_STATUSES: tuple[str, ...] = (
    "REAL_ACTIVE",
    "LIVE_TRADING",
    "AUTO_SUBMIT_ENABLED",
)

VALID_MODES: tuple[str, ...] = (
    "SHADOW_ONLY",
    "OFFLINE_ONLY",
    "DRY_RUN_ONLY",
    "TESTNET_DRY_RUN_PREP",
)

FORBIDDEN_MODES: tuple[str, ...] = (
    "REAL_ACTIVE",
    "LIVE_TRADING",
    "AUTO_SUBMIT",
)


@dataclass(frozen=True)
class StrategyRecord:
    """Single strategy registry entry."""
    strategy_id: str
    strategy_name: str
    market: str
    asset_type: str
    signal_type: str
    timeframe: str
    data_source: str
    risk_level: str
    current_mode: str
    evidence_refs: list[str]
    test_status: str
    promotion_status: str
    blockers: list[str]
    next_action: str

    def to_dict(self) -> dict:
        return {
            "strategy_id": self.strategy_id,
            "strategy_name": self.strategy_name,
            "market": self.market,
            "asset_type": self.asset_type,
            "signal_type": self.signal_type,
            "timeframe": self.timeframe,
            "data_source": self.data_source,
            "risk_level": self.risk_level,
            "current_mode": self.current_mode,
            "evidence_refs": self.evidence_refs,
            "test_status": self.test_status,
            "promotion_status": self.promotion_status,
            "blockers": self.blockers,
            "next_action": self.next_action,
        }


def validate_strategy_record(record: dict) -> list[str]:
    """Validate a strategy record. Returns list of errors."""
    errors: list[str] = []

    sid = record.get("strategy_id", "")
    if not sid:
        errors.append("missing_strategy_id")

    mode = record.get("current_mode", "")
    if mode in FORBIDDEN_MODES:
        errors.append(f"forbidden_mode={mode}")

    status = record.get("promotion_status", "")
    if status in FORBIDDEN_PROMOTION_STATUSES:
        errors.append(f"forbidden_promotion_status={status}")
    if status and status not in VALID_PROMOTION_STATUSES:
        errors.append(f"invalid_promotion_status={status}")

    return errors


def build_strategy_record(
    strategy_id: str,
    strategy_name: str,
    market: str,
    asset_type: str,
    signal_type: str,
    timeframe: str,
    data_source: str,
    risk_level: str,
    current_mode: str = "SHADOW_ONLY",
    evidence_refs: list[str] | None = None,
    test_status: str = "PENDING",
    promotion_status: str = "RESEARCH_ONLY",
    blockers: list[str] | None = None,
    next_action: str = "COLLECT_EVIDENCE",
) -> StrategyRecord:
    """Build a strategy record with validation."""
    return StrategyRecord(
        strategy_id=strategy_id,
        strategy_name=strategy_name,
        market=market,
        asset_type=asset_type,
        signal_type=signal_type,
        timeframe=timeframe,
        data_source=data_source,
        risk_level=risk_level,
        current_mode=current_mode,
        evidence_refs=evidence_refs or [],
        test_status=test_status,
        promotion_status=promotion_status,
        blockers=blockers or [],
        next_action=next_action,
    )


# Default strategy registry with known strategy directions
DEFAULT_STRATEGIES: list[dict] = [
    {
        "strategy_id": "macd_momentum_v1",
        "strategy_name": "MACD Second Momentum Strategy",
        "market": "crypto",
        "asset_type": "spot",
        "signal_type": "macd_crossover",
        "timeframe": "4h",
        "data_source": "binance_ohlcv",
        "risk_level": "MEDIUM",
        "promotion_status": "RESEARCH_ONLY",
        "blockers": ["needs_shadow_evidence", "needs_backtest_validation"],
        "next_action": "COLLECT_SHADOW_EVIDENCE",
    },
    {
        "strategy_id": "institutional_rally_model_1",
        "strategy_name": "Institutional Rally Model 1",
        "market": "us_stock",
        "asset_type": "equity",
        "signal_type": "volume_price_breakout",
        "timeframe": "daily",
        "data_source": "market_data_api",
        "risk_level": "MEDIUM",
        "promotion_status": "WATCHLIST_ONLY",
        "blockers": ["needs_live_data_validation"],
        "next_action": "VALIDATE_DATA_SOURCE",
    },
    {
        "strategy_id": "institutional_rally_model_2",
        "strategy_name": "Institutional Rally Model 2",
        "market": "us_stock",
        "asset_type": "equity",
        "signal_type": "earnings_momentum",
        "timeframe": "daily",
        "data_source": "market_data_api",
        "risk_level": "MEDIUM",
        "promotion_status": "WATCHLIST_ONLY",
        "blockers": ["needs_earnings_data_pipeline"],
        "next_action": "BUILD_DATA_PIPELINE",
    },
    {
        "strategy_id": "institutional_rally_model_3",
        "strategy_name": "Institutional Rally Model 3",
        "market": "us_stock",
        "asset_type": "equity",
        "signal_type": "sector_rotation",
        "timeframe": "weekly",
        "data_source": "market_data_api",
        "risk_level": "LOW",
        "promotion_status": "RESEARCH_ONLY",
        "blockers": ["needs_sector_data"],
        "next_action": "COLLECT_SECTOR_DATA",
    },
    {
        "strategy_id": "ai_infra_watchlist",
        "strategy_name": "AI Infrastructure Watchlist",
        "market": "us_stock",
        "asset_type": "equity",
        "signal_type": "thematic_watchlist",
        "timeframe": "daily",
        "data_source": "manual_curation",
        "risk_level": "LOW",
        "promotion_status": "WATCHLIST_ONLY",
        "blockers": [],
        "next_action": "MONITOR",
    },
    {
        "strategy_id": "cpo_watchlist",
        "strategy_name": "CPO Watchlist",
        "market": "us_stock",
        "asset_type": "equity",
        "signal_type": "thematic_watchlist",
        "timeframe": "daily",
        "data_source": "manual_curation",
        "risk_level": "LOW",
        "promotion_status": "WATCHLIST_ONLY",
        "blockers": [],
        "next_action": "MONITOR",
    },
    {
        "strategy_id": "silicon_photonics_watchlist",
        "strategy_name": "Silicon Photonics Watchlist",
        "market": "us_stock",
        "asset_type": "equity",
        "signal_type": "thematic_watchlist",
        "timeframe": "daily",
        "data_source": "manual_curation",
        "risk_level": "LOW",
        "promotion_status": "WATCHLIST_ONLY",
        "blockers": [],
        "next_action": "MONITOR",
    },
    {
        "strategy_id": "earnings_event_strategy",
        "strategy_name": "Earnings Event Strategy",
        "market": "us_stock",
        "asset_type": "equity",
        "signal_type": "earnings_surprise",
        "timeframe": "event",
        "data_source": "earnings_calendar",
        "risk_level": "HIGH",
        "promotion_status": "RESEARCH_ONLY",
        "blockers": ["needs_earnings_data_pipeline", "needs_event_backtest"],
        "next_action": "BUILD_EARNINGS_PIPELINE",
    },
    {
        "strategy_id": "stock_price_alert_watcher",
        "strategy_name": "Stock Price Alert Watcher",
        "market": "us_stock",
        "asset_type": "equity",
        "signal_type": "price_alert",
        "timeframe": "intraday",
        "data_source": "market_data_api",
        "risk_level": "LOW",
        "promotion_status": "WATCHLIST_ONLY",
        "blockers": [],
        "next_action": "MONITOR",
    },
    {
        "strategy_id": "binance_futures_scanner",
        "strategy_name": "Binance Futures Scanner",
        "market": "crypto",
        "asset_type": "futures",
        "signal_type": "volume_breakout",
        "timeframe": "1h",
        "data_source": "binance_futures_api",
        "risk_level": "HIGH",
        "promotion_status": "SHADOW_CANDIDATE",
        "blockers": ["needs_shadow_evidence", "needs_risk_validation"],
        "next_action": "COLLECT_SHADOW_EVIDENCE",
    },
    {
        "strategy_id": "options_call_strategy",
        "strategy_name": "Options Call Trading Plan",
        "market": "us_stock",
        "asset_type": "options",
        "signal_type": "volatility_play",
        "timeframe": "weekly",
        "data_source": "options_chain",
        "risk_level": "HIGH",
        "promotion_status": "RESEARCH_ONLY",
        "blockers": ["needs_options_data_source", "needs_greeks_model"],
        "next_action": "RESEARCH_OPTIONS_DATA",
    },
]


def build_default_registry() -> list[StrategyRecord]:
    """Build default strategy registry from known strategies."""
    records: list[StrategyRecord] = []
    for s in DEFAULT_STRATEGIES:
        records.append(build_strategy_record(**s))
    return records


def check_unique_ids(records: list[StrategyRecord]) -> bool:
    """Check all strategy IDs are unique."""
    ids = [r.strategy_id for r in records]
    return len(ids) == len(set(ids))


def compute_registry_hash(records: list[StrategyRecord]) -> str:
    raw = json.dumps([r.to_dict() for r in records], sort_keys=True, indent=2)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def render_registry_markdown(records: list[StrategyRecord]) -> str:
    lines = [
        "# Strategy Registry Overview",
        "",
        f"**Total strategies:** {len(records)}",
        f"**All IDs unique:** {check_unique_ids(records)}",
        "",
        "## Promotion Status Summary",
        "",
    ]

    status_counts: dict[str, int] = {}
    for r in records:
        status_counts[r.promotion_status] = status_counts.get(r.promotion_status, 0) + 1
    for s, count in sorted(status_counts.items()):
        lines.append(f"- **{s}:** {count}")

    lines.append("")
    lines.append("## Strategy Details")
    lines.append("")

    for r in records:
        lines.append(f"### {r.strategy_id}")
        lines.append("")
        lines.append(f"- **Name:** {r.strategy_name}")
        lines.append(f"- **Market:** {r.market}")
        lines.append(f"- **Asset type:** {r.asset_type}")
        lines.append(f"- **Signal type:** {r.signal_type}")
        lines.append(f"- **Timeframe:** {r.timeframe}")
        lines.append(f"- **Risk level:** {r.risk_level}")
        lines.append(f"- **Current mode:** {r.current_mode}")
        lines.append(f"- **Promotion status:** {r.promotion_status}")
        lines.append(f"- **Test status:** {r.test_status}")
        lines.append(f"- **Next action:** {r.next_action}")
        if r.blockers:
            lines.append(f"- **Blockers:** {', '.join(r.blockers)}")
        lines.append("")

    lines.append("---")
    lines.append("REGISTRY ONLY. NO REAL TRADING AUTHORIZED.")
    lines.append("")

    return "\n".join(lines)


def write_json(records: list[StrategyRecord], out_path) -> None:
    import pathlib
    p = pathlib.Path(out_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(
        json.dumps([r.to_dict() for r in records], indent=2),
        encoding="utf-8",
    )


def write_manifest(records: list[StrategyRecord], out_path, release_hold: str) -> None:
    import pathlib
    p = pathlib.Path(out_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    status_counts: dict[str, int] = {}
    for r in records:
        status_counts[r.promotion_status] = status_counts.get(r.promotion_status, 0) + 1
    manifest = {
        "total_strategies": len(records),
        "all_ids_unique": check_unique_ids(records),
        "status_counts": dict(sorted(status_counts.items())),
        "release_hold": release_hold,
        "simulation_only": True,
        "registry_hash": compute_registry_hash(records),
    }
    p.write_text(json.dumps(manifest, indent=2), encoding="utf-8")


def write_markdown(records: list[StrategyRecord], out_path) -> None:
    import pathlib
    p = pathlib.Path(out_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(render_registry_markdown(records), encoding="utf-8")
