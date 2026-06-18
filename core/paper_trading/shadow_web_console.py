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


def render_dashboard_html(status: dict[str, Any]) -> str:
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
        items = "".join(f"<li>{r}</li>" for r in reasons)
        reasons_html = f"<p>Gate reasons:</p><ul>{items}</ul>"

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
</script>
</body>
</html>"""
    return html
