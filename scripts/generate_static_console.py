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
import shutil
import stat
import sys
import tempfile
import uuid
from datetime import date, datetime, timedelta, timezone
from html import escape as _html_escape
from typing import Any

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core.paper_trading.paper_position import load_canonical_closed_clean_positions

REPO_ROOT = os.path.join(os.path.dirname(__file__), "..")
REPORT_DIR = os.path.join(REPO_ROOT, "reports", "strategies")
DEFAULT_OUTPUT_DIR = "/www/wwwroot/quant-shadow-console"

# Maximum release versions to keep (including current)
MAX_RELEASES = 5
PUBLIC_DIRECTORY_MODE = 0o755
PUBLIC_FILE_MODE = 0o644


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


def _require_nonnegative_int(
    mapping: dict, field: str, label: str, errors: list[str],
) -> int | None:
    """Require a non-negative int field. Appends to errors if missing/invalid.

    Rejects: missing key, None, bool, float, negative, string numbers.
    """
    if field not in mapping:
        errors.append(f"{label}: missing field '{field}'")
        return None
    value = mapping[field]
    if value is None:
        errors.append(f"{label}: field '{field}' is None")
        return None
    if isinstance(value, bool):
        errors.append(f"{label}: field '{field}' is bool, not int")
        return None
    if not isinstance(value, int):
        errors.append(f"{label}: field '{field}' is {type(value).__name__}, not int")
        return None
    if value < 0:
        errors.append(f"{label}: field '{field}' is negative ({value})")
        return None
    return value


def _require_str(mapping: dict, field: str, label: str, errors: list[str]) -> str | None:
    """Require a non-empty string field."""
    if field not in mapping:
        errors.append(f"{label}: missing field '{field}'")
        return None
    value = mapping[field]
    if not isinstance(value, str) or not value:
        errors.append(f"{label}: field '{field}' must be non-empty string")
        return None
    return value


def _parse_iso_date(value: object) -> date | None:
    """Parse a strict YYYY-MM-DD calendar date."""
    if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def _parse_aware_iso_datetime(value: object) -> datetime | None:
    """Parse an ISO datetime that explicitly includes a timezone."""
    if not isinstance(value, str):
        return None
    if "T" not in value:
        return None
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return None
    return dt if dt.tzinfo is not None and dt.utcoffset() is not None else None


def _public_profit_factor(value: object) -> tuple[float | None, str, str]:
    """Return standards-compliant JSON value, status, and HTML display."""
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError):
        return None, "UNDEFINED", "—"
    if math.isnan(number):
        return None, "UNDEFINED", "—"
    if math.isinf(number):
        if number > 0:
            return None, "INFINITE", "∞"
        raise ValueError("negative infinite profit_factor is invalid")
    if number < 0:
        raise ValueError("negative profit_factor is invalid")
    rounded = round(number, 2)
    return rounded, "FINITE", str(rounded)


def _validate_steps(pipeline: dict, label: str, errors: list[str]) -> bool:
    """Validate step-level status for a pipeline result.

    Returns True if all steps pass. Checks:
    - steps is non-empty list
    - each step is dict with status=="PASS", exit_code==0, started_at, finished_at
    - Contradictory top-level PASS + step FAIL is fatal
    """
    steps = pipeline.get("steps")
    if not isinstance(steps, list) or len(steps) == 0:
        errors.append(f"{label}: steps is empty or missing")
        return False

    all_pass = True
    for i, step in enumerate(steps):
        if not isinstance(step, dict):
            errors.append(f"{label}: step[{i}] is not a dict")
            all_pass = False
            continue
        step_status = step.get("status")
        if step_status != "PASS":
            errors.append(f"{label}: step[{i}] status='{step_status}', expected PASS")
            all_pass = False
        exit_code = step.get("exit_code")
        if exit_code != 0:
            errors.append(f"{label}: step[{i}] exit_code={exit_code}, expected 0")
            all_pass = False
        if not step.get("started_at"):
            errors.append(f"{label}: step[{i}] missing started_at")
            all_pass = False
        if not step.get("finished_at"):
            errors.append(f"{label}: step[{i}] missing finished_at")
            all_pass = False
        sa = _parse_aware_iso_datetime(step.get("started_at"))
        fa = _parse_aware_iso_datetime(step.get("finished_at"))
        if sa is None:
            errors.append(f"{label}: step[{i}] invalid timezone-aware started_at")
            all_pass = False
        if fa is None:
            errors.append(f"{label}: step[{i}] invalid timezone-aware finished_at")
            all_pass = False
        if sa is not None and fa is not None and sa > fa:
            errors.append(f"{label}: step[{i}] started_at > finished_at")
            all_pass = False

    return all_pass


def _latest_step_finished_at(
    pipeline: dict,
    label: str,
    errors: list[str],
) -> datetime | None:
    """Return the latest completion across all steps, independent of list order."""
    parsed: list[tuple[int, datetime]] = []
    for index, step in enumerate(pipeline.get("steps", [])):
        if not isinstance(step, dict):
            errors.append(f"{label}: step[{index}] is not a dict")
            continue
        finished = _parse_aware_iso_datetime(step.get("finished_at"))
        if finished is None:
            errors.append(
                f"{label}: step[{index}] invalid timezone-aware finished_at"
            )
            continue
        parsed.append((index, finished))
    if not parsed:
        errors.append(f"{label}: no valid step finished_at values")
        return None
    return max(parsed, key=lambda item: item[1])[1]


def validate_inputs(
    report_dir: str,
    report_date: str | None = None,
) -> tuple[dict, list[str]]:
    """Validate all required inputs exist and are consistent.

    Strict validation order:
    1. Read inputs
    2. Schema required fields
    3. Run ID four-way consistency
    4. Date five-way consistency
    5. Step-level status validation
    6. Timeline validation
    7. Accounting validation
    8. Six-way count validation
    9. Return bundle for JSON/HTML generation

    Returns (data_bundle, errors).
    If errors is non-empty, generation must not proceed.
    """
    errors: list[str] = []
    bundle: dict[str, Any] = {}

    if report_date is not None and _parse_iso_date(report_date) is None:
        errors.append(f"Authoritative report_date is invalid: {report_date!r}")
        return bundle, errors

    def source_path(suffix: str) -> str | None:
        if report_date is None:
            return _find_latest(report_dir, suffix)
        exact = os.path.join(report_dir, f"{report_date}{suffix}")
        return exact if os.path.isfile(exact) else None

    # --- 1. Read lifecycle ---
    lc_path = source_path("_shadow_lifecycle_result.json")
    if not lc_path:
        errors.append("Missing lifecycle result file")
        return bundle, errors
    lc_data = _load_json(lc_path)
    if not lc_data:
        errors.append("Corrupt lifecycle result JSON")
        return bundle, errors

    # --- 2. Read update ---
    update_path = source_path("_shadow_position_update_result.json")
    if not update_path:
        errors.append("Missing update result file")
        return bundle, errors
    update_data = _load_json(update_path)
    if not update_data:
        errors.append("Corrupt update result JSON")
        return bundle, errors

    # --- 3. Read scorecard ---
    sc_path = source_path("_paper_performance_scorecard.json")
    if not sc_path:
        errors.append("Missing performance scorecard file")
        return bundle, errors
    sc_data = _load_json(sc_path)
    if not sc_data:
        errors.append("Corrupt scorecard JSON")
        return bundle, errors

    # --- 4. Read gate ---
    gate_path = source_path("_shadow_sample_gate.json")
    if not gate_path:
        errors.append("Missing sample gate file")
        return bundle, errors
    gate_data = _load_json(gate_path)
    if not gate_data:
        errors.append("Corrupt gate JSON")
        return bundle, errors

    # --- 5. Read registry ---
    # The production registry has a stable, non-date-prefixed filename.
    reg_path = os.path.join(report_dir, "shadow_run_registry.jsonl")
    if not os.path.isfile(reg_path):
        # Retain compatibility with older/date-prefixed fixtures and archives.
        reg_path = _find_latest(report_dir, "_shadow_run_registry.jsonl")
    if not reg_path:
        errors.append("Missing registry file")
        return bundle, errors

    reg_records = []
    try:
        with open(reg_path) as f:
            for line in f:
                line = line.strip()
                if line:
                    reg_records.append(json.loads(line))
    except (OSError, json.JSONDecodeError) as e:
        errors.append(f"Registry read error: {e}")
        return bundle, errors

    if errors:
        return bundle, errors

    # --- Schema: required top-level fields ---
    _require_str(lc_data, "pipeline_status", "Lifecycle", errors)
    _require_str(lc_data, "date", "Lifecycle", errors)
    _require_str(update_data, "pipeline_status", "Update", errors)
    _require_str(update_data, "date", "Update", errors)
    _require_str(sc_data, "date", "Scorecard", errors)
    _require_str(gate_data, "date", "Gate", errors)

    if errors:
        return bundle, errors

    # --- Pipeline status must be PASS ---
    if lc_data["pipeline_status"] != "PASS":
        errors.append(f"Lifecycle pipeline_status='{lc_data['pipeline_status']}', not PASS")
    if update_data["pipeline_status"] != "PASS":
        errors.append(f"Update pipeline_status='{update_data['pipeline_status']}', not PASS")
    if errors:
        return bundle, errors

    # --- Step-level validation (must happen before timeline) ---
    _validate_steps(lc_data, "Lifecycle", errors)
    _validate_steps(update_data, "Update", errors)
    if errors:
        return bundle, errors

    # --- Five-way date consistency ---
    dates = {
        "lifecycle": lc_data["date"],
        "update": update_data["date"],
        "scorecard": sc_data["date"],
        "gate": gate_data["date"],
    }
    # Registry date comes from matching record (found below), validate after run_id

    if len(set(dates.values())) > 1:
        errors.append(f"Date mismatch: {dates}")
        return bundle, errors
    if report_date is not None and any(value != report_date for value in dates.values()):
        errors.append(
            f"Date mismatch against authoritative report_date={report_date}: {dates}"
        )
        return bundle, errors
    run_date = lc_data["date"]
    for label, value in dates.items():
        if _parse_iso_date(value) is None:
            errors.append(f"Date: {label} has invalid YYYY-MM-DD calendar date '{value}'")
    if errors:
        return bundle, errors

    # --- Four-way Run ID consistency ---
    lc_run_id = lc_data.get("run_id", "")
    update_run_id = update_data.get("run_id", "")
    gate_run_id = gate_data.get("latest_run_id", "")

    run_ids = {
        "lifecycle": lc_run_id,
        "update": update_run_id,
        "gate_latest": gate_run_id,
    }

    # Validate run_ids are non-empty strings
    for label, rid in run_ids.items():
        if not rid or not isinstance(rid, str):
            errors.append(f"Run ID: {label} run_id is missing or empty")
    if errors:
        return bundle, errors

    # All four must match
    if len(set(run_ids.values())) > 1:
        errors.append(f"Run ID mismatch: {run_ids}")
        return bundle, errors

    run_id = lc_run_id

    # Find exactly one matching registry record
    matching_regs = [r for r in reg_records if r.get("run_id") == run_id]
    if len(matching_regs) == 0:
        errors.append(f"Registry: no record with run_id={run_id}")
        return bundle, errors
    if len(matching_regs) > 1:
        errors.append(f"Registry: {len(matching_regs)} records with run_id={run_id}, expected 1")
        return bundle, errors
    matching_reg = matching_regs[0]

    # Registry run_id fourth source
    run_ids["registry"] = matching_reg.get("run_id", "")
    if run_ids["registry"] != run_id:
        errors.append(f"Run ID mismatch: registry={run_ids['registry']}, expected={run_id}")
        return bundle, errors

    # Registry date must match
    reg_date = matching_reg.get("date", "")
    if _parse_iso_date(reg_date) is None:
        errors.append(f"Date: registry has invalid YYYY-MM-DD calendar date '{reg_date}'")
        return bundle, errors
    if reg_date != run_date:
        errors.append(f"Date mismatch: lifecycle={run_date}, registry={reg_date}")
        return bundle, errors

    # Registry accounting_status
    if matching_reg.get("accounting_status") != "OK":
        errors.append(f"Registry accounting_status={matching_reg.get('accounting_status')}")
        return bundle, errors

    bundle["lifecycle"] = lc_data
    bundle["update"] = update_data
    bundle["scorecard"] = sc_data
    bundle["gate"] = gate_data
    bundle["registry"] = matching_reg
    bundle["run_date"] = run_date
    bundle["run_id"] = run_id

    # --- Timeline validation ---
    # Registry.finished_at >= Lifecycle.finished_at and >= Update.finished_at
    lc_finished = _latest_step_finished_at(lc_data, "Lifecycle", errors)
    update_finished = _latest_step_finished_at(update_data, "Update", errors)
    reg_finished = _parse_aware_iso_datetime(matching_reg.get("finished_at"))

    if errors:
        return bundle, errors

    if not reg_finished:
        errors.append("Registry finished_at is missing or invalid")
        return bundle, errors

    if lc_finished and reg_finished < lc_finished:
        errors.append(
            f"Timeline: Registry finished_at ({matching_reg.get('finished_at')}) "
            f"< Lifecycle latest step finished_at ({lc_finished.isoformat()})"
        )
    if update_finished and reg_finished < update_finished:
        errors.append(
            f"Timeline: Registry finished_at ({matching_reg.get('finished_at')}) "
            f"< Update latest step finished_at ({update_finished.isoformat()})"
        )
    if errors:
        return bundle, errors

    # Also check registry started_at <= finished_at
    reg_started = _parse_aware_iso_datetime(matching_reg.get("started_at"))
    if reg_started is None:
        errors.append("Registry started_at is missing, invalid, or lacks timezone")
        return bundle, errors
    if reg_started > reg_finished:
        errors.append("Timeline: Registry started_at > finished_at")
        return bundle, errors

    now_utc = datetime.now(timezone.utc)
    if reg_finished.astimezone(timezone.utc) > now_utc + timedelta(minutes=5):
        errors.append("Timeline: Registry finished_at is more than 5 minutes in the future")
        return bundle, errors

    # Completion time = registry.finished_at (authoritative)
    completion_time = matching_reg.get("finished_at", "")

    bundle["completion_time"] = str(completion_time)

    # --- Accounting validation ---
    eligible, all_canonical, diag = load_canonical_closed_clean_positions(report_dir)
    if diag.get("accounting_status") != "OK":
        errors.append(f"Accounting status: {diag.get('accounting_status')}")
        for fe in diag.get("fatal_errors", []):
            errors.append(f"  fatal: {fe}")
        return bundle, errors

    bundle["eligible"] = eligible
    bundle["all_canonical"] = all_canonical
    bundle["diag"] = diag

    # --- Six-way count verification (all mandatory) ---
    canonical_count = len(eligible)

    # Scorecard global_metrics.closed_positions
    sc_global = sc_data.get("global_metrics")
    if not isinstance(sc_global, dict):
        errors.append("Scorecard: global_metrics is missing or not a dict")
        return bundle, errors
    sc_global_closed = _require_nonnegative_int(
        sc_global, "closed_positions", "Scorecard global_metrics", errors,
    )

    # Scorecard strategy sum
    sc_strategies = sc_data.get("strategy_scorecards")
    if not isinstance(sc_strategies, list):
        errors.append("Scorecard: strategy_scorecards is missing or not a list")
        return bundle, errors
    if canonical_count > 0 and len(sc_strategies) == 0:
        errors.append("Scorecard: strategy_scorecards is empty but canonical count > 0")
        return bundle, errors

    sc_strat_sum = 0
    for i, strat in enumerate(sc_strategies):
        if not isinstance(strat, dict):
            errors.append(f"Scorecard: strategy_scorecards[{i}] is not a dict")
            continue
        cc = _require_nonnegative_int(
            strat, "closed_count", f"Scorecard strategy[{i}]", errors,
        )
        if cc is not None:
            sc_strat_sum += cc

    # Scorecard top-level cumulative_closed_clean
    sc_cumulative = _require_nonnegative_int(
        sc_data, "cumulative_closed_clean", "Scorecard", errors,
    )

    # Gate cumulative_closed_clean
    gate_cumulative = _require_nonnegative_int(
        gate_data, "cumulative_closed_clean", "Gate", errors,
    )

    # Registry cumulative_closed_clean
    reg_cumulative = _require_nonnegative_int(
        matching_reg, "cumulative_closed_clean", "Registry", errors,
    )

    if errors:
        return bundle, errors

    counts = {
        "canonical": canonical_count,
        "scorecard_global": sc_global_closed,
        "scorecard_strategy_sum": sc_strat_sum,
        "scorecard_cumulative": sc_cumulative,
        "gate_cumulative": gate_cumulative,
        "registry_cumulative": reg_cumulative,
    }

    # All six must agree
    values = set(counts.values())
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
<h2>{net_title}</h2>
<table>
<tr><th>Gross PF</th><td>{gross_pf}</td><th>Net PF</th><td>{net_pf}</td></tr>
<tr><th>Gross Expectancy R</th><td>{gross_expectancy}</td><th>Net Expectancy R</th><td>{net_expectancy}</td></tr>
<tr><th>Mean Friction R</th><td>{mean_friction}</td><th>Median Friction R</th><td>{median_friction}</td></tr>
<tr><th>Model</th><td>{net_model}</td><th>Status</th><td>{net_status}</td></tr>
<tr><th>Assumptions Hash</th><td colspan="3">{net_hash}</td></tr>
<tr><th>P1-03 Trusted Closed</th><td colspan="3">{net_trusted_closed}</td></tr>
<tr><th>Eligible / Complete</th><td>{net_eligible} / {net_complete_count}</td><th>Coverage</th><td>{net_coverage}</td></tr>
<tr><th>Partial / Invalid+Unavailable</th><td>{net_partial} / {net_invalid_unavailable}</td><th>Trusted Status</th><td>{net_metrics_status}</td></tr>
<tr><th>Matched Gross / Net PF</th><td>{matched_gross_pf} / {diagnostic_net_pf}</td><th>Selection Bias</th><td>{selection_bias_warning}</td></tr>
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
        ct_parsed = _parse_aware_iso_datetime(completion_time)
        if ct_parsed:
            ct_utc = ct_parsed.astimezone(timezone.utc) if ct_parsed.tzinfo else ct_parsed.replace(tzinfo=timezone.utc)
            age = max(0.0, (datetime.now(timezone.utc) - ct_utc).total_seconds() / 60)
            data_age_minutes = str(round(age, 1))
            freshness_status = "fresh" if age <= 90 else ("stale" if age <= 180 else "expired")

    global_metrics = sc.get("global_metrics", {})
    net = sc.get("net_friction") if isinstance(sc.get("net_friction"), dict) else {}
    net_complete = net.get("complete_metrics") or {}
    net_trusted = net.get("trusted_metrics") or {}
    net_metrics = (
        net_trusted if net_trusted.get("eligible_closed_count", 0) > 0 else net_complete
    )
    _, _, gross_pf_display = _public_profit_factor(
        net.get("gross_profit_factor", global_metrics.get("profit_factor"))
    )
    net_headline_allowed = str(net_metrics.get("net_metrics_status", "")).startswith("COMPLETE_")
    net_pf_display = net_metrics.get("net_profit_factor") if net_headline_allowed else None
    if net_metrics.get("net_profit_factor_status") == "INFINITE":
        net_pf_display = "∞"
    if net_pf_display is None:
        net_pf_display = "—"
    sample_status = gate.get("sample_status", "UNKNOWN")
    gate_status = gate.get("testnet_gate_status", "UNKNOWN")

    # Strategy rows — all values escaped
    strat_rows = []
    for s in sc.get("strategy_scorecards", []):
        _, _, pf_display = _public_profit_factor(s.get("profit_factor"))
        strat_rows.append(
            f"<tr><td>{_html(s.get('strategy_id',''))}</td>"
            f"<td>{_html(s.get('closed_count',0))}</td>"
            f"<td>{_html(round(s.get('win_rate',0)*100,1))}%</td>"
            f"<td>{_html(pf_display)}</td>"
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
        net_title="净摩擦核算" if lang == "zh" else "Net Friction Accounting",
        gross_pf=_html(gross_pf_display),
        net_pf=_html(net_pf_display),
        gross_expectancy=_html(net.get("gross_expectancy_r", global_metrics.get("expectancy_r"))),
        net_expectancy=_html(
            (net_metrics.get("net_expectancy_r") if net_headline_allowed else None) or "—"
        ),
        mean_friction=_html(net_metrics.get("mean_friction_r") or "—"),
        median_friction=_html(net_metrics.get("median_friction_r") or "—"),
        net_model=_html(net.get("friction_model_version") or "net_friction_v1"),
        net_status=_html(net.get("model_configuration_status") or "UNCONFIGURED"),
        net_hash=_html(net.get("friction_assumptions_hash") or "—"),
        net_trusted_closed=_html(net_trusted.get("net_complete_closed_count", 0)),
        net_eligible=_html(net_metrics.get("eligible_closed_count", 0)),
        net_complete_count=_html(net_metrics.get("complete_assessment_count", 0)),
        net_coverage=_html(net_metrics.get("net_coverage_ratio", "0")),
        net_partial=_html(net_metrics.get("partial_assessment_count", 0)),
        net_invalid_unavailable=_html(
            net_metrics.get("invalid_assessment_count", 0)
            + net_metrics.get("unavailable_assessment_count", 0)
        ),
        net_metrics_status=_html(net_metrics.get("net_metrics_status", "NO_SAMPLE")),
        matched_gross_pf=_html(net_metrics.get("matched_subset_gross_pf") or "—"),
        diagnostic_net_pf=_html(net_metrics.get("diagnostic_complete_subset_net_pf") or "—"),
        selection_bias_warning=_html(net_metrics.get("selection_bias_warning") or "NO"),
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
        pf_value, pf_status, _ = _public_profit_factor(s.get("profit_factor"))
        strategies[sid] = {
            "strategy_id": sid,
            "closed_count": s.get("closed_count"),
            "win_rate": round(s.get("win_rate", 0) * 100, 1),
            "profit_factor": pf_value,
            "profit_factor_status": pf_status,
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
            "signal_bar_close_time": p.get("signal_bar_close_time"),
            "signal_bar_contract_version": p.get("signal_bar_contract_version"),
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
            "signal_bar_close_time": p.get("signal_bar_close_time"),
            "signal_bar_contract_version": p.get("signal_bar_contract_version"),
        })

    # Freshness (based on real completion time)
    data_age_minutes = None
    freshness_status = "unknown"
    if completion_time:
        ct_parsed = _parse_aware_iso_datetime(completion_time)
        if ct_parsed:
            ct_utc = ct_parsed.astimezone(timezone.utc) if ct_parsed.tzinfo else ct_parsed.replace(tzinfo=timezone.utc)
            age = max(0.0, (datetime.now(timezone.utc) - ct_utc).total_seconds() / 60)
            data_age_minutes = round(age, 1)
            freshness_status = "fresh" if age <= 90 else ("stale" if age <= 180 else "expired")

    global_metrics = sc.get("global_metrics", {})
    net = sc.get("net_friction") if isinstance(sc.get("net_friction"), dict) else {}
    net_complete = net.get("complete_metrics") or {}
    net_trusted = net.get("trusted_metrics") or {}
    net_metrics = (
        net_trusted if net_trusted.get("eligible_closed_count", 0) > 0 else net_complete
    )
    public_gross_pf, public_gross_pf_status, _ = _public_profit_factor(
        net.get("gross_profit_factor", global_metrics.get("profit_factor"))
    )

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
        "fee_adjusted": net_complete.get("net_complete_closed_count", 0) > 0,
        "slippage_adjusted": net_complete.get("net_complete_closed_count", 0) > 0,
        "gross_profit_factor": public_gross_pf,
        "gross_profit_factor_status": public_gross_pf_status,
        "net_profit_factor": (
            net_metrics.get("net_profit_factor")
            if str(net_metrics.get("net_metrics_status", "")).startswith("COMPLETE_") else None
        ),
        "net_profit_factor_status": (
            net_metrics.get("net_profit_factor_status", "NO_SAMPLE")
            if str(net_metrics.get("net_metrics_status", "")).startswith("COMPLETE_") else "NO_RESULT"
        ),
        "gross_expectancy_r": net.get("gross_expectancy_r", global_metrics.get("expectancy_r")),
        "net_expectancy_r": (
            net_metrics.get("net_expectancy_r")
            if str(net_metrics.get("net_metrics_status", "")).startswith("COMPLETE_") else None
        ),
        "eligible_net_population": net_metrics.get("eligible_closed_count", 0),
        "net_complete_count": net_metrics.get("complete_assessment_count", 0),
        "net_partial_count": net_metrics.get("partial_assessment_count", 0),
        "net_invalid_count": net_metrics.get("invalid_assessment_count", 0),
        "net_unavailable_count": net_metrics.get("unavailable_assessment_count", 0),
        "net_coverage_ratio": net_metrics.get("net_coverage_ratio", "0"),
        "net_metrics_status": net_metrics.get("net_metrics_status", "NO_SAMPLE"),
        "diagnostic_matched_subset_gross_pf": net_metrics.get("matched_subset_gross_pf"),
        "diagnostic_matched_subset_net_pf": net_metrics.get("diagnostic_complete_subset_net_pf"),
        "diagnostic_matched_subset_gross_expectancy": net_metrics.get("matched_subset_gross_expectancy"),
        "diagnostic_matched_subset_net_expectancy": net_metrics.get("diagnostic_complete_subset_net_expectancy"),
        "excluded_by_close_reason": net_metrics.get("excluded_by_close_reason", {}),
        "selection_bias_warning": net_metrics.get("selection_bias_warning"),
        "mean_friction_r": net_metrics.get("mean_friction_r"),
        "median_friction_r": net_metrics.get("median_friction_r"),
        "friction_component_totals_r": {
            key: net_metrics.get(key) for key in (
                "fee_effect_r", "spread_effect_r", "slippage_effect_r",
                "funding_effect_r", "gap_effect_r",
            )
        },
        "friction_model_version": net.get("friction_model_version", "net_friction_v1"),
        "friction_model_status": net.get("model_configuration_status", "UNCONFIGURED"),
        "friction_assumptions_hash": net.get("friction_assumptions_hash"),
        "p1_03_activation": net.get("p1_03_activation", {}),
        "p1_03_trusted_closed": net_trusted.get("net_complete_closed_count", 0),
        "testnet_enabled": False,
        "live_enabled": False,
        "p1_02_trusted_cohort_closed": sc.get("diagnostics", {}).get(
            "p1_02_trusted_cohort_closed", 0
        ),
        "p1_02_trusted_cohort_start_at": sc.get("diagnostics", {}).get(
            "p1_02_trusted_cohort_start_at"
        ),
        "p1_02_trusted_cohort_rule_version": sc.get("diagnostics", {}).get(
            "p1_02_trusted_cohort_rule_version"
        ),
        "p1_02_trusted_cohort_start_run_id": sc.get("diagnostics", {}).get(
            "p1_02_trusted_cohort_start_run_id"
        ),
        "p1_02_trusted_cohort_start_commit": sc.get("diagnostics", {}).get(
            "p1_02_trusted_cohort_start_commit"
        ),
        "closed_bar_trusted_cohort_start_at": sc.get("diagnostics", {}).get(
            "closed_bar_trusted_cohort_start_at"
        ),
        "closed_bar_trusted_cohort_rule_version": sc.get("diagnostics", {}).get(
            "closed_bar_trusted_cohort_rule_version"
        ),
        "closed_bar_trusted_cohort_start_run_id": sc.get("diagnostics", {}).get(
            "closed_bar_trusted_cohort_start_run_id"
        ),
        "closed_bar_trusted_cohort_start_commit": sc.get("diagnostics", {}).get(
            "closed_bar_trusted_cohort_start_commit"
        ),
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


def _set_exact_mode(path: str, mode: int) -> None:
    """Set and verify an exact filesystem mode without changing ownership."""
    os.chmod(path, mode)
    actual = stat.S_IMODE(os.stat(path).st_mode)
    if actual != mode:
        raise PermissionError(
            f"Mode verification failed for {path}: "
            f"expected={oct(mode)}, actual={oct(actual)}"
        )


def _set_exact_fd_mode(fd: int, path: str, mode: int) -> None:
    """Set and verify an exact mode while the published file is still open."""
    os.fchmod(fd, mode)
    actual = stat.S_IMODE(os.fstat(fd).st_mode)
    if actual != mode:
        raise PermissionError(
            f"Mode verification failed for {path}: "
            f"expected={oct(mode)}, actual={oct(actual)}"
        )


def _verify_exact_mode(path: str, mode: int) -> None:
    actual = stat.S_IMODE(os.stat(path).st_mode)
    if actual != mode:
        raise PermissionError(
            f"Mode verification failed for {path}: "
            f"expected={oct(mode)}, actual={oct(actual)}"
        )


_VERSION_PATTERN = re.compile(r"^\d{8}-\d{6}-[0-9a-f]{8}$")


def _cleanup_old_releases(releases_dir: str, current_target: str, keep: int = MAX_RELEASES) -> list[str]:
    """Remove old releases, keeping at most `keep` valid versions.

    Always retains the current target. Sorts by mtime then name.
    Only considers directories matching the version naming pattern.
    Returns list of warnings (non-fatal).
    """
    warnings: list[str] = []
    try:
        all_entries = os.listdir(releases_dir)
    except OSError:
        return warnings

    current_version = current_target.split("/")[-1] if current_target else ""

    # Collect only valid release directories
    valid_releases = []
    for entry in all_entries:
        if not _VERSION_PATTERN.match(entry):
            continue
        entry_path = os.path.join(releases_dir, entry)
        if not os.path.isdir(entry_path):
            continue
        try:
            mtime = os.stat(entry_path).st_mtime_ns
        except OSError:
            mtime = 0
        valid_releases.append((mtime, entry, entry_path))

    # Sort by mtime descending, then name descending as tiebreaker
    valid_releases.sort(key=lambda x: (x[0], x[1]), reverse=True)

    # Build keep set: current + (keep-1) newest
    keep_set = {current_version}
    for _, name, _ in valid_releases:
        if len(keep_set) >= keep:
            break
        keep_set.add(name)

    # Remove everything not in keep_set
    for _, name, path in valid_releases:
        if name in keep_set:
            continue
        try:
            shutil.rmtree(path)
        except OSError as e:
            warnings.append(f"Failed to remove old release {name}: {e}")

    return warnings


def generate_console(
    report_dir: str,
    output_dir: str,
    server_commit: str = "",
    report_date: str | None = None,
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
    bundle, errors = validate_inputs(report_dir, report_date=report_date)
    if errors:
        result["errors"] = errors
        return result

    # 2-3. Render public representations; invalid metric semantics fail closed.
    try:
        html_zh = render_readonly_html(bundle, lang="zh", server_commit=server_commit)
        html_en = render_readonly_html(bundle, lang="en", server_commit=server_commit)
        public_json = build_public_json(bundle, server_commit=server_commit)
    except (ValueError, TypeError, OverflowError) as e:
        result["errors"].append(f"Public metric rendering failed: {e}")
        return result
    try:
        json_str = json.dumps(
            public_json, ensure_ascii=False, indent=2, allow_nan=False,
        )
    except (ValueError, TypeError, OverflowError) as e:
        result["errors"].append(f"JSON serialization failed: {e}")
        return result

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

    current_switched = False
    try:
        # The public root and Generator-managed directories must be traversable
        # by the Nginx worker regardless of the service process umask.
        os.makedirs(output_dir, exist_ok=True)
        _set_exact_mode(output_dir, PUBLIC_DIRECTORY_MODE)

        # Create releases directory
        os.makedirs(releases_dir, exist_ok=True)
        _set_exact_mode(releases_dir, PUBLIC_DIRECTORY_MODE)

        # Create version directory (temp name first)
        os.makedirs(tmp_version_dir, exist_ok=True)
        _set_exact_mode(tmp_version_dir, PUBLIC_DIRECTORY_MODE)

        # Write, fsync, and make each file publicly readable before it can be
        # renamed into a release that current may reference.
        for filename, content in files.items():
            filepath = os.path.join(tmp_version_dir, filename)
            fd, tmp_path = tempfile.mkstemp(dir=tmp_version_dir, suffix=".tmp")
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as f:
                    f.write(content)
                    f.flush()
                    os.fsync(f.fileno())
                    _set_exact_fd_mode(f.fileno(), tmp_path, PUBLIC_FILE_MODE)
                    os.fsync(f.fileno())
                os.replace(tmp_path, filepath)
            except Exception as e:
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass
                raise

            _fsync_file(filepath)
            _verify_exact_mode(filepath, PUBLIC_FILE_MODE)

        # Verify the complete temporary release before finalizing it.
        _set_exact_mode(tmp_version_dir, PUBLIC_DIRECTORY_MODE)
        for filename in files:
            _verify_exact_mode(os.path.join(tmp_version_dir, filename), PUBLIC_FILE_MODE)
        _fsync_dir(tmp_version_dir)

        # Rename temp version dir to final
        os.replace(tmp_version_dir, version_dir)
        _verify_exact_mode(output_dir, PUBLIC_DIRECTORY_MODE)
        _verify_exact_mode(releases_dir, PUBLIC_DIRECTORY_MODE)
        _verify_exact_mode(version_dir, PUBLIC_DIRECTORY_MODE)
        for filename in files:
            _verify_exact_mode(os.path.join(version_dir, filename), PUBLIC_FILE_MODE)
        _fsync_dir(releases_dir)

        # Create temp symlink and atomic replace
        if os.path.islink(current_tmp):
            os.unlink(current_tmp)
        os.symlink(os.path.join("releases", version_id), current_tmp)

        # Atomic replace current symlink
        os.replace(current_tmp, current_link)
        current_switched = True
        _fsync_dir(output_dir)

        result["success"] = True
        result["version_id"] = version_id
        result["release_dir"] = version_dir
        result["current_target"] = os.path.join("releases", version_id)
        result["public_root"] = os.path.join(output_dir, "current")
        result["required_nginx_alias"] = os.path.join(output_dir, "current") + "/"

        # 8. Cleanup old releases (after successful switch)
        cleanup_warnings = _cleanup_old_releases(releases_dir, result["current_target"])
        if cleanup_warnings:
            result["warnings"] = cleanup_warnings

    except Exception as e:
        # Clean up temp artifacts
        cleanup_paths = [current_tmp, tmp_version_dir]
        if not current_switched:
            cleanup_paths.append(version_dir)
        for cleanup in cleanup_paths:
            try:
                if os.path.islink(cleanup):
                    os.unlink(cleanup)
                elif os.path.isdir(cleanup):
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
    parser.add_argument("--report-date", default=None,
                        help="Authoritative Asia/Shanghai report date (YYYY-MM-DD)")
    args = parser.parse_args()

    # Validate server commit format if provided
    if args.server_commit:
        if not re.match(r"^[0-9a-f]{7,40}$", args.server_commit):
            print(f"ERROR: Invalid server commit hash: {args.server_commit}")
            return 1

    result = generate_console(
        args.report_dir,
        args.output_dir,
        args.server_commit,
        report_date=args.report_date,
    )

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
