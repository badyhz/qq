"""Operator review runner — generates review queue + decision pack. No network."""
from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core.paper_trading.runtime_config import default_config
from core.paper_trading.runtime_orchestrator import run_paper_runtime
from core.paper_trading.review_queue import (
    create_candidate, append_candidate, read_queue, queue_summary, OperatorStatus,
)
from core.paper_trading.candidate_ranker import rank_candidates
from core.paper_trading.operator_decision_pack import (
    generate_decision_pack, generate_decision_markdown, generate_decision_html,
)
from core.paper_trading.run_history import read_history, compare_last_two

FIXTURE_DIR = os.path.join(os.path.dirname(__file__), "..", "tests", "fixtures", "paper_trading")
REPORT_DIR = os.path.join(os.path.dirname(__file__), "..", "reports")


def find_fixtures() -> list:
    SKIP = {"runtime_config_sample.json", "empty_sample.json", "malformed_sample.json"}
    return sorted([
        os.path.join(FIXTURE_DIR, f)
        for f in os.listdir(FIXTURE_DIR)
        if f.endswith(".json") and f not in SKIP
    ])


def main():
    print("=== Paper Operator Review ===\n")
    os.makedirs(REPORT_DIR, exist_ok=True)

    # Run runtime to get fresh results
    fixtures = find_fixtures()
    config = default_config(fixture_paths=fixtures)
    print(f"Strategy: {config.strategy_name}")
    print(f"Fixtures: {len(config.fixture_paths)}\n")

    result = run_paper_runtime(config, write_history=True)
    print(f"Runtime: {result.status} | Trades: {result.total_trades} | Score: {result.score:.1f} | Rating: {result.rating}\n")

    # Create review candidates from runtime result
    queue_path = os.path.join(REPORT_DIR, "paper_trading_review_queue.jsonl")
    run_id = result.strategy_name + "_" + result.status

    # Generate candidates based on runtime stats
    candidates_created = 0
    if result.total_trades > 0:
        c = create_candidate(
            symbol="BTCUSDT",
            strategy_name=result.strategy_name,
            side="BUY",
            entry_price=0.0,  # Paper-only, no real entry
            stop_loss=0.0,
            take_profit=0.0,
            score=result.score,
            rating=result.rating,
            risk_summary=f"trades={result.total_trades}, win_rate={result.win_rate:.1%}, pnl={result.total_pnl}",
            source_run_id=run_id,
        )
        append_candidate(c, queue_path)
        candidates_created += 1

    # Rank candidates
    queue_entries = read_queue(queue_path)
    ranked = rank_candidates(queue_entries)

    # Generate decision pack
    pack = generate_decision_pack(ranked)
    md = generate_decision_markdown(ranked)
    html = generate_decision_html(ranked)

    # History comparison
    history = read_history()
    trend = compare_last_two(history)

    # Summary
    summary = queue_summary(queue_path)
    print("=== Review Queue ===")
    print(f"Candidates created: {candidates_created}")
    print(f"Queue total: {summary['total']}")
    for status, count in summary.items():
        if status != "total" and count > 0:
            print(f"  {status}: {count}")

    print(f"\n=== Ranked ===")
    print(f"HIGH: {pack['high_count']} | MEDIUM: {pack['medium_count']} | LOW: {pack['low_count']} | REJECT: {pack['reject_count']}")

    if trend:
        print(f"\n=== Trend ===")
        print(f"Score delta: {trend.score:+.1f} | PnL delta: {trend.pnl:+.2f} | Improved: {trend.improved}")

    # JSON output
    json_path = os.path.join(REPORT_DIR, "paper_trading_operator_review.json")
    json_data = {
        "runtime_status": result.status,
        "strategy_name": result.strategy_name,
        "score": result.score,
        "rating": result.rating,
        "total_trades": result.total_trades,
        "win_rate": result.win_rate,
        "total_pnl": result.total_pnl,
        "candidates_created": candidates_created,
        "queue_summary": summary,
        "ranked_summary": {
            "high": pack["high_count"],
            "medium": pack["medium_count"],
            "low": pack["low_count"],
            "reject": pack["reject_count"],
        },
        "trend": {
            "score_delta": trend.score if trend else None,
            "pnl_delta": trend.pnl if trend else None,
            "improved": trend.improved if trend else None,
        },
        "safety_flags": ["NO_REAL_ORDER", "PAPER_ONLY", "HUMAN_REVIEW_REQUIRED", "NO_TESTNET", "NO_LIVE", "NO_SECRET_READ", "NO_REAL_HTTP"],
    }
    with open(json_path, "w") as f:
        json.dump(json_data, f, indent=2)
    print(f"\nJSON: {json_path}")

    # Markdown output
    md_path = os.path.join(REPORT_DIR, "paper_trading_operator_review.md")
    with open(md_path, "w") as f:
        f.write(md)
        f.write("\n\n## Safety\n\n")
        f.write("- PAPER_ONLY\n- NO_REAL_ORDER\n- NO_TESTNET\n- NO_LIVE\n- NO_SECRET_READ\n- NO_REAL_HTTP\n- HUMAN_REVIEW_REQUIRED\n")
    print(f"Markdown: {md_path}")

    # HTML output
    html_path = os.path.join(REPORT_DIR, "paper_trading_operator_review.html")
    with open(html_path, "w") as f:
        f.write(html)
    print(f"HTML: {html_path}")

    print(f"\nStatus: PAPER_OPERATOR_REVIEW_COMPLETE")
    return 0


if __name__ == "__main__":
    sys.exit(main())
