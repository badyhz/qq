from __future__ import annotations

import csv
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from core.signal_outcome import parse_shadow_order_plan


def to_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def to_float_nan(value: Any) -> float:
    if value is None:
        return float("nan")
    text = str(value).strip()
    if text == "":
        return float("nan")
    try:
        return float(text)
    except (TypeError, ValueError):
        return float("nan")


def to_bool(value: Any) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "y"}


def parse_dt(value: Any) -> datetime | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        dt = datetime.fromisoformat(text)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except ValueError:
        return None


def to_epoch_ms(value: Any) -> int:
    if value is None:
        return 0
    if isinstance(value, (int, float)):
        raw = int(float(value))
        if raw > 10_000_000_000:
            return raw
        if raw > 1_000_000_000:
            return raw * 1000
        return 0
    text = str(value).strip()
    if not text:
        return 0
    try:
        raw = int(float(text))
        if raw > 10_000_000_000:
            return raw
        if raw > 1_000_000_000:
            return raw * 1000
    except ValueError:
        pass
    dt = parse_dt(text)
    if dt is None:
        return 0
    return int(dt.timestamp() * 1000)


def interval_ms(timeframe: str) -> int:
    text = str(timeframe or "5m").strip().lower()
    if not text:
        return 5 * 60 * 1000
    unit = text[-1]
    number = max(1, int(to_float(text[:-1], 5)))
    if unit == "m":
        return number * 60 * 1000
    if unit == "h":
        return number * 60 * 60 * 1000
    if unit == "d":
        return number * 24 * 60 * 60 * 1000
    return 5 * 60 * 1000


def read_csv_rows(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    try:
        with path.open("r", encoding="utf-8", newline="") as handle:
            return list(csv.DictReader(handle))
    except OSError:
        return []


def read_jsonl_rows(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            text = line.strip()
            if not text:
                continue
            try:
                payload = json.loads(text)
            except json.JSONDecodeError:
                continue
            if isinstance(payload, dict):
                rows.append(payload)
    except OSError:
        return []
    return rows


def load_cached_klines(*, cache_root: str, symbol: str, timeframe: str) -> list[dict[str, Any]]:
    root = Path(cache_root) / str(symbol or "").strip().upper() / str(timeframe or "5m").strip()
    if not root.exists():
        return []
    rows: list[dict[str, Any]] = []
    step = interval_ms(timeframe)
    for path in sorted(root.glob("*.csv")):
        for raw in read_csv_rows(path):
            open_ms = to_epoch_ms(raw.get("open_time_ms", raw.get("timestamp", raw.get("open_time", 0))))
            if open_ms <= 0:
                continue
            close_ms = to_epoch_ms(raw.get("close_time_ms", raw.get("close_time", 0)))
            if close_ms <= 0:
                close_ms = open_ms + step - 1
            row = {
                "open_time_ms": open_ms,
                "close_time_ms": close_ms,
                "open": to_float(raw.get("open", 0.0), 0.0),
                "high": to_float(raw.get("high", 0.0), 0.0),
                "low": to_float(raw.get("low", 0.0), 0.0),
                "close": to_float(raw.get("close", 0.0), 0.0),
                "volume": to_float(raw.get("volume", 0.0), 0.0),
            }
            rows.append(row)
    rows.sort(key=lambda item: int(item.get("open_time_ms", 0)))
    dedup: dict[int, dict[str, Any]] = {}
    for row in rows:
        dedup[int(row["open_time_ms"])] = row
    return [dedup[key] for key in sorted(dedup.keys())]


def find_bar_index(klines: list[dict[str, Any]], ts_ms: int) -> int:
    if ts_ms <= 0:
        return -1
    for idx, row in enumerate(klines):
        if int(row.get("open_time_ms", 0)) <= ts_ms <= int(row.get("close_time_ms", 0)):
            return idx
    best_idx = -1
    best_delta = 2**63 - 1
    for idx, row in enumerate(klines):
        delta = abs(int(row.get("open_time_ms", 0)) - ts_ms)
        if delta < best_delta:
            best_delta = delta
            best_idx = idx
    return best_idx


def ema(values: list[float], period: int) -> list[float]:
    if not values:
        return []
    p = max(1, int(period))
    alpha = 2.0 / (p + 1.0)
    out: list[float] = []
    prev = float(values[0])
    for value in values:
        current = float(value) * alpha + prev * (1.0 - alpha)
        out.append(current)
        prev = current
    return out


def atr(rows: list[dict[str, Any]], period: int = 14) -> list[float]:
    if not rows:
        return []
    p = max(1, int(period))
    tr_values: list[float] = []
    for idx, row in enumerate(rows):
        high = to_float(row.get("high", 0.0), 0.0)
        low = to_float(row.get("low", 0.0), 0.0)
        if idx == 0:
            tr_values.append(max(high - low, 0.0))
            continue
        prev_close = to_float(rows[idx - 1].get("close", 0.0), 0.0)
        tr = max(high - low, abs(high - prev_close), abs(low - prev_close))
        tr_values.append(max(tr, 0.0))
    return ema(tr_values, p)


def safe_ratio(numerator: float, denominator: float) -> float:
    if (not math.isfinite(numerator)) or (not math.isfinite(denominator)) or denominator == 0:
        return float("nan")
    return numerator / denominator


def nan_to_empty(value: Any) -> Any:
    if isinstance(value, float) and (not math.isfinite(value)):
        return float("nan")
    return value


def load_shadow_plan_rows(shadow_plan_jsonl: str) -> list[dict[str, Any]]:
    plans: list[dict[str, Any]] = []
    for raw in read_jsonl_rows(Path(shadow_plan_jsonl)):
        parsed = parse_shadow_order_plan(raw)
        if not bool(parsed.get("ok", False)):
            continue
        plan = dict(parsed.get("plan", {}))
        plan["order_key"] = (
            f"{str(plan.get('symbol', '')).strip().upper()}|"
            f"{int(plan.get('entry_timestamp_ms', 0) or 0)}|"
            f"{float(plan.get('entry_price', 0.0) or 0.0):.10f}"
        )
        plans.append(plan)
    return plans


def load_shadow_outcome_rows(shadow_outcome_csv: str) -> list[dict[str, Any]]:
    return read_csv_rows(Path(shadow_outcome_csv))


def best_shadow_outcome_by_key(outcome_rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    best: dict[str, dict[str, Any]] = {}
    for row in outcome_rows:
        key = str(row.get("order_key", "")).strip()
        if not key:
            continue
        horizon = int(to_float(row.get("horizon_bars", 0), 0))
        old = best.get(key)
        old_h = int(to_float((old or {}).get("horizon_bars", 0), 0)) if old else -1
        if old is None or horizon > old_h:
            best[key] = row
    return best


def match_plan_for_trade(
    *,
    trade_row: dict[str, Any],
    plans: list[dict[str, Any]],
    max_time_diff_hours: float = 48.0,
) -> dict[str, Any]:
    symbol = str(trade_row.get("symbol", "")).strip().upper()
    if not symbol:
        return {}
    target_ts = to_epoch_ms(trade_row.get("entry_time", ""))
    target_price = to_float_nan(trade_row.get("entry_price"))
    same_symbol = [plan for plan in plans if str(plan.get("symbol", "")).strip().upper() == symbol]
    if not same_symbol:
        return {}
    best_plan: dict[str, Any] | None = None
    best_score: float | None = None
    max_diff_ms = int(max(1.0, float(max_time_diff_hours)) * 3600 * 1000)
    for plan in same_symbol:
        plan_ts = int(plan.get("entry_timestamp_ms", 0) or 0)
        plan_price = to_float_nan(plan.get("entry_price"))
        ts_diff = abs(plan_ts - target_ts) if target_ts > 0 and plan_ts > 0 else max_diff_ms + 1
        if target_ts > 0 and ts_diff > max_diff_ms:
            continue
        price_rel = abs(plan_price - target_price) / target_price if (math.isfinite(plan_price) and math.isfinite(target_price) and target_price > 0) else 1.0
        score = (ts_diff / max(1, max_diff_ms)) + price_rel
        if best_score is None or score < best_score:
            best_score = score
            best_plan = plan
    if best_plan is not None:
        return best_plan
    # fallback to same symbol nearest timestamp even if far
    same_symbol.sort(key=lambda plan: abs(int(plan.get("entry_timestamp_ms", 0) or 0) - target_ts))
    return same_symbol[0]


def evaluate_sample_confidence(*, sample_count: int, minimum_required_samples: int = 20) -> dict[str, Any]:
    count = max(0, int(sample_count))
    min_required = max(1, int(minimum_required_samples))
    level = "TOO_SMALL"
    score = 0.0
    reason = "sample_size_too_small"
    is_sufficient = False

    if count < 5:
        level = "TOO_SMALL"
        score = min(20.0, (count / 5.0) * 20.0)
        reason = "sample_size_too_small"
    elif count < 20:
        level = "LOW"
        score = 20.0 + ((count - 5) / 15.0) * 30.0
        reason = "sample_size_low"
    elif count < 50:
        level = "MEDIUM"
        score = 50.0 + ((count - 20) / 30.0) * 25.0
        reason = "sample_size_medium"
        is_sufficient = True
    else:
        level = "HIGH"
        score = 75.0 + min(25.0, ((count - 50) / 50.0) * 25.0)
        reason = "sample_size_high"
        is_sufficient = True

    score = max(0.0, min(100.0, score))
    return {
        "minimum_required_samples": min_required,
        "sample_confidence_score": round(score, 8),
        "sample_confidence_level": level,
        "is_sample_size_sufficient": bool(is_sufficient),
        "confidence_reason": reason,
    }


def compute_weighted_sample_count(
    *,
    real_sample_count: int | float,
    shadow_sample_count: int | float,
    shadow_sample_weight: float = 0.3,
) -> float:
    real_count = max(0.0, to_float(real_sample_count, 0.0))
    shadow_count = max(0.0, to_float(shadow_sample_count, 0.0))
    weight = to_float(shadow_sample_weight, 0.3)
    if (not math.isfinite(weight)) or weight < 0:
        weight = 0.3
    return real_count + (shadow_count * weight)


def compute_weighted_sample_count_with_observation(
    *,
    real_sample_count: int | float,
    strict_shadow_sample_count: int | float,
    observation_shadow_sample_count: int | float,
    strict_shadow_sample_weight: float = 0.3,
    observation_shadow_sample_weight: float = 0.1,
) -> float:
    real_count = max(0.0, to_float(real_sample_count, 0.0))
    strict_count = max(0.0, to_float(strict_shadow_sample_count, 0.0))
    observation_count = max(0.0, to_float(observation_shadow_sample_count, 0.0))
    strict_weight = to_float(strict_shadow_sample_weight, 0.3)
    observation_weight = to_float(observation_shadow_sample_weight, 0.1)
    if (not math.isfinite(strict_weight)) or strict_weight < 0:
        strict_weight = 0.3
    if (not math.isfinite(observation_weight)) or observation_weight < 0:
        observation_weight = 0.1
    return real_count + (strict_count * strict_weight) + (observation_count * observation_weight)


def evaluate_weighted_sample_confidence(
    *,
    weighted_sample_count: int | float,
    minimum_required_samples: int = 20,
) -> dict[str, Any]:
    count = max(0.0, to_float(weighted_sample_count, 0.0))
    min_required = max(1, int(minimum_required_samples))
    level = "TOO_SMALL"
    score = 0.0
    reason = "sample_size_too_small"
    is_sufficient = False

    if count < 5.0:
        level = "TOO_SMALL"
        score = min(20.0, (count / 5.0) * 20.0)
        reason = "sample_size_too_small"
    elif count < 20.0:
        level = "LOW"
        score = 20.0 + ((count - 5.0) / 15.0) * 30.0
        reason = "sample_size_low"
    elif count < 50.0:
        level = "MEDIUM"
        score = 50.0 + ((count - 20.0) / 30.0) * 25.0
        reason = "sample_size_medium"
        is_sufficient = True
    else:
        level = "HIGH"
        score = 75.0 + min(25.0, ((count - 50.0) / 50.0) * 25.0)
        reason = "sample_size_high"
        is_sufficient = True

    score = max(0.0, min(100.0, score))
    return {
        "minimum_required_samples": min_required,
        "sample_confidence_score": round(score, 8),
        "sample_confidence_level": level,
        "is_sample_size_sufficient": bool(is_sufficient),
        "confidence_reason": reason,
    }


def sample_mix_status(*, real_sample_count: int | float, shadow_sample_count: int | float) -> str:
    real_count = max(0.0, to_float(real_sample_count, 0.0))
    shadow_count = max(0.0, to_float(shadow_sample_count, 0.0))
    if real_count > 0 and shadow_count > 0:
        return "MIXED"
    if real_count > 0:
        return "REAL_ONLY"
    if shadow_count > 0:
        return "SHADOW_ONLY"
    return "NO_SAMPLES"
