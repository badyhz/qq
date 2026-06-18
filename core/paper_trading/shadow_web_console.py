"""Shadow Web Console — local-only web dashboard for shadow trading.

Provides:
- Dashboard with current status from reports
- Action buttons to trigger shadow-only scripts
- Report file viewer (safe path only)
- Action logging

All actions use subprocess with shell=False, timeout=300.
No network binding except 127.0.0.1/localhost.
No orders, no accounts, no secrets, no testnet, no live.
"""
from __future__ import annotations

import glob
import json
import os
import re
import subprocess
import sys
from datetime import datetime
from typing import Any, Optional
from urllib.parse import parse_qs, urlparse

REPORT_DIR_NAME = "reports"
STRATEGIES_DIR = "strategies"
ALLOWED_EXTENSIONS = {".json", ".md", ".csv", ".jsonl", ".txt"}

ALLOWED_ACTIONS = {
    "run-lifecycle": {
        "label": "扫描新机会 + 更新持仓",
        "command": [sys.executable, "scripts/run_shadow_trading_lifecycle.py", "--allow-public-http"],
    },
    "run-update-only": {
        "label": "只更新已有持仓",
        "command": [sys.executable, "scripts/run_shadow_position_update_only.py", "--allow-public-http"],
    },
    "run-sample-gate": {
        "label": "刷新样本门禁",
        "command": [sys.executable, "scripts/run_sample_collection_gate.py"],
    },
    "print-status": {
        "label": "打印当前状态",
        "command": [sys.executable, "scripts/print_shadow_operator_status.py"],
    },
}

SAFETY_FLAGS = [
    "PAPER_ONLY", "SHADOW_ONLY", "NO_SECRET", "NO_ENV_READ",
    "NO_ACCOUNT", "NO_ORDER", "NO_REAL_ORDER", "NO_TESTNET", "NO_LIVE",
    "NO_WEBSOCKET", "NO_PRIVATE_ENDPOINT", "NO_WEBHOOK_SEND",
    "LOCAL_ONLY", "CONSOLE_READ_WRITE",
]


def _ts() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _today_str() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def _find_latest(report_dir: str, suffix: str) -> Optional[str]:
    """Find the most recent file matching suffix pattern."""
    pattern = os.path.join(report_dir, f"*{suffix}")
    files = sorted(glob.glob(pattern))
    return files[-1] if files else None


def _load_json(path: str) -> Optional[dict]:
    try:
        with open(path) as f:
            return json.load(f)
    except Exception:
        return None


def is_safe_report_name(name: str) -> bool:
    """Check if report name is safe (no path traversal, valid extension)."""
    if not name:
        return False
    # No path separators
    if "/" in name or "\\" in name or ".." in name:
        return False
    # Must have allowed extension
    _, ext = os.path.splitext(name)
    if ext not in ALLOWED_EXTENSIONS:
        return False
    # No null bytes
    if "\x00" in name:
        return False
    return True


def load_console_status(report_dir: str) -> dict[str, Any]:
    """Load status from report files for dashboard display."""
    status: dict[str, Any] = {}

    # Sample gate
    gate_path = _find_latest(report_dir, "_shadow_sample_gate.json")
    if gate_path and os.path.isfile(gate_path):
        gate = _load_json(gate_path)
        if gate:
            status["sample_status"] = gate.get("sample_status", "UNKNOWN")
            status["testnet_gate_status"] = gate.get("testnet_gate_status", "UNKNOWN")
            status["gate_reasons"] = gate.get("gate_reasons", [])

    # Scorecard
    sc_path = _find_latest(report_dir, "_paper_performance_scorecard.json")
    if sc_path and os.path.isfile(sc_path):
        sc = _load_json(sc_path)
        if sc:
            gm = sc.get("global_metrics", {})
            status["clean_positions"] = gm.get("clean_positions", 0)
            status["closed_clean_positions"] = gm.get("closed_positions", 0)
            status["excluded_positions"] = gm.get("excluded_positions", 0)
            status["open_positions"] = gm.get("open_positions", 0)
            status["win_rate"] = gm.get("win_rate", 0.0)
            status["profit_factor"] = gm.get("profit_factor", 0.0)

    # Quarantine
    q_path = _find_latest(report_dir, "_paper_positions_quarantine.json")
    if q_path and os.path.isfile(q_path):
        q = _load_json(q_path)
        if q:
            status["quarantined_count"] = q.get("quarantined_count", 0)

    # Latest lifecycle result
    lc_path = _find_latest(report_dir, "_shadow_lifecycle_result.json")
    if lc_path and os.path.isfile(lc_path):
        lc = _load_json(lc_path)
        if lc:
            status["lifecycle_status"] = lc.get("pipeline_status", "UNKNOWN")
            status["lifecycle_date"] = lc.get("date", "")

    # Latest update-only result
    uo_path = _find_latest(report_dir, "_shadow_position_update_result.json")
    if uo_path and os.path.isfile(uo_path):
        uo = _load_json(uo_path)
        if uo:
            status["update_only_status"] = uo.get("pipeline_status", "UNKNOWN")
            status["update_only_date"] = uo.get("date", "")

    return status


def find_latest_report(report_dir: str, suffix: str) -> Optional[str]:
    """Public wrapper for _find_latest."""
    return _find_latest(report_dir, suffix)


def render_report_file(report_dir: str, name: str) -> Optional[str]:
    """Safely read a report file. Returns content or None if unsafe/missing."""
    if not is_safe_report_name(name):
        return None
    path = os.path.join(report_dir, name)
    if not os.path.isfile(path):
        return None
    try:
        with open(path) as f:
            return f.read()
    except Exception:
        return None


def run_allowed_action(action: str, repo_root: str, report_dir: str) -> dict[str, Any]:
    """Run an allowed action. Returns result dict."""
    if action not in ALLOWED_ACTIONS:
        return {
            "action": action,
            "status": "REJECTED",
            "error": f"Unknown action: {action}",
            "started_at": _ts(),
            "finished_at": _ts(),
        }

    action_def = ALLOWED_ACTIONS[action]
    cmd = list(action_def["command"])
    started = _ts()
    t0 = datetime.now()

    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300,
            cwd=repo_root,
            shell=False,
        )
        exit_code = proc.returncode
        stdout_tail = "\n".join(proc.stdout.strip().splitlines()[-15:])
        stderr_tail = "\n".join(proc.stderr.strip().splitlines()[-5:])
        status = "PASS" if exit_code == 0 else "FAIL"
    except subprocess.TimeoutExpired:
        exit_code, stdout_tail, stderr_tail, status = -1, "", "TIMEOUT after 300s", "FAIL"
    except Exception as e:
        exit_code, stdout_tail, stderr_tail, status = -1, "", str(e), "FAIL"

    finished = _ts()
    duration = (datetime.now() - t0).total_seconds()

    result = {
        "action": action,
        "label": action_def["label"],
        "command": cmd,
        "started_at": started,
        "finished_at": finished,
        "duration_seconds": round(duration, 2),
        "exit_code": exit_code,
        "status": status,
        "stdout_tail": stdout_tail,
        "stderr_tail": stderr_tail,
        "safety_flags": list(SAFETY_FLAGS),
    }

    append_action_log(result, report_dir)
    return result


def append_action_log(result: dict, report_dir: str) -> None:
    """Append action result to daily JSONL log."""
    os.makedirs(report_dir, exist_ok=True)
    log_path = os.path.join(report_dir, f"{_today_str()}_shadow_web_console_actions.jsonl")
    try:
        with open(log_path, "a") as f:
            f.write(json.dumps(result) + "\n")
    except Exception:
        pass


def _escape_html(text: str) -> str:
    """Escape HTML special characters."""
    import html as html_mod
    return html_mod.escape(str(text))


def load_latest_positions(report_dir: str) -> list[dict]:
    """Load positions from latest quarantine JSON."""
    path = _find_latest(report_dir, "_paper_positions_quarantine.json")
    if not path or not os.path.isfile(path):
        return []
    data = _load_json(path)
    if not data:
        return []
    return data.get("positions", [])


def load_latest_scorecard(report_dir: str) -> dict:
    """Load scorecard data from latest scorecard JSON."""
    path = _find_latest(report_dir, "_paper_performance_scorecard.json")
    if not path or not os.path.isfile(path):
        return {}
    data = _load_json(path)
    if not data:
        return {}
    return {
        "global_metrics": data.get("global_metrics", {}),
        "strategy_scorecards": data.get("strategy_scorecards", []),
    }


def load_latest_sample_gate(report_dir: str) -> dict:
    """Load sample gate data from latest gate JSON."""
    path = _find_latest(report_dir, "_shadow_sample_gate.json")
    if not path or not os.path.isfile(path):
        return {}
    data = _load_json(path)
    if not data:
        return {}
    return data


def load_recent_actions(report_dir: str, limit: int = 10) -> list[dict]:
    """Load recent actions from JSONL log."""
    path = _find_latest(report_dir, "_shadow_web_console_actions.jsonl")
    if not path or not os.path.isfile(path):
        return []
    actions = []
    try:
        with open(path) as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        actions.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
    except Exception:
        return []
    return actions[-limit:]


_STATUS_ORDER = {
    "OPEN": 0, "TAKE_PROFIT_HIT": 1, "STOP_LOSS_HIT": 2,
    "TIMEOUT_EXIT": 3, "LEGACY": 4,
}


def _position_sort_key(p: dict) -> tuple:
    s = p.get("status", "OPEN")
    order = _STATUS_ORDER.get(s, 5)
    excluded = p.get("excluded_from_performance_stats", False)
    return (order, 1 if excluded else 0)


def render_positions_table(positions: list[dict], limit: int = 50) -> str:
    """Render positions as HTML table."""
    if not positions:
        return "<p>No positions found.</p>"

    sorted_pos = sorted(positions, key=_position_sort_key)[:limit]

    rows = []
    for p in sorted_pos:
        status = p.get("status", "")
        excluded = p.get("excluded_from_performance_stats", False)
        row_class = "excluded" if excluded else status.lower()
        rows.append(
            f'<tr class="{row_class}">'
            f"<td>{_escape_html(status)}</td>"
            f"<td>{_escape_html(p.get('strategy_id', ''))}</td>"
            f"<td>{_escape_html(p.get('symbol', ''))}</td>"
            f"<td>{_escape_html(p.get('timeframe', ''))}</td>"
            f"<td>{_escape_html(p.get('side', ''))}</td>"
            f"<td>{p.get('entry_price', '')}</td>"
            f"<td>{p.get('stop_loss', '')}</td>"
            f"<td>{p.get('take_profit', '')}</td>"
            f"<td>{p.get('unrealized_pnl', 0):.4f}</td>"
            f"<td>{p.get('realized_pnl', 0):.4f}</td>"
            f"<td>{p.get('r_multiple', 0):.2f}</td>"
            f"<td>{_escape_html(p.get('quarantine_status', ''))}</td>"
            f"<td>{'Yes' if excluded else 'No'}</td>"
            f"</tr>"
        )

    table = f"""<table>
<thead><tr>
<th>Status</th><th>Strategy</th><th>Symbol</th><th>TF</th><th>Side</th>
<th>Entry</th><th>SL</th><th>TP</th><th>Unreal PnL</th><th>Real PnL</th>
<th>R</th><th>Quarantine</th><th>Excluded</th>
</tr></thead>
<tbody>
{''.join(rows)}
</tbody></table>"""

    # Stats cards
    open_count = sum(1 for p in positions if p.get("status") == "OPEN")
    tp_count = sum(1 for p in positions if p.get("status") == "TAKE_PROFIT_HIT")
    sl_count = sum(1 for p in positions if p.get("status") == "STOP_LOSS_HIT")
    timeout_count = sum(1 for p in positions if p.get("status") == "TIMEOUT_EXIT")
    quarantined = sum(1 for p in positions if p.get("excluded_from_performance_stats", False))
    clean = len(positions) - quarantined

    cards = f"""<div class="status-grid">
  <div class="status-item"><div class="status-label">OPEN</div><div class="status-value">{open_count}</div></div>
  <div class="status-item"><div class="status-label">TP HIT</div><div class="status-value ok">{tp_count}</div></div>
  <div class="status-item"><div class="status-label">SL HIT</div><div class="status-value blocked">{sl_count}</div></div>
  <div class="status-item"><div class="status-label">TIMEOUT</div><div class="status-value warn">{timeout_count}</div></div>
  <div class="status-item"><div class="status-label">Quarantined</div><div class="status-value warn">{quarantined}</div></div>
  <div class="status-item"><div class="status-label">Clean</div><div class="status-value ok">{clean}</div></div>
</div>"""

    return cards + table


def render_scorecard_table(scorecards: list[dict], sample_status: str = "") -> str:
    """Render strategy scorecards as HTML table."""
    if not scorecards:
        return "<p>No strategy scorecards found.</p>"

    rows = []
    for sc in scorecards:
        rows.append(
            f"<tr>"
            f"<td>{_escape_html(sc.get('strategy_id', ''))}</td>"
            f"<td>{_escape_html(sc.get('strategy_type', ''))}</td>"
            f"<td>{sc.get('position_count', 0)}</td>"
            f"<td>{sc.get('open_count', 0)}</td>"
            f"<td>{sc.get('closed_count', 0)}</td>"
            f"<td>{sc.get('tp_count', 0)}</td>"
            f"<td>{sc.get('sl_count', 0)}</td>"
            f"<td>{sc.get('timeout_count', 0)}</td>"
            f"<td>{sc.get('win_rate', 0):.2%}</td>"
            f"<td>{sc.get('profit_factor', 0):.2f}</td>"
            f"<td>{sc.get('expectancy_r', 0):.2f}</td>"
            f"<td>{_escape_html(sc.get('sample_status', ''))}</td>"
            f"<td>{_escape_html(sc.get('strategy_status', ''))}</td>"
            f"<td>{sc.get('strategy_score', 0):.2f}</td>"
            f"</tr>"
        )

    table = f"""<table>
<thead><tr>
<th>Strategy</th><th>Type</th><th>Total</th><th>Open</th><th>Closed</th>
<th>TP</th><th>SL</th><th>Timeout</th><th>Win Rate</th><th>PF</th>
<th>Exp R</th><th>Sample</th><th>Status</th><th>Score</th>
</tr></thead>
<tbody>
{''.join(rows)}
</tbody></table>"""

    warning = ""
    if sample_status == "INSUFFICIENT_CLOSED_SAMPLE":
        warning = '<div class="next-action"><strong>样本不足</strong>，继续 shadow，不允许 testnet/live。</div>'

    return warning + table


def render_sample_gate_card(gate: dict) -> str:
    """Render sample gate status card."""
    if not gate:
        return "<p>No sample gate data found.</p>"

    sample = gate.get("sample_status", "UNKNOWN")
    testnet = gate.get("testnet_gate_status", "UNKNOWN")
    closed = gate.get("closed_clean_positions", 0)
    reasons = gate.get("testnet_gate_reasons", [])

    status_class = "blocked" if "BLOCKED" in testnet else "ok"

    reasons_html = ""
    if reasons:
        items = "".join(f"<li>{_escape_html(r)}</li>" for r in reasons)
        reasons_html = f"<ul>{items}</ul>"

    return f"""<div class="status-grid">
  <div class="status-item">
    <div class="status-label">sample_status</div>
    <div class="status-value {'blocked' if 'INSUFFICIENT' in sample else 'warn' if 'LOW' in sample else 'ok'}">{_escape_html(sample)}</div>
  </div>
  <div class="status-item">
    <div class="status-label">testnet_gate_status</div>
    <div class="status-value {status_class}">{_escape_html(testnet)}</div>
  </div>
  <div class="status-item">
    <div class="status-label">closed_clean_positions</div>
    <div class="status-value">{closed}</div>
  </div>
</div>
{reasons_html}"""


def render_recent_actions_table(actions: list[dict]) -> str:
    """Render recent actions as HTML table."""
    if not actions:
        return "<p>No web console actions yet.</p>"

    rows = []
    for a in reversed(actions):
        status_class = "ok" if a.get("status") == "PASS" else "blocked"
        rows.append(
            f"<tr>"
            f"<td>{_escape_html(a.get('action', ''))}</td>"
            f"<td>{_escape_html(a.get('started_at', ''))}</td>"
            f"<td>{a.get('duration_seconds', 0)}s</td>"
            f"<td>{a.get('exit_code', '')}</td>"
            f'<td class="{status_class}">{_escape_html(a.get("status", ""))}</td>'
            f"</tr>"
        )

    return f"""<table>
<thead><tr>
<th>Action</th><th>Started</th><th>Duration</th><th>Exit</th><th>Status</th>
</tr></thead>
<tbody>
{''.join(rows)}
</tbody></table>"""


def load_strategy_config(config_path: str) -> Optional[dict]:
    """Load strategy config from YAML file. Read-only."""
    if not os.path.isfile(config_path):
        return None
    try:
        import yaml
        with open(config_path) as f:
            return yaml.safe_load(f)
    except Exception:
        return None


def load_strategy_switchboard(config_path: str, scorecard: Optional[dict] = None) -> list[dict]:
    """Build switchboard data by merging config with scorecard."""
    config = load_strategy_config(config_path)
    if not config:
        return []

    strategies = config.get("strategies", {})
    sc_map: dict[str, dict] = {}
    if scorecard:
        for sc in scorecard.get("strategy_scorecards", []):
            sid = sc.get("strategy_id", "")
            if sid:
                sc_map[sid] = sc

    rows = []
    for strategy_id, cfg in strategies.items():
        sc = sc_map.get(strategy_id, {})
        symbols = cfg.get("symbols", [])
        symbols_display = ", ".join(symbols[:20])
        if len(symbols) > 20:
            symbols_display += f" +{len(symbols) - 20} more"

        rows.append({
            "strategy_id": strategy_id,
            "enabled": cfg.get("enabled", False),
            "strategy_type": cfg.get("strategy_type", ""),
            "mode": cfg.get("mode", ""),
            "data_api": cfg.get("data_api", ""),
            "symbols_count": len(symbols),
            "symbols_display": symbols_display,
            "timeframes": ", ".join(cfg.get("timeframes", [])),
            "feishu_payload": cfg.get("alert", {}).get("feishu_payload", False),
            "auto_send": cfg.get("alert", {}).get("auto_send", False),
            "scorecard_sample_status": sc.get("sample_status", "N/A"),
            "scorecard_strategy_status": sc.get("strategy_status", "N/A"),
            "scorecard_strategy_score": sc.get("strategy_score", "N/A"),
        })

    return rows


def render_strategy_switchboard_table(switchboard: list[dict]) -> str:
    """Render strategy switchboard as read-only HTML table."""
    if not switchboard:
        return "<p>No strategy config found.</p>"

    rows = []
    for s in switchboard:
        enabled = s.get("enabled", False)
        enabled_html = '<span style="color:#44ff44">ON</span>' if enabled else '<span style="color:#666">OFF</span>'
        auto_send = s.get("auto_send", False)
        auto_send_html = '<span style="color:#ff4444">true</span>' if auto_send else "false"
        score = s.get("scorecard_strategy_score", "N/A")
        score_display = f"{score:.2f}" if isinstance(score, (int, float)) else str(score)

        rows.append(
            f"<tr>"
            f"<td>{_escape_html(s.get('strategy_id', ''))}</td>"
            f"<td>{enabled_html}</td>"
            f"<td>{_escape_html(s.get('strategy_type', ''))}</td>"
            f"<td>{_escape_html(s.get('mode', ''))}</td>"
            f"<td>{_escape_html(s.get('data_api', ''))}</td>"
            f"<td>{s.get('symbols_count', 0)}</td>"
            f"<td>{_escape_html(s.get('symbols_display', ''))}</td>"
            f"<td>{_escape_html(s.get('timeframes', ''))}</td>"
            f"<td>{auto_send_html}</td>"
            f"<td>{_escape_html(str(s.get('scorecard_sample_status', 'N/A')))}</td>"
            f"<td>{_escape_html(str(s.get('scorecard_strategy_status', 'N/A')))}</td>"
            f"<td>{score_display}</td>"
            f"</tr>"
        )

    return f"""<table>
<thead><tr>
<th>Strategy</th><th>Enabled</th><th>Type</th><th>Mode</th><th>Data API</th>
<th>Sym#</th><th>Symbols</th><th>Timeframes</th><th>Auto Send</th>
<th>Sample</th><th>Status</th><th>Score</th>
</tr></thead>
<tbody>
{''.join(rows)}
</tbody></table>"""


ALLOWED_TIMEFRAMES = {"1m", "3m", "5m", "15m", "30m", "1h", "2h", "4h", "1d"}
_MAX_SYMBOLS = 100
_MAX_SYMBOL_LEN = 30
_MAX_TIMEFRAMES = 20
_MAX_REASON_LEN = 500


def validate_config_change_request(
    form: dict[str, str],
    switchboard: list[dict],
) -> tuple[dict, list[str]]:
    """Validate config change request form. Returns (cleaned_form, errors)."""
    errors: list[str] = []
    known_ids = {s["strategy_id"] for s in switchboard}

    strategy_id = form.get("strategy_id", "").strip()
    if not strategy_id:
        errors.append("strategy_id is required")
    elif strategy_id not in known_ids:
        errors.append(f"Unknown strategy: {strategy_id}")

    requested_enabled = form.get("requested_enabled", "no_change").strip()
    if requested_enabled not in ("no_change", "true", "false"):
        errors.append(f"Invalid requested_enabled: {requested_enabled}")

    # Symbols
    symbols_raw = form.get("requested_symbols", "").strip()
    requested_symbols: list[str] = []
    if symbols_raw:
        parts = [s.strip().upper() for s in symbols_raw.split(",") if s.strip()]
        for p in parts:
            if len(p) > _MAX_SYMBOL_LEN:
                errors.append(f"Symbol too long: {p}")
            if not re.match(r'^[A-Z0-9_\-/]+$', p):
                errors.append(f"Invalid symbol: {p}")
        if len(parts) > _MAX_SYMBOLS:
            errors.append(f"Too many symbols: {len(parts)} (max {_MAX_SYMBOLS})")
        requested_symbols = parts

    # Timeframes
    timeframes_raw = form.get("requested_timeframes", "").strip()
    requested_timeframes: list[str] = []
    if timeframes_raw:
        parts = [t.strip() for t in timeframes_raw.split(",") if t.strip()]
        for p in parts:
            if p not in ALLOWED_TIMEFRAMES:
                errors.append(f"Invalid timeframe: {p}")
        if len(parts) > _MAX_TIMEFRAMES:
            errors.append(f"Too many timeframes: {len(parts)} (max {_MAX_TIMEFRAMES})")
        requested_timeframes = parts

    reason = form.get("reason", "").strip()
    if not reason:
        errors.append("reason is required")
    elif len(reason) > _MAX_REASON_LEN:
        errors.append(f"reason too long: {len(reason)} (max {_MAX_REASON_LEN})")

    cleaned = {
        "strategy_id": strategy_id,
        "requested_enabled": requested_enabled,
        "requested_symbols": requested_symbols,
        "requested_timeframes": requested_timeframes,
        "reason": reason,
    }
    return cleaned, errors


def create_config_change_request(
    form: dict,
    config_snapshot: dict,
) -> dict:
    """Create a config change request dict."""
    import uuid
    return {
        "request_id": f"CR_{_today_str()}_{uuid.uuid4().hex[:8]}",
        "created_at": _ts(),
        "strategy_id": form["strategy_id"],
        "current_config_snapshot": config_snapshot,
        "requested_enabled": form["requested_enabled"],
        "requested_symbols": form["requested_symbols"],
        "requested_timeframes": form["requested_timeframes"],
        "reason": form["reason"],
        "status": "PENDING_HUMAN_REVIEW",
        "config_written": False,
        "safety_flags": list(SAFETY_FLAGS),
    }


def append_config_change_request(request: dict, report_dir: str) -> tuple[str, str]:
    """Append request to JSONL and write latest markdown. Returns (jsonl_path, md_path)."""
    os.makedirs(report_dir, exist_ok=True)
    date_str = _today_str()

    jsonl_path = os.path.join(report_dir, f"{date_str}_strategy_config_change_requests.jsonl")
    with open(jsonl_path, "a") as f:
        f.write(json.dumps(request, ensure_ascii=False) + "\n")

    md_path = os.path.join(report_dir, f"{date_str}_strategy_config_change_request_latest.md")
    md = _render_config_change_markdown(request)
    with open(md_path, "w") as f:
        f.write(md)

    return jsonl_path, md_path


def _render_config_change_markdown(request: dict) -> str:
    """Render config change request as markdown."""
    snap = request.get("current_config_snapshot", {})
    symbols = request.get("requested_symbols", [])
    timeframes = request.get("requested_timeframes", [])

    lines = [
        "# Strategy Config Change Request",
        "",
        f"**Request ID:** {request.get('request_id', '')}",
        f"**Created:** {request.get('created_at', '')}",
        f"**Status:** {request.get('status', '')}",
        f"**config_written:** {request.get('config_written', False)}",
        "",
        "## Current Config",
        "",
        f"- enabled: {snap.get('enabled', 'N/A')}",
        f"- strategy_type: {snap.get('strategy_type', 'N/A')}",
        f"- mode: {snap.get('mode', 'N/A')}",
        f"- symbols: {', '.join(snap.get('symbols', []))}",
        f"- timeframes: {', '.join(snap.get('timeframes', []))}",
        f"- auto_send: {snap.get('auto_send', 'N/A')}",
        "",
        "## Requested Change",
        "",
        f"- requested_enabled: {request.get('requested_enabled', 'no_change')}",
        f"- requested_symbols: {', '.join(symbols) if symbols else 'no_change'}",
        f"- requested_timeframes: {', '.join(timeframes) if timeframes else 'no_change'}",
        f"- reason: {request.get('reason', '')}",
        "",
        "## Safety",
        "",
        "- config_written: false",
        "- 本文件只是变更草案。",
        "- 尚未修改 config/strategies.yaml。",
        "- 需要人工审核后另行执行。",
        "",
        "## Manual Review Required",
        "",
        "请人工审核以上变更草案后，决定是否手动执行配置变更。",
    ]
    return "\n".join(lines)


def render_config_change_form(switchboard: list[dict]) -> str:
    """Render config change request form as HTML."""
    strategy_options = "".join(
        f'<option value="{_escape_html(s["strategy_id"])}">{_escape_html(s["strategy_id"])}</option>'
        for s in switchboard
    )

    return f"""<div class="read-only-notice">
  Change request 模式。不会直接修改 config/strategies.yaml。提交后只生成审核文件。
</div>
<form id="config-change-form" onsubmit="submitConfigChange(event)">
  <div class="form-group">
    <label for="strategy_id">Strategy</label>
    <select id="strategy_id" name="strategy_id" required>
      {strategy_options}
    </select>
  </div>
  <div class="form-group">
    <label for="requested_enabled">Requested Enabled</label>
    <select id="requested_enabled" name="requested_enabled">
      <option value="no_change">no_change</option>
      <option value="true">true (enable)</option>
      <option value="false">false (disable)</option>
    </select>
  </div>
  <div class="form-group">
    <label for="requested_symbols">Requested Symbols (comma separated, empty=no_change)</label>
    <input type="text" id="requested_symbols" name="requested_symbols" placeholder="BTCUSDT, ETHUSDT">
  </div>
  <div class="form-group">
    <label for="requested_timeframes">Requested Timeframes (comma separated, empty=no_change)</label>
    <input type="text" id="requested_timeframes" name="requested_timeframes" placeholder="15m, 1h">
  </div>
  <div class="form-group">
    <label for="reason">Reason (required)</label>
    <textarea id="reason" name="reason" rows="3" required maxlength="500"></textarea>
  </div>
  <button type="submit" class="btn">Submit Change Request</button>
</form>
<div id="config-change-result" class="result"></div>"""


def render_config_change_result(request: dict) -> str:
    """Render config change request result as HTML."""
    return f"""<div class="result-header pass">Request created: {_escape_html(request.get('request_id', ''))}</div>
<p>Status: {_escape_html(request.get('status', ''))}</p>
<p>config_written: {request.get('config_written', False)}</p>
<p>Strategy: {_escape_html(request.get('strategy_id', ''))}</p>
<p>Requested enabled: {_escape_html(request.get('requested_enabled', ''))}</p>
<p>本文件只是变更草案，尚未修改 config/strategies.yaml。</p>"""


def render_dashboard_html(
    status: dict[str, Any],
    positions: Optional[list[dict]] = None,
    scorecard: Optional[dict] = None,
    sample_gate: Optional[dict] = None,
    recent_actions: Optional[list[dict]] = None,
    strategy_switchboard: Optional[list[dict]] = None,
    config_change_result: Optional[str] = None,
) -> str:
    """Render dashboard HTML."""
    sample = status.get("sample_status", "UNKNOWN")
    gate = status.get("testnet_gate_status", "UNKNOWN")
    clean = status.get("clean_positions", "N/A")
    closed = status.get("closed_clean_positions", "N/A")
    excluded = status.get("excluded_positions", "N/A")
    open_pos = status.get("open_positions", "N/A")
    win_rate = status.get("win_rate", 0.0)
    pf = status.get("profit_factor", 0.0)
    quarantined = status.get("quarantined_count", "N/A")
    lc_status = status.get("lifecycle_status", "N/A")
    lc_date = status.get("lifecycle_date", "")
    uo_status = status.get("update_only_status", "N/A")
    uo_date = status.get("update_only_date", "")

    # Gate reasons
    reasons_html = ""
    reasons = status.get("gate_reasons", [])
    if reasons:
        items = "".join(f"<li>{_escape_html(r)}</li>" for r in reasons)
        reasons_html = f"<p>Gate reasons:</p><ul>{items}</ul>"

    # Data sections
    positions_html = render_positions_table(positions or [])
    sc_data = scorecard or {}
    scorecard_html = render_scorecard_table(
        sc_data.get("strategy_scorecards", []),
        sample_status=sc_data.get("global_metrics", {}).get("sample_status", sample),
    )
    sample_gate_html = render_sample_gate_card(sample_gate or {})
    recent_actions_html = render_recent_actions_table(recent_actions or [])
    switchboard_html = render_strategy_switchboard_table(strategy_switchboard or [])
    config_form_html = render_config_change_form(strategy_switchboard or [])
    config_result_html = config_change_result or ""

    # Next action hint
    next_action = "继续 shadow collection。不要 testnet。不要 live。"
    if gate == "PAPER_SAMPLE_READY_FOR_HUMAN_REVIEW":
        next_action = "样本已达到人工审查门槛。请人工审查策略表现后决定下一步。"

    html = f"""<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="utf-8">
<title>Shadow Trading Console</title>
<style>
  body {{ font-family: -apple-system, sans-serif; max-width: 900px; margin: 40px auto; padding: 0 20px; background: #1a1a2e; color: #e0e0e0; }}
  h1 {{ color: #00d4ff; }}
  h2 {{ color: #00d4ff; border-bottom: 1px solid #333; padding-bottom: 6px; }}
  .status-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin: 16px 0; }}
  .status-item {{ background: #16213e; padding: 12px; border-radius: 6px; border: 1px solid #0f3460; }}
  .status-label {{ color: #888; font-size: 0.85em; }}
  .status-value {{ font-size: 1.3em; font-weight: bold; color: #00d4ff; }}
  .status-value.warn {{ color: #ffa500; }}
  .status-value.blocked {{ color: #ff4444; }}
  .status-value.ok {{ color: #44ff44; }}
  .btn-row {{ display: flex; gap: 10px; flex-wrap: wrap; margin: 16px 0; }}
  .btn {{ background: #0f3460; color: #00d4ff; border: 1px solid #00d4ff; padding: 10px 18px;
          border-radius: 6px; cursor: pointer; font-size: 0.95em; }}
  .btn:hover {{ background: #00d4ff; color: #1a1a2e; }}
  .btn:disabled {{ opacity: 0.5; cursor: not-allowed; }}
  .result {{ background: #16213e; border: 1px solid #0f3460; border-radius: 6px;
             padding: 12px; margin: 10px 0; white-space: pre-wrap; font-family: monospace;
             font-size: 0.85em; max-height: 400px; overflow-y: auto; display: none; }}
  .result.show {{ display: block; }}
  .result-header {{ font-weight: bold; margin-bottom: 8px; }}
  .result-header.pass {{ color: #44ff44; }}
  .result-header.fail {{ color: #ff4444; }}
  .report-list {{ list-style: none; padding: 0; }}
  .report-list li {{ margin: 6px 0; }}
  .report-list a {{ color: #00d4ff; text-decoration: none; }}
  .report-list a:hover {{ text-decoration: underline; }}
  .report-content {{ background: #16213e; border: 1px solid #0f3460; border-radius: 6px;
                     padding: 16px; margin: 10px 0; white-space: pre-wrap; font-family: monospace;
                     font-size: 0.85em; max-height: 600px; overflow-y: auto; display: none; }}
  .report-content.show {{ display: block; }}
  .next-action {{ background: #0f3460; border: 1px solid #ffa500; border-radius: 6px;
                  padding: 12px; margin: 16px 0; color: #ffa500; }}
  .safety {{ color: #888; font-size: 0.8em; margin-top: 20px; border-top: 1px solid #333; padding-top: 10px; }}
  table {{ width: 100%; border-collapse: collapse; margin: 10px 0; font-size: 0.85em; }}
  th, td {{ padding: 6px 8px; text-align: left; border-bottom: 1px solid #0f3460; }}
  th {{ background: #0f3460; color: #00d4ff; position: sticky; top: 0; }}
  tr:hover {{ background: #16213e; }}
  tr.open {{ color: #e0e0e0; }}
  tr.take_profit_hit {{ color: #44ff44; }}
  tr.stop_loss_hit {{ color: #ff4444; }}
  tr.timeout_exit {{ color: #ffa500; }}
  tr.excluded {{ color: #666; }}
  td.ok {{ color: #44ff44; }}
  td.blocked {{ color: #ff4444; }}
  .table-wrap {{ max-height: 400px; overflow-y: auto; margin: 10px 0; }}
  .read-only-notice {{ background: #0f3460; border: 1px solid #00d4ff; border-radius: 6px;
                       padding: 8px 12px; margin: 10px 0; color: #00d4ff; font-size: 0.9em; }}
  .form-group {{ margin: 10px 0; }}
  .form-group label {{ display: block; color: #888; font-size: 0.85em; margin-bottom: 4px; }}
  .form-group input, .form-group select, .form-group textarea {{
    width: 100%; padding: 8px; background: #16213e; color: #e0e0e0;
    border: 1px solid #0f3460; border-radius: 4px; font-size: 0.9em;
    box-sizing: border-box;
  }}
  .form-group textarea {{ resize: vertical; }}
  .form-group input:focus, .form-group select:focus, .form-group textarea:focus {{
    border-color: #00d4ff; outline: none;
  }}
</style>
</head>
<body>
<h1>Shadow Trading Console</h1>

<h2>Status</h2>
<div class="status-grid">
  <div class="status-item">
    <div class="status-label">sample_status</div>
    <div class="status-value {'blocked' if 'INSUFFICIENT' in sample else 'warn' if 'LOW' in sample else 'ok'}">{sample}</div>
  </div>
  <div class="status-item">
    <div class="status-label">testnet_gate_status</div>
    <div class="status-value {'blocked' if 'BLOCKED' in gate else 'ok'}">{gate}</div>
  </div>
  <div class="status-item">
    <div class="status-label">clean_positions</div>
    <div class="status-value">{clean}</div>
  </div>
  <div class="status-item">
    <div class="status-label">closed_clean_positions</div>
    <div class="status-value">{closed}</div>
  </div>
  <div class="status-item">
    <div class="status-label">open_positions</div>
    <div class="status-value">{open_pos}</div>
  </div>
  <div class="status-item">
    <div class="status-label">excluded_positions</div>
    <div class="status-value">{excluded}</div>
  </div>
  <div class="status-item">
    <div class="status-label">lifecycle_status</div>
    <div class="status-value {'ok' if lc_status == 'PASS' else 'blocked'}">{lc_status} {lc_date}</div>
  </div>
  <div class="status-item">
    <div class="status-label">update_only_status</div>
    <div class="status-value {'ok' if uo_status == 'PASS' else 'blocked'}">{uo_status} {uo_date}</div>
  </div>
</div>

{reasons_html}

<div class="next-action">
  <strong>Next action:</strong> {next_action}
</div>

<h2>Actions</h2>
<div class="btn-row">
  <button class="btn" onclick="runAction('run-lifecycle')">扫描新机会 + 更新持仓</button>
  <button class="btn" onclick="runAction('run-update-only')">只更新已有持仓</button>
  <button class="btn" onclick="runAction('run-sample-gate')">刷新样本门禁</button>
  <button class="btn" onclick="runAction('print-status')">打印当前状态</button>
</div>
<div id="action-result" class="result"></div>

<h2>Reports</h2>
<ul class="report-list">
  <li><a href="#" onclick="loadReport('latest_lifecycle'); return false;">Latest Lifecycle Result</a></li>
  <li><a href="#" onclick="loadReport('latest_update'); return false;">Latest Update-Only Result</a></li>
  <li><a href="#" onclick="loadReport('latest_gate'); return false;">Latest Sample Gate</a></li>
  <li><a href="#" onclick="loadReport('latest_scorecard'); return false;">Latest Scorecard</a></li>
</ul>
<div id="report-content" class="report-content"></div>

<h2>Paper Positions</h2>
<div class="table-wrap">
{positions_html}
</div>

<h2>Strategy Scorecard</h2>
<div class="table-wrap">
{scorecard_html}
</div>

<h2>Sample Gate</h2>
{sample_gate_html}

<h2>Recent Actions</h2>
<div class="table-wrap">
{recent_actions_html}
</div>

<h2>Strategy Switchboard</h2>
<div class="read-only-notice">Read-only view. Source: config/strategies.yaml. 网页不会修改策略配置。</div>
<div class="table-wrap">
{switchboard_html}
</div>

<h2>Strategy Config Change Request</h2>
{config_result_html}
{config_form_html}

<div class="safety">
  Paper-only | Shadow-only | Local-only | No order | No testnet | No live | No secret
</div>

<script>
function runAction(action) {{
  var btns = document.querySelectorAll('.btn');
  btns.forEach(function(b) {{ b.disabled = true; }});
  var el = document.getElementById('action-result');
  el.className = 'result show';
  el.innerHTML = '<div class="result-header">Running: ' + action + '...</div>';

  fetch('/action/' + action, {{ method: 'POST' }})
    .then(function(r) {{ return r.json(); }})
    .then(function(data) {{
      var cls = data.status === 'PASS' ? 'pass' : 'fail';
      var html = '<div class="result-header ' + cls + '">' + data.status + ' (' + data.duration_seconds + 's, exit=' + data.exit_code + ')</div>';
      if (data.stdout_tail) html += '<pre>' + escapeHtml(data.stdout_tail) + '</pre>';
      if (data.stderr_tail) html += '<pre style="color:#ff4444">' + escapeHtml(data.stderr_tail) + '</pre>';
      el.innerHTML = html;
      btns.forEach(function(b) {{ b.disabled = false; }});
    }})
    .catch(function(e) {{
      el.innerHTML = '<div class="result-header fail">Error: ' + e.message + '</div>';
      btns.forEach(function(b) {{ b.disabled = false; }});
    }});
}}

function loadReport(which) {{
  var el = document.getElementById('report-content');
  el.className = 'report-content show';
  el.innerHTML = 'Loading...';

  fetch('/report?name=' + which)
    .then(function(r) {{ return r.text(); }})
    .then(function(text) {{
      el.textContent = text;
    }})
    .catch(function(e) {{
      el.innerHTML = 'Error: ' + e.message;
    }});
}}

function escapeHtml(s) {{
  var d = document.createElement('div');
  d.appendChild(document.createTextNode(s));
  return d.innerHTML;
}}

function submitConfigChange(e) {{
  e.preventDefault();
  var form = document.getElementById('config-change-form');
  var data = new FormData(form);
  var params = new URLSearchParams();
  for (var pair of data) {{
    params.append(pair[0], pair[1]);
  }}

  var el = document.getElementById('config-change-result');
  el.className = 'result show';
  el.innerHTML = '<div class="result-header">Submitting...</div>';

  fetch('/action/request-config-change', {{
    method: 'POST',
    headers: {{ 'Content-Type': 'application/x-www-form-urlencoded' }},
    body: params.toString()
  }})
    .then(function(r) {{ return r.text(); }})
    .then(function(text) {{
      el.innerHTML = text;
    }})
    .catch(function(err) {{
      el.innerHTML = '<div class="result-header fail">Error: ' + err.message + '</div>';
    }});
}}
</script>
</body>
</html>"""
    return html
