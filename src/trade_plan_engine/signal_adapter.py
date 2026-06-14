"""Signal adapter: reads scanner outputs and converts to SignalCandidate."""
from __future__ import annotations
import csv, json, pathlib, uuid
from dataclasses import dataclass
from datetime import datetime, timezone

from src.trade_plan_engine.models import SignalCandidate, new_id, utc_now_iso


@dataclass(frozen=True)
class SignalAdapterResult:
    adapter_id: str
    created_at: str
    scanner_path: str
    candidates: tuple[SignalCandidate, ...]
    total_raw: int
    total_deduplicated: int
    total_valid: int
    final_verdict: str

    def to_dict(self) -> dict:
        return {
            "adapter_id": self.adapter_id, "created_at": self.created_at,
            "scanner_path": self.scanner_path,
            "candidates": [c.to_dict() for c in self.candidates],
            "total_raw": self.total_raw,
            "total_deduplicated": self.total_deduplicated,
            "total_valid": self.total_valid,
            "final_verdict": self.final_verdict,
        }


def _read_csv(path: pathlib.Path) -> list[dict]:
    if not path.exists():
        return []
    try:
        with open(path, newline="", encoding="utf-8") as f:
            return list(csv.DictReader(f))
    except Exception:
        return []


def _read_jsonl(path: pathlib.Path) -> list[dict]:
    if not path.exists():
        return []
    rows = []
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line:
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    except Exception:
        pass
    return rows


def _safe_float(val, default: float = 0.0) -> float:
    try:
        return float(val)
    except (TypeError, ValueError):
        return default


def _safe_bool(val) -> bool:
    if isinstance(val, bool):
        return val
    if isinstance(val, str):
        return val.strip().lower() in ("true", "1", "yes")
    return bool(val)


def _row_to_candidate(row: dict, source: str = "macd_rebound_scanner") -> SignalCandidate | None:
    symbol = row.get("symbol", "").strip()
    price = _safe_float(row.get("price"))
    if not symbol or price <= 0:
        return None
    return SignalCandidate(
        signal_id=new_id("SIG"),
        symbol=symbol,
        timeframe=row.get("interval", "5m").strip(),
        signal_time=row.get("time", row.get("signal_time", "")).strip(),
        price=price,
        signal_level=row.get("signal_level", "B").strip(),
        drop_pct=_safe_float(row.get("drop_pct")),
        macd_dif=_safe_float(row.get("dif")),
        macd_dea=_safe_float(row.get("dea")),
        macd_hist=_safe_float(row.get("hist")),
        ma7=_safe_float(row.get("ma7")),
        ma25=_safe_float(row.get("ma25")),
        ma99=_safe_float(row.get("ma99")),
        volume=_safe_float(row.get("volume")),
        volume_ma5=_safe_float(row.get("volume_ma5")),
        volume_ratio=_safe_float(row.get("volume_ratio")),
        above_ma99=_safe_bool(row.get("above_ma99")),
        reason=row.get("reason", "").strip(),
        source=source,
    )


def _deduplicate(candidates: list[SignalCandidate]) -> list[SignalCandidate]:
    seen: set[tuple[str, str, str]] = set()
    result: list[SignalCandidate] = []
    for c in candidates:
        key = (c.symbol, c.timeframe, c.signal_time)
        if key not in seen:
            seen.add(key)
            result.append(c)
    return result


def adapt_signals(scanner_path: str) -> SignalAdapterResult:
    root = pathlib.Path(scanner_path)
    signals_csv = _read_csv(root / "data" / "signals.csv")
    alerts_jsonl = _read_jsonl(root / "logs" / "alerts.jsonl")
    raw_count = len(signals_csv) + len(alerts_jsonl)

    candidates: list[SignalCandidate] = []
    for row in signals_csv:
        c = _row_to_candidate(row, "macd_rebound_scanner")
        if c:
            candidates.append(c)
    for row in alerts_jsonl:
        c = _row_to_candidate(row, "macd_rebound_scanner_alert")
        if c:
            candidates.append(c)

    deduped = _deduplicate(candidates)
    valid = [c for c in deduped if c.price > 0 and c.symbol]

    return SignalAdapterResult(
        adapter_id=new_id("SA"),
        created_at=utc_now_iso(),
        scanner_path=str(root),
        candidates=tuple(valid),
        total_raw=raw_count,
        total_deduplicated=len(deduped),
        total_valid=len(valid),
        final_verdict=f"MACD_REBOUND_SIGNAL_ADAPTER_READY|RAW={raw_count}|VALID={len(valid)}|REAL_ORDER_SUBMIT_NOT_ALLOWED",
    )


def write_result(result: SignalAdapterResult, out: pathlib.Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result.to_dict(), indent=2), encoding="utf-8")


def render_report(result: SignalAdapterResult) -> str:
    lines = ["# Signal Adapter Result", "",
        f"**adapter_id={result.adapter_id}**",
        f"**scanner_path={result.scanner_path}**", "",
        f"- total_raw: {result.total_raw}",
        f"- total_deduplicated: {result.total_deduplicated}",
        f"- total_valid: {result.total_valid}", "",
        "## Candidates", "",
        "| Symbol | Timeframe | Price | Level | Drop% | Vol Ratio |",
        "|--------|-----------|-------|-------|-------|-----------|"]
    for c in result.candidates[:20]:
        lines.append(f"| {c.symbol} | {c.timeframe} | {c.price} | {c.signal_level} | {c.drop_pct:.2f} | {c.volume_ratio:.2f} |")
    lines.extend(["", "## Conclusion", "", result.final_verdict, ""])
    return "\n".join(lines)
