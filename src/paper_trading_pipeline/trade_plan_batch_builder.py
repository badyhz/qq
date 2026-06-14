"""Trade plan batch builder — generates trade plans from deduped signals."""
from __future__ import annotations
from src.paper_trading_pipeline.models import TradePlanBatch, new_id, utc_now_iso
from src.trade_plan_engine.models import SignalCandidate
from src.trade_plan_engine.entry_plan import generate_entry_plan
from src.trade_plan_engine.exit_plan import compute_stop_loss, compute_take_profits
from src.trade_plan_engine.risk_plan import calculate_risk_plan
from src.trade_plan_engine.models import TradePlan as TPTradePlan


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


def _to_signal_candidate(d: dict) -> SignalCandidate | None:
    symbol = d.get("symbol", "").strip()
    price = _safe_float(d.get("price"))
    if not symbol or price <= 0:
        return None
    return SignalCandidate(
        signal_id=new_id("SIG"),
        symbol=symbol,
        timeframe=d.get("interval", "5m").strip(),
        signal_time=d.get("time", d.get("signal_time", "")).strip(),
        price=price,
        signal_level=d.get("signal_level", "B").strip(),
        drop_pct=_safe_float(d.get("drop_pct")),
        macd_dif=_safe_float(d.get("dif")),
        macd_dea=_safe_float(d.get("dea")),
        macd_hist=_safe_float(d.get("hist")),
        ma7=_safe_float(d.get("ma7")),
        ma25=_safe_float(d.get("ma25")),
        ma99=_safe_float(d.get("ma99")),
        volume=_safe_float(d.get("volume")),
        volume_ma5=_safe_float(d.get("volume_ma5")),
        volume_ratio=_safe_float(d.get("volume_ratio")),
        above_ma99=_safe_bool(d.get("above_ma99")),
        reason=d.get("reason", "").strip(),
        source="paper_trading_pipeline",
    )


def build_trade_plans(
    signals: list[dict],
    snapshot_id: str = "",
    account_equity: float = 10000.0,
) -> TradePlanBatch:
    plans: list[dict] = []
    rejections: list[str] = []

    for sig_dict in signals:
        sig = _to_signal_candidate(sig_dict)
        if not sig:
            rejections.append(f"Invalid signal: {sig_dict.get('symbol', '?')}")
            continue

        entry = generate_entry_plan(sig)
        sl = compute_stop_loss(entry["entry_price"], sig.ma25)
        tp1, tp2, tp3 = compute_take_profits(entry["entry_price"], sl)
        risk = calculate_risk_plan(entry["entry_price"], sl, account_equity=account_equity)

        risk_pct = round(abs(sl - entry["entry_price"]) / entry["entry_price"] * 100, 2)

        if risk.risk_level == "REJECTED":
            rejections.append(f"{sig.symbol}: risk {risk_pct}% REJECTED")
            continue

        grade = "B"
        if entry["confidence"] == "HIGH":
            grade = "A"
        elif entry["confidence"] == "LOW":
            grade = "C"
        if not sig.above_ma99 and grade == "A":
            grade = "B"

        plan = TPTradePlan(
            plan_id=new_id("TP"), signal_id=sig.signal_id,
            symbol=sig.symbol, timeframe=sig.timeframe,
            side="LONG", entry_type=entry["entry_type"],
            entry_price=entry["entry_price"],
            entry_zone_low=entry["entry_zone_low"],
            entry_zone_high=entry["entry_zone_high"],
            stop_loss=sl, take_profit_1=tp1, take_profit_2=tp2, take_profit_3=tp3,
            risk_pct=risk_pct, reward_risk_1=1.5, reward_risk_2=2.5, reward_risk_3=4.0,
            position_size_hint=risk.suggested_quantity_placeholder,
            max_account_risk_pct=0.01, plan_grade=grade,
            valid_until="4h", invalid_if="price < ma25 or MACD histogram negative",
            explain=entry["entry_reason"], dry_run_only=True,
        )
        plans.append(plan.to_dict())

    return TradePlanBatch(
        batch_id=new_id("TPB"),
        created_at=utc_now_iso(),
        source_snapshot_id=snapshot_id,
        total_signals=len(signals),
        plans_created=len(plans),
        plans_rejected=len(rejections),
        plans=tuple(plans),
        rejection_reasons=rejections,
        final_verdict=f"PAPER_TRADE_PLAN_BATCH_READY|CREATED={len(plans)}|REJECTED={len(rejections)}|REAL_ORDER_SUBMIT_NOT_ALLOWED",
    )
