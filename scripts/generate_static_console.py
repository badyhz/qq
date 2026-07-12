"""Generate static read-only shadow console for public access.

Reads reports/strategies, generates HTML + JSON for Nginx.
No orders, no accounts, no secrets, no external network, no control buttons.

Uses versioned release directory with atomic symlink switch.
Public files only accessible via <output-dir>/current/.
"""
from __future__ import annotations

import argparse
import glob
import hashlib
import json
import math
import os
import re
import sys
import tempfile
import uuid
from datetime import datetime, timezone
from html import escape as _html_escape
from typing import Any

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core.paper_trading.paper_position import load_canonical_closed_clean_positions

REPO_ROOT = os.path.join(os.path.dirname(__file__), "..")
REPORT_DIR = os.path.join(REPO_ROOT, "reports", "strategies")
DEFAULT_OUTPUT_DIR = "/www/wwwroot/quant-shadow-console"

# Maximum release versions to keep (including current)
MAX_RELEASES = 5


# ---------------------------------------------------------------------------
# HTML escaping helper
# ---------------------------------------------------------------------------

def _html(value: object) -> str:
    """Escape any value for safe HTML embedding."""
    return _html_escape(str(value if value is not None else ""), quote=True)


# ---------------------------------------------------------------------------
# Input validation
# ---------------------------------------------------------------------------

def _find_latest(report_dir: str, suffix: str) -> str | None:
    """Find most recent file matching suffix."""
    pattern = os.path.join(report_dir, f"*{suffix}")
    files = sorted(glob.glob(pattern))
    return files[-1] if files else None


def _load_json(path: str) -> dict | None:
    """Load JSON file, return None on any error."""
    try:
        with open(path) as f:
            return json.load(f)
    except Exception:
        return None


def _extract_completion_time(data: dict) -> str | None:
    """Extract a real ISO completion time from pipeline result.

    Looks at the last step's finished_at field.
    Returns None if no valid time found.
    """
    steps = data.get("steps", [])
    if steps and isinstance(steps[-1], dict):
        finished = steps[-1].get("finished_at", "")
        if finished and "T" in str(finished):
            return str(finished)
    # Fallback: top-level finished_at (registry records have this)
    finished = data.get("finished_at", "")
    if finished and "T" in str(finished):
        return str(finished)
    return None


def _parse_iso_time(time_str: str) -> datetime | None:
    """Parse ISO time string, return None if invalid."""
    try:
        return datetime.fromisoformat(time_str.replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return None


def validate_inputs(report_dir: str) -> tuple[dict, list[str]]:
    """Validate all required inputs exist and are consistent.

    Returns (data_bundle, errors).
    If errors is non-empty, generation must not proceed.
    """
    errors: list[str] = []
    bundle: dict[str, Any] = {}

    # 1. Find lifecycle result (determines run_date)
    lc_path = _find_latest(report_dir, "_shadow_lifecycle_result.json")
    if not lc_path:
        errors.append("Missing lifecycle result")
        return bundle, errors

    lc_data = _load_json(lc_path)
    if not lc_data:
        errors.append("Corrupt lifecycle result JSON")
        return bundle, errors

    # Validate lifecycle pipeline_status
    lc_status = lc_data.get("pipeline_status", "")
    if lc_status != "PASS":
        errors.append(f"Lifecycle status is '{lc_status}', not PASS")
        return bundle, errors

    run_date = lc_data.get("date", "")
    run_id = lc_data.get("run_id", "")
    if not run_date:
        errors.append("Lifecycle result missing date")
        return bundle, errors

    bundle["lifecycle"] = lc_data
    bundle["run_date"] = run_date
    bundle["run_id"] = run_id

    # 2. Find update result for same date
    update_path = _find_latest(report_dir, "_shadow_position_update_result.json")
    if not update_path:
        errors.append("Missing update result")
        return bundle, errors

    update_data = _load_json(update_path)
    if not update_data:
        errors.append("Corrupt update result JSON")
        return bundle, errors

    # Validate update pipeline_status
    update_status = update_data.get("pipeline_status", "")
    if update_status != "PASS":
        errors.append(f"Update status is '{update_status}', not PASS")
        return bundle, errors

    if update_data.get("date") != run_date:
        errors.append(
            f"Date mismatch: lifecycle={run_date}, update={update_data.get('date')}"
        )
        return bundle, errors

    bundle["update"] = update_data

    # 3. Find scorecard for same date
    sc_path = _find_latest(report_dir, "_paper_performance_scorecard.json")
    if not sc_path:
        errors.append("Missing performance scorecard")
        return bundle, errors

    sc_data = _load_json(sc_path)
    if not sc_data:
        errors.append("Corrupt scorecard JSON")
        return bundle, errors

    if sc_data.get("date") != run_date:
        errors.append(
            f"Date mismatch: lifecycle={run_date}, scorecard={sc_data.get('date')}"
        )
        return bundle, errors

    bundle["scorecard"] = sc_data

    # 4. Find sample gate for same date
    gate_path = _find_latest(report_dir, "_shadow_sample_gate.json")
    if not gate_path:
        errors.append("Missing sample gate")
        return bundle, errors

    gate_data = _load_json(gate_path)
    if not gate_data:
        errors.append("Corrupt sample gate JSON")
        return bundle, errors

    if gate_data.get("date") != run_date:
        errors.append(
            f"Date mismatch: lifecycle={run_date}, gate={gate_data.get('date')}"
        )
        return bundle, errors

    bundle["gate"] = gate_data

    # 5. Find registry and match by run_id
    reg_path = _find_latest(report_dir, "_shadow_run_registry.jsonl")
    if not reg_path:
        errors.append("Missing registry file")
        return bundle, errors

    matching_reg = None
    try:
        with open(reg_path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                rec = json.loads(line)
                if rec.get("run_id") == run_id:
                    matching_reg = rec
                    break
    except (OSError, json.JSONDecodeError) as e:
        errors.append(f"Registry read error: {e}")
        return bundle, errors

    if not matching_reg:
        errors.append(f"Registry missing matching run_id={run_id}")
        return bundle, errors

    if matching_reg.get("accounting_status") != "OK":
        errors.append(
            f"Registry accounting_status={matching_reg.get('accounting_status')}"
        )
        return bundle, errors

    bundle["registry"] = matching_reg

    # 6. Extract real completion time
    lc_finished = _extract_completion_time(lc_data)
    reg_finished = matching_reg.get("finished_at", "")

    # Prefer registry finished_at (it's the authoritative record)
    completion_time = reg_finished if reg_finished and "T" in str(reg_finished) else lc_finished

    if not completion_time or "T" not in str(completion_time):
        errors.append("No valid completion time found (need ISO datetime, not date-only)")
        return bundle, errors

    ct_parsed = _parse_iso_time(str(completion_time))
    if not ct_parsed:
        errors.append(f"Cannot parse completion time: {completion_time}")
        return bundle, errors

    # Reject future time (more than 5 minutes ahead)
    now = datetime.now(timezone.utc)
    ct_utc = ct_parsed.astimezone(timezone.utc) if ct_parsed.tzinfo else ct_parsed.replace(tzinfo=timezone.utc)
    if ct_utc > now:
        age_min = (ct_utc - now).total_seconds() / 60
        if age_min > 5:
            errors.append(f"Completion time is {age_min:.1f} minutes in the future")
            return bundle, errors

    bundle["completion_time"] = str(completion_time)

    # 7. Load canonical positions and check accounting status
    eligible, all_canonical, diag = load_canonical_closed_clean_positions(report_dir)

    if diag.get("accounting_status") != "OK":
        errors.append(f"Accounting status: {diag.get('accounting_status')}")
        for fe in diag.get("fatal_errors", []):
            errors.append(f"  fatal: {fe}")
        return bundle, errors

    bundle["eligible"] = eligible
    bundle["all_canonical"] = all_canonical
    bundle["diag"] = diag

    # 8. Six-way count verification
    # 1. Canonical eligible count
    canonical_count = len(eligible)

    # 2. Scorecard global_metrics.closed_positions
    sc_global_closed = sc_data.get("global_metrics", {}).get("closed_positions", -1)

    # 3. Scorecard strategy sum
    sc_strat_sum = sum(
        s.get("closed_count", 0) for s in sc_data.get("strategy_scorecards", [])
    )

    # 4. Scorecard top-level cumulative_closed_clean
    sc_cumulative = sc_data.get("cumulative_closed_clean", -1)

    # 5. Gate cumulative_closed_clean
    gate_cumulative = gate_data.get("cumulative_closed_clean", -1)

    # 6. Registry matching record cumulative_closed_clean
    reg_cumulative = matching_reg.get("cumulative_closed_clean", -1)

    counts = {
        "canonical": canonical_count,
        "scorecard_global": sc_global_closed,
        "scorecard_strategy_sum": sc_strat_sum,
        "scorecard_cumulative": sc_cumulative,
        "gate_cumulative": gate_cumulative,
        "registry_cumulative": reg_cumulative,
    }

    # All non-negative counts must agree
    non_neg = {k: v for k, v in counts.items() if v is not None and v >= 0}
    if non_neg:
        values = set(non_neg.values())
        if len(values) > 1:
            errors.append(f"Count mismatch: {counts}")

    bundle["counts"] = counts
    return bundle, errors


# ---------------------------------------------------------------------------
# Read-only HTML template (no control code)
# ---------------------------------------------------------------------------

_HTML_TEMPLATE = """\
<!DOCTYPE html>
<html lang="{lang}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Shadow Console — {lang_upper}</title>
<style>
  body {{ font-family: system-ui, sans-serif; margin: 20px; background: #f8f9fa; color: #222; }}
  .card {{ background: #fff; border-radius: 8px; padding: 16px; margin: 12px 0; box-shadow: 0 1px 3px rgba(0,0,0,.1); }}
  table {{ border-collapse: collapse; width: 100%; }}
  th, td {{ border: 1px solid #ddd; padding: 6px 10px; text-align: left; font-size: 14px; }}
  th {{ background: #f0f0f0; }}
  .ok {{ color: #0a0; }} .warn {{ color: #c90; }} .err {{ color: #c00; }}
  .meta {{ font-size: 13px; color: #666; }}
  a {{ color: #0366d6; }}
</style>
</head>
<body>
<h1>{title}</h1>
<p class="meta">{generated_label}: {generated_at} | {commit_label}: {server_commit}</p>
<p class="meta">{freshness_label}: {freshness_status} ({data_age_minutes} min)</p>

<div class="card">
<h2>{status_title}</h2>
<table>
<tr><th>{sample_label}</th><td class="{sample_class}">{sample_status}</td></tr>
<tr><th>{gate_label}</th><td class="{gate_class}">{gate_status}</td></tr>
<tr><th>{eligible_label}</th><td>{eligible_count}</td></tr>
<tr><th>{open_label}</th><td>{open_count}</td></tr>
<tr><th>{tp_label}</th><td>{tp_count}</td></tr>
<tr><th>{sl_label}</th><td>{sl_count}</td></tr>
<tr><th>{timeout_label}</th><td>{timeout_count}</td></tr>
</table>
</div>

<div class="card">
<h2>{strategies_title}</h2>
<table>
<tr>
  <th>{strat_id_label}</th><th>{closed_label}</th><th>{wr_label}</th>
  <th>{pf_label}</th><th>{avg_r_label}</th><th>{cum_r_label}</th><th>{mdd_label}</th>
</tr>
{strategy_rows}
</table>
</div>

<div class="card">
<h2>{open_positions_title}</h2>
{open_positions_table}
</div>

<div class="card">
<h2>{recent_closed_title}</h2>
{recent_closed_table}
</div>

<p class="meta">
  {lang_switch_label}: {lang_switch_link}
  | {counts_label}: canonical={count_canonical}, scorecard={count_scorecard}, gate={count_gate}
  | {run_label}: {latest_run_at}
</p>

<p class="meta">{safety_label}</p>
</body>
</html>
"""


def _status_class(status: str) -> str:
    if status in ("PASS", "ELIGIBLE", "BLOCKED"):
        return "ok"
    if status in ("STALE", "UNKNOWN"):
        return "warn"
    return "err"


def render_readonly_html(
    bundle: dict[str, Any],
    lang: str = "zh",
    server_commit: str = "",
) -> str:
    """Render read-only HTML directly from data — no control code.

    All dynamic values are HTML-escaped via _html().
    """
    sc = bundle["scorecard"]
    gate = bundle["gate"]
    counts = bundle["counts"]

    generated_at = _html(datetime.now(timezone.utc).isoformat(timespec="seconds"))
    completion_time = bundle.get("completion_time", "")

    # Freshness
    data_age_minutes = "?"
    freshness_status = "unknown"
    if completion_time:
        ct_parsed = _parse_iso_time(completion_time)
        if ct_parsed:
            ct_utc = ct_parsed.astimezone(timezone.utc) if ct_parsed.tzinfo else ct_parsed.replace(tzinfo=timezone.utc)
            age = (datetime.now(timezone.utc) - ct_utc).total_seconds() / 60
            data_age_minutes = str(round(age, 1))
            freshness_status = "fresh" if age <= 90 else ("stale" if age <= 180 else "expired")

    global_metrics = sc.get("global_metrics", {})
    sample_status = gate.get("sample_status", "UNKNOWN")
    gate_status = gate.get("testnet_gate_status", "UNKNOWN")

    # Strategy rows — all values escaped
    strat_rows = []
    for s in sc.get("strategy_scorecards", []):
        strat_rows.append(
            f"<tr><td>{_html(s.get('strategy_id',''))}</td>"
            f"<td>{_html(s.get('closed_count',0))}</td>"
            f"<td>{_html(round(s.get('win_rate',0)*100,1))}%</td>"
            f"<td>{_html(round(s.get('profit_factor',0),2))}</td>"
            f"<td>{_html(round(s.get('avg_r_multiple',0),4))}</td>"
            f"<td>{_html(round(s.get('avg_r_multiple',0)*s.get('closed_count',0),2))}</td>"
            f"<td>{_html(round(s.get('max_single_loss_r',0),4))}</td></tr>"
        )

    # Open positions table
    open_positions = [
        p for p in bundle.get("all_canonical", []) if p.get("status") == "OPEN"
    ]
    if open_positions:
        op_rows = []
        for p in open_positions[:10]:
            op_rows.append(
                f"<tr><td>{_html(p.get('symbol',''))}</td>"
                f"<td>{_html(p.get('timeframe',''))}</td>"
                f"<td>{_html(p.get('side',''))}</td>"
                f"<td>{_html(p.get('entry_price',''))}</td>"
                f"<td>{_html(p.get('stop_loss',''))}</td>"
                f"<td>{_html(p.get('take_profit',''))}</td>"
                f"<td>{_html(p.get('strategy_id',''))}</td></tr>"
            )
        open_table = (
            "<table><tr><th>Symbol</th><th>TF</th><th>Side</th>"
            "<th>Entry</th><th>SL</th><th>TP</th><th>Strategy</th></tr>"
            + "".join(op_rows) + "</table>"
        )
    else:
        open_table = "<p>None</p>"

    # Recent closed table
    closed = sorted(
        [p for p in bundle.get("all_canonical", []) if p.get("status") != "OPEN"],
        key=lambda p: p.get("closed_at", ""),
        reverse=True,
    )[:20]
    if closed:
        cl_rows = []
        for p in closed:
            cl_rows.append(
                f"<tr><td>{_html(p.get('symbol',''))}</td>"
                f"<td>{_html(p.get('strategy_id',''))}</td>"
                f"<td>{_html(p.get('status',''))}</td>"
                f"<td>{_html(p.get('exit_reason',''))}</td>"
                f"<td>{_html(round(p.get('r_multiple',0),4))}</td>"
                f"<td>{_html(p.get('closed_at',''))}</td></tr>"
            )
        cl_table = (
            "<table><tr><th>Symbol</th><th>Strategy</th><th>Status</th>"
            "<th>Exit Reason</th><th>R</th><th>Closed</th></tr>"
            + "".join(cl_rows) + "</table>"
        )
    else:
        cl_table = "<p>None</p>"

    # i18n
    if lang == "zh":
        labels = {
            "title": "Shadow Console (只读)",
            "generated_label": "生成时间",
            "commit_label": "服务端 Commit",
            "freshness_label": "数据新鲜度",
            "status_title": "状态概览",
            "sample_label": "样本状态",
            "gate_label": "Testnet Gate",
            "eligible_label": "合格已平仓",
            "open_label": "持仓中",
            "tp_label": "止盈",
            "sl_label": "止损",
            "timeout_label": "超时",
            "strategies_title": "策略统计",
            "strat_id_label": "策略",
            "closed_label": "已平仓",
            "wr_label": "胜率",
            "pf_label": "盈亏比",
            "avg_r_label": "平均R",
            "cum_r_label": "累计R",
            "mdd_label": "最大亏损R",
            "open_positions_title": "当前持仓",
            "recent_closed_title": "最近平仓",
            "lang_switch_label": "语言",
            "lang_switch_link": '<a href="index_en.html">English</a>',
            "counts_label": "计数核对",
            "run_label": "运行时间",
            "safety_label": "Paper-only | No order | No testnet | No live | No secret",
        }
    else:
        labels = {
            "title": "Shadow Console (Read-Only)",
            "generated_label": "Generated",
            "commit_label": "Server Commit",
            "freshness_label": "Data freshness",
            "status_title": "Status Overview",
            "sample_label": "Sample Status",
            "gate_label": "Testnet Gate",
            "eligible_label": "Eligible Closed",
            "open_label": "Open Positions",
            "tp_label": "Take Profit",
            "sl_label": "Stop Loss",
            "timeout_label": "Timeout",
            "strategies_title": "Strategy Scorecards",
            "strat_id_label": "Strategy",
            "closed_label": "Closed",
            "wr_label": "Win Rate",
            "pf_label": "Profit Factor",
            "avg_r_label": "Avg R",
            "cum_r_label": "Cumulative R",
            "mdd_label": "Max Loss R",
            "open_positions_title": "Open Positions",
            "recent_closed_title": "Recent Closed",
            "lang_switch_label": "Language",
            "lang_switch_link": '<a href="index.html">中文</a>',
            "counts_label": "Count check",
            "run_label": "Run time",
            "safety_label": "Paper-only | No order | No testnet | No live | No secret",
        }

    lang_upper = lang.upper()

    return _HTML_TEMPLATE.format(
        lang=lang,
        lang_upper=lang_upper,
        title=labels["title"],
        generated_label=labels["generated_label"],
        generated_at=generated_at,
        commit_label=labels["commit_label"],
        server_commit=_html(server_commit or "unknown"),
        freshness_label=labels["freshness_label"],
        freshness_status=freshness_status,
        data_age_minutes=data_age_minutes,
        status_title=labels["status_title"],
        sample_label=labels["sample_label"],
        sample_status=_html(sample_status),
        sample_class=_status_class(sample_status),
        gate_label=labels["gate_label"],
        gate_status=_html(gate_status),
        gate_class=_status_class(gate_status),
        eligible_label=labels["eligible_label"],
        eligible_count=_html(counts.get("canonical", 0)),
        open_label=labels["open_label"],
        open_count=_html(global_metrics.get("open_positions", 0)),
        tp_label=labels["tp_label"],
        tp_count=_html(global_metrics.get("take_profit_hit", 0)),
        sl_label=labels["sl_label"],
        sl_count=_html(global_metrics.get("stop_loss_hit", 0)),
        timeout_label=labels["timeout_label"],
        timeout_count=_html(global_metrics.get("timeout_exit", 0)),
        strategies_title=labels["strategies_title"],
        strat_id_label=labels["strat_id_label"],
        closed_label=labels["closed_label"],
        wr_label=labels["wr_label"],
        pf_label=labels["pf_label"],
        avg_r_label=labels["avg_r_label"],
        cum_r_label=labels["cum_r_label"],
        mdd_label=labels["mdd_label"],
        strategy_rows="\n".join(strat_rows),
        open_positions_title=labels["open_positions_title"],
        open_positions_table=open_table,
        recent_closed_title=labels["recent_closed_title"],
        recent_closed_table=cl_table,
        lang_switch_label=labels["lang_switch_label"],
        lang_switch_link=labels["lang_switch_link"],
        counts_label=labels["counts_label"],
        count_canonical=counts.get("canonical", 0),
        count_scorecard=counts.get("scorecard_global", 0),
        count_gate=counts.get("gate_cumulative", 0),
        run_label=labels["run_label"],
        latest_run_at=_html(completion_time),
        safety_label=labels["safety_label"],
    )


# ---------------------------------------------------------------------------
# Public JSON (strict allowlist with length limits)
# ---------------------------------------------------------------------------

_FIELD_LENGTH_LIMITS = {
    "symbol": 32,
    "strategy_id": 64,
    "exit_reason": 128,
    "status": 32,
    "side": 16,
    "timeframe": 16,
}


def _truncate_field(value: str, field_name: str) -> str:
    """Truncate a string field to its allowed length."""
    limit = _FIELD_LENGTH_LIMITS.get(field_name)
    if limit and isinstance(value, str) and len(value) > limit:
        return value[:limit]
    return value


def build_public_json(
    bundle: dict[str, Any],
    server_commit: str = "",
) -> dict[str, Any]:
    """Build public-safe JSON using strict allowlist.

    No position_id, intent_id, registry_path, source info, or diagnostics.
    String fields are length-limited.
    """
    sc = bundle["scorecard"]
    gate = bundle["gate"]
    counts = bundle["counts"]
    completion_time = bundle.get("completion_time", "")

    # Strategy metrics (allowlisted fields only)
    strategies = {}
    for s in sc.get("strategy_scorecards", []):
        sid = _truncate_field(str(s.get("strategy_id", "")), "strategy_id")
        strategies[sid] = {
            "strategy_id": sid,
            "closed_count": s.get("closed_count"),
            "win_rate": round(s.get("win_rate", 0) * 100, 1),
            "profit_factor": round(s.get("profit_factor", 0), 2),
            "avg_r": round(s.get("avg_r_multiple", 0), 4),
            "cumulative_r": round(s.get("avg_r_multiple", 0) * s.get("closed_count", 0), 2),
            "max_drawdown_r": round(s.get("max_single_loss_r", 0), 4),
        }

    # Current open positions (allowlisted fields only, no position_id)
    current_positions = []
    for p in bundle.get("all_canonical", []):
        if p.get("status") != "OPEN":
            continue
        current_positions.append({
            "symbol": _truncate_field(str(p.get("symbol", "")), "symbol"),
            "timeframe": _truncate_field(str(p.get("timeframe", "")), "timeframe"),
            "side": _truncate_field(str(p.get("side", "")), "side"),
            "entry_price": p.get("entry_price"),
            "stop_loss": p.get("stop_loss"),
            "take_profit": p.get("take_profit"),
            "strategy_id": _truncate_field(str(p.get("strategy_id", "")), "strategy_id"),
        })

    # Recent closed (allowlisted fields only, last 20, no position_id)
    closed = sorted(
        [p for p in bundle.get("all_canonical", []) if p.get("status") != "OPEN"],
        key=lambda p: p.get("closed_at", ""),
        reverse=True,
    )[:20]
    recent_closed = []
    for p in closed:
        recent_closed.append({
            "symbol": _truncate_field(str(p.get("symbol", "")), "symbol"),
            "strategy_id": _truncate_field(str(p.get("strategy_id", "")), "strategy_id"),
            "status": _truncate_field(str(p.get("status", "")), "status"),
            "exit_reason": _truncate_field(str(p.get("exit_reason", "")), "exit_reason"),
            "r_multiple": round(p.get("r_multiple", 0), 4),
            "closed_at": p.get("closed_at"),
        })

    # Freshness (based on real completion time)
    data_age_minutes = None
    freshness_status = "unknown"
    if completion_time:
        ct_parsed = _parse_iso_time(completion_time)
        if ct_parsed:
            ct_utc = ct_parsed.astimezone(timezone.utc) if ct_parsed.tzinfo else ct_parsed.replace(tzinfo=timezone.utc)
            age = (datetime.now(timezone.utc) - ct_utc).total_seconds() / 60
            data_age_minutes = round(age, 1)
            freshness_status = "fresh" if age <= 90 else ("stale" if age <= 180 else "expired")

    global_metrics = sc.get("global_metrics", {})

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "server_commit": server_commit or "unknown",
        "run_date": bundle.get("run_date", ""),
        "latest_run_at": completion_time,
        "freshness_status": freshness_status,
        "data_age_minutes": data_age_minutes,
        "sample_status": gate.get("sample_status", "UNKNOWN"),
        "gate_status": gate.get("testnet_gate_status", "UNKNOWN"),
        "eligible_closed_clean": counts.get("canonical", 0),
        "open_positions": global_metrics.get("open_positions", 0),
        "take_profit_count": global_metrics.get("take_profit_hit", 0),
        "stop_loss_count": global_metrics.get("stop_loss_hit", 0),
        "timeout_count": global_metrics.get("timeout_exit", 0),
        "count_check": counts,
        "fee_adjusted": False,
        "slippage_adjusted": False,
        "testnet_enabled": False,
        "live_enabled": False,
        "strategies": strategies,
        "recent_closed": recent_closed,
        "current_positions": current_positions,
    }


# ---------------------------------------------------------------------------
# Sensitive leak check
# ---------------------------------------------------------------------------

SENSITIVE_PATTERNS = [
    r"/opt/quant-shadow",
    r"/www/wwwroot",
    r"10\.66\.66\.\d+",
    r"43\.156\.54\.\d+",
    r"\bSSH\b",
    r"API_KEY",
    r"SECRET_KEY",
    r"SECRET_TOKEN",
    r"\bTOKEN\b",
    r"PASSWORD",
    r"Webhook",
    r"wireguard",
    r"\.env",
]


def check_sensitive_leaks(text: str) -> list[str]:
    """Check for sensitive data leaks."""
    found = []
    for pattern in SENSITIVE_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            found.append(pattern)
    return found


# ---------------------------------------------------------------------------
# Atomic versioned release with retention
# ---------------------------------------------------------------------------

def _fsync_file(path: str) -> None:
    """fsync a single file."""
    fd = os.open(path, os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def _fsync_dir(path: str) -> None:
    """fsync a directory."""
    fd = os.open(path, os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def _cleanup_old_releases(releases_dir: str, current_target: str, keep: int = MAX_RELEASES) -> None:
    """Remove old releases, keeping at most `keep` versions.

    Never deletes the current target or anything newer.
    Cleanup failures are logged as warnings, not errors.
    """
    try:
        entries = sorted(os.listdir(releases_dir))
    except OSError:
        return

    # current_target is like "releases/20260712-223000-abc12345"
    current_version = current_target.split("/")[-1] if current_target else ""

    # Keep everything from current_version onward, plus (keep-1) before
    to_keep = set()
    versions = sorted(entries, reverse=True)
    for i, v in enumerate(versions):
        if i < keep:
            to_keep.add(v)

    for entry in entries:
        if entry in to_keep:
            continue
        if entry == current_version:
            continue
        entry_path = os.path.join(releases_dir, entry)
        if os.path.isdir(entry_path):
            try:
                import shutil
                shutil.rmtree(entry_path)
            except OSError:
                pass  # cleanup failure is non-fatal


def generate_console(
    report_dir: str,
    output_dir: str,
    server_commit: str = "",
) -> dict[str, Any]:
    """Generate static console with versioned atomic release.

    Public files are ONLY accessible via <output-dir>/current/.
    Root-level legacy files are NOT created.

    Returns result dict with success, version_id, release_dir, current_target,
    public_root, required_nginx_alias, errors.
    """
    result: dict[str, Any] = {
        "success": False,
        "version_id": None,
        "release_dir": None,
        "current_target": None,
        "public_root": None,
        "required_nginx_alias": None,
        "errors": [],
    }

    # 1. Validate inputs
    bundle, errors = validate_inputs(report_dir)
    if errors:
        result["errors"] = errors
        return result

    # 2. Render HTML (read-only template, all dynamic values escaped)
    html_zh = render_readonly_html(bundle, lang="zh", server_commit=server_commit)
    html_en = render_readonly_html(bundle, lang="en", server_commit=server_commit)

    # 3. Build JSON (strict allowlist, field length limits)
    public_json = build_public_json(bundle, server_commit=server_commit)
    json_str = json.dumps(public_json, ensure_ascii=False, indent=2)

    # 4. Validate JSON roundtrip
    try:
        json.loads(json_str)
    except json.JSONDecodeError as e:
        result["errors"].append(f"JSON validation failed: {e}")
        return result

    # 5. Sensitive leak check
    for label, content in [("zh", html_zh), ("en", html_en), ("json", json_str)]:
        leaks = check_sensitive_leaks(content)
        if leaks:
            result["errors"].append(f"Sensitive data in {label}: {leaks}")
            return result

    # 6. Verify no control code in HTML
    control_patterns = [
        r"<button", r"<form", r"<input\b", r"onclick", r"runAction",
        r"loadReport", r"run-lifecycle", r"run-update-only",
        r"run-sample-gate", r"print-status", r"fetch\(",
        r"XMLHttpRequest", r"WebSocket", r"\bPOST\b",
    ]
    for label, html in [("zh", html_zh), ("en", html_en)]:
        for pat in control_patterns:
            if re.search(pat, html, re.IGNORECASE):
                result["errors"].append(f"Control code in {label}: {pat}")
                return result

    # 7. Versioned release directory
    version_id = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S") + "-" + uuid.uuid4().hex[:8]
    releases_dir = os.path.join(output_dir, "releases")
    version_dir = os.path.join(releases_dir, version_id)
    current_link = os.path.join(output_dir, "current")
    current_tmp = os.path.join(output_dir, "current.next")
    tmp_version_dir = version_dir + ".tmp"

    files = {
        "index.html": html_zh,
        "index_en.html": html_en,
        "console_data.json": json_str,
    }

    try:
        # Create releases directory
        os.makedirs(releases_dir, exist_ok=True)

        # Create version directory (temp name first)
        os.makedirs(tmp_version_dir, exist_ok=True)

        # Write all files with fsync
        for filename, content in files.items():
            filepath = os.path.join(tmp_version_dir, filename)
            fd, tmp_path = tempfile.mkstemp(dir=tmp_version_dir, suffix=".tmp")
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as f:
                    f.write(content)
                    f.flush()
                    os.fsync(f.fileno())
                os.replace(tmp_path, filepath)
            except Exception as e:
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass
                raise e

            _fsync_file(filepath)

        # fsync version directory
        _fsync_dir(tmp_version_dir)

        # Rename temp version dir to final
        os.replace(tmp_version_dir, version_dir)
        _fsync_dir(releases_dir)

        # Create temp symlink and atomic replace
        if os.path.islink(current_tmp):
            os.unlink(current_tmp)
        os.symlink(os.path.join("releases", version_id), current_tmp)

        # Atomic replace current symlink
        os.replace(current_tmp, current_link)
        _fsync_dir(output_dir)

        result["success"] = True
        result["version_id"] = version_id
        result["release_dir"] = version_dir
        result["current_target"] = os.path.join("releases", version_id)
        result["public_root"] = os.path.join(output_dir, "current")
        result["required_nginx_alias"] = os.path.join(output_dir, "current") + "/"

        # 8. Cleanup old releases (after successful switch)
        _cleanup_old_releases(releases_dir, result["current_target"])

    except Exception as e:
        # Clean up temp artifacts
        for cleanup in [current_tmp, tmp_version_dir]:
            try:
                if os.path.islink(cleanup):
                    os.unlink(cleanup)
                elif os.path.isdir(cleanup):
                    import shutil
                    shutil.rmtree(cleanup)
            except OSError:
                pass
        result["errors"].append(f"Release failed: {e}")

    return result


def main():
    parser = argparse.ArgumentParser(description="Generate static shadow console")
    parser.add_argument("--report-dir", default=REPORT_DIR)
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--server-commit", default="",
                        help="Git commit hash of the server (hex)")
    args = parser.parse_args()

    # Validate server commit format if provided
    if args.server_commit:
        if not re.match(r"^[0-9a-f]{7,40}$", args.server_commit):
            print(f"ERROR: Invalid server commit hash: {args.server_commit}")
            return 1

    result = generate_console(args.report_dir, args.output_dir, args.server_commit)

    if result["success"]:
        print(f"Console generated: version={result['version_id']}")
        print(f"  release_dir: {result['release_dir']}")
        print(f"  current_target: {result['current_target']}")
        print(f"  public_root: {result['public_root']}")
        print(f"  required_nginx_alias: {result['required_nginx_alias']}")
        return 0
    else:
        print("Console generation FAILED:")
        for err in result["errors"]:
            print(f"  - {err}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
