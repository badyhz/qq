"""Feishu paper review payload — dry-run only, no real send."""
from __future__ import annotations
from src.paper_trading_pipeline.models import DailyPaperReview, FeishuPaperReviewPayload, new_id, utc_now_iso


def generate_feishu_payload(review: DailyPaperReview) -> FeishuPaperReviewPayload:
    return FeishuPaperReviewPayload(
        payload_id=new_id("FPR"),
        created_at=utc_now_iso(),
        title=f"[DRY-RUN] Paper Trading Review {review.date}",
        date=review.date,
        raw_signals=review.raw_signals,
        deduped_signals=review.deduped_signals,
        trade_plans_created=review.trade_plans_created,
        paper_open_count=review.paper_open_count,
        paper_closed_count=review.paper_closed_count,
        tp_hit_count=review.tp1_count,
        stop_count=review.stop_count,
        top_symbols=review.top_symbols,
        risk_notes=review.risk_notes,
        next_actions=review.next_actions,
        dry_run_only=True,
        final_verdict="FEISHU_PAPER_REVIEW_PAYLOAD_DRY_RUN_READY|DRY_RUN_ONLY=TRUE|REAL_ORDER_SUBMIT_NOT_ALLOWED",
    )
