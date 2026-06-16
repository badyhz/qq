"""Operator decision pack — human-readable review package. No network, no orders."""
from __future__ import annotations

from typing import List, Dict, Any, Optional

from core.paper_trading.candidate_ranker import Priority, RankedCandidate


def generate_decision_pack(ranked: List[RankedCandidate]) -> Dict[str, Any]:
    """Generate a decision pack dict from ranked candidates."""
    groups = {p.value: [] for p in Priority}
    for r in ranked:
        groups[r.priority.value].append(_candidate_dict(r))

    return {
        "total_candidates": len(ranked),
        "high_count": len(groups["HIGH"]),
        "medium_count": len(groups["MEDIUM"]),
        "low_count": len(groups["LOW"]),
        "reject_count": len(groups["REJECT"]),
        "groups": groups,
        "safety_flags": ["NO_REAL_ORDER", "PAPER_ONLY", "HUMAN_REVIEW_REQUIRED", "NO_TESTNET", "NO_LIVE"],
        "allowed_actions": ["WATCHLIST", "REJECTED", "PAPER_APPROVED"],
        "note": "PAPER_APPROVED means paper review passed. It does NOT create real orders.",
    }


def generate_decision_markdown(ranked: List[RankedCandidate]) -> str:
    """Generate a markdown report from ranked candidates."""
    pack = generate_decision_pack(ranked)
    lines = [
        "# Operator Decision Pack\n",
        f"**Total candidates:** {pack['total_candidates']}",
        f"**HIGH:** {pack['high_count']} | **MEDIUM:** {pack['medium_count']} | "
        f"**LOW:** {pack['low_count']} | **REJECT:** {pack['reject_count']}\n",
    ]

    for priority in ["HIGH", "MEDIUM", "LOW", "REJECT"]:
        candidates = pack["groups"][priority]
        if not candidates:
            continue
        lines.append(f"## {priority} Priority ({len(candidates)})\n")
        for c in candidates:
            lines.append(f"### {c['symbol']} {c['side']} — {c['strategy_name']}")
            lines.append(f"- **Rating:** {c['rating']} (score {c['score']:.0f})")
            lines.append(f"- **Entry:** {c['entry_price']:.2f} | **SL:** {c['stop_loss']:.2f} | **TP:** {c['take_profit']:.2f}")
            lines.append(f"- **Risk:** {c['risk_summary']}")
            lines.append(f"- **Rank:** #{c['rank']} (rank_score {c['rank_score']:.1f})")
            lines.append(f"- **Reasons:** {', '.join(c['reason_codes'])}")
            lines.append(f"- **Summary:** {c['human_summary']}")
            lines.append("")

    lines.append("## Allowed Actions\n")
    lines.append("- **WATCHLIST** — Add to observation list")
    lines.append("- **REJECTED** — Does not meet criteria")
    lines.append("- **PAPER_APPROVED** — Paper review passed (NOT real orders)\n")

    lines.append("## Safety\n")
    for flag in pack["safety_flags"]:
        lines.append(f"- {flag}")
    lines.append(f"\n{pack['note']}")
    return "\n".join(lines)


def generate_decision_html(ranked: List[RankedCandidate]) -> str:
    """Generate a self-contained HTML report. No external links, no scripts."""
    pack = generate_decision_pack(ranked)
    rows = ""
    for priority in ["HIGH", "MEDIUM", "LOW", "REJECT"]:
        for c in pack["groups"][priority]:
            rows += (
                f'<tr class="priority-{priority.lower()}">'
                f'<td>{c["rank"]}</td><td>{priority}</td><td>{c["symbol"]}</td>'
                f'<td>{c["side"]}</td><td>{c["rating"]}</td><td>{c["score"]:.0f}</td>'
                f'<td>{c["entry_price"]:.2f}</td><td>{c["stop_loss"]:.2f}</td>'
                f'<td>{c["take_profit"]:.2f}</td><td>{c["risk_summary"]}</td></tr>\n'
            )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Operator Decision Pack</title>
<style>
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; margin: 0; padding: 20px; background: #f5f5f5; color: #333; }}
  .container {{ max-width: 1000px; margin: 0 auto; }}
  h1 {{ color: #1a1a2e; border-bottom: 3px solid #16213e; padding-bottom: 10px; }}
  .card {{ background: white; border-radius: 8px; padding: 20px; margin: 15px 0; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
  .summary {{ display: flex; gap: 20px; flex-wrap: wrap; }}
  .stat {{ text-align: center; }}
  .stat .num {{ font-size: 2em; font-weight: bold; }}
  .stat .lbl {{ font-size: 0.85em; color: #666; }}
  .num-high {{ color: #155724; }}
  .num-medium {{ color: #004085; }}
  .num-low {{ color: #856404; }}
  .num-reject {{ color: #721c24; }}
  table {{ width: 100%; border-collapse: collapse; }}
  th, td {{ padding: 8px; text-align: left; border-bottom: 1px solid #ddd; font-size: 0.9em; }}
  th {{ background: #16213e; color: white; }}
  .priority-high {{ background: #d4edda; }}
  .priority-medium {{ background: #cce5ff; }}
  .priority-low {{ background: #fff3cd; }}
  .priority-reject {{ background: #f8d7da; }}
  .safety {{ background: #e8f5e9; border-left: 4px solid #4caf50; padding: 15px; margin-top: 20px; }}
  .footer {{ margin-top: 30px; padding: 15px; background: #1a1a2e; color: #aaa; border-radius: 8px; text-align: center; font-size: 0.85em; }}
</style>
</head>
<body>
<div class="container">
<h1>Operator Decision Pack</h1>
<div class="card">
  <div class="summary">
    <div class="stat"><div class="num">{pack['total_candidates']}</div><div class="lbl">Total</div></div>
    <div class="stat"><div class="num num-high">{pack['high_count']}</div><div class="lbl">HIGH</div></div>
    <div class="stat"><div class="num num-medium">{pack['medium_count']}</div><div class="lbl">MEDIUM</div></div>
    <div class="stat"><div class="num num-low">{pack['low_count']}</div><div class="lbl">LOW</div></div>
    <div class="stat"><div class="num num-reject">{pack['reject_count']}</div><div class="lbl">REJECT</div></div>
  </div>
</div>
<div class="card">
<table>
  <tr><th>#</th><th>Priority</th><th>Symbol</th><th>Side</th><th>Rating</th><th>Score</th><th>Entry</th><th>SL</th><th>TP</th><th>Risk</th></tr>
  {rows}
</table>
</div>
<div class="safety">
  <strong>Allowed Actions:</strong> WATCHLIST / REJECTED / PAPER_APPROVED<br>
  <strong>Note:</strong> PAPER_APPROVED means paper review passed. It does NOT create real orders.
  <ul>{''.join(f'<li>{f}</li>' for f in pack['safety_flags'])}</ul>
</div>
<div class="footer">
  Operator Decision Pack | Mode: paper-only | No real orders | No network calls | Generated locally
</div>
</div>
</body>
</html>"""


def _candidate_dict(r: RankedCandidate) -> Dict[str, Any]:
    return {
        "review_id": r.review_id,
        "rank": r.rank,
        "priority": r.priority.value,
        "rank_score": r.rank_score,
        "reason_codes": r.reason_codes,
        "human_summary": r.human_summary,
        "symbol": r.symbol,
        "strategy_name": r.strategy_name,
        "side": r.side,
        "entry_price": r.entry_price,
        "stop_loss": r.stop_loss,
        "take_profit": r.take_profit,
        "score": r.score,
        "rating": r.rating,
        "risk_summary": r.risk_summary,
        "operator_status": r.operator_status,
        "source_run_id": r.source_run_id,
        "safety_flags": r.safety_flags,
    }
