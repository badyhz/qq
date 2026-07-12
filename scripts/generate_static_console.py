"""Generate static read-only shadow console for public access.

Reads reports/strategies, generates HTML + JSON for Nginx.
No orders, no accounts, no secrets, no external network, no control buttons.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import tempfile
from datetime import datetime, timezone
from typing import Any

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core.paper_trading.shadow_web_console import (
    load_console_status,
    load_latest_positions,
    load_latest_scorecard,
    load_latest_sample_gate,
    render_dashboard_html,
)

REPO_ROOT = os.path.join(os.path.dirname(__file__), "..")
REPORT_DIR = os.path.join(REPO_ROOT, "reports", "strategies")
DEFAULT_OUTPUT_DIR = "/www/wwwroot/quant-shadow-console"

SENSITIVE_PATTERNS = [
    r"/opt/quant-shadow",
    r"/www/wwwroot",
    r"10\.66\.66\.\d+",
    r"43\.156\.54\.\d+",
    r"\bSSH\b",
    r"API_KEY",
    r"SECRET_KEY",
    r"SECRET_TOKEN",
    r"TOKEN",
    r"PASSWORD",
    r"Webhook",
    r"wireguard",
    r"\.env",
]


def strip_control_elements(html: str) -> str:
    """Remove action buttons, forms, and JS from HTML for public view."""
    # Remove action buttons section
    html = re.sub(
        r'<div class="next-action">.*?</div>\s*</div>',
        _keep_advice_only,
        html,
        flags=re.DOTALL,
    )
    # Remove config change form
    html = re.sub(r'<form[^>]*>.*?</form>', '', html, flags=re.DOTALL)
    # Remove action result div
    html = re.sub(r'<div id="action-result"[^>]*>.*?</div>', '', html, flags=re.DOTALL)
    # Remove runAction function
    html = re.sub(r'function runAction.*?}\s*}', '', html, flags=re.DOTALL)
    # Remove fetch calls
    html = re.sub(r'fetch\([^)]+\).*?;', '', html, flags=re.DOTALL)
    return html


def _keep_advice_only(match: re.Match) -> str:
    """Keep only the advice text, remove buttons."""
    text = match.group(0)
    advice_match = re.search(
        r'<strong>.*?action.*?</strong>\s*(.*?)\s*<button', text, re.DOTALL | re.IGNORECASE
    )
    if advice_match:
        advice = advice_match.group(1).strip()
        return f'<div class="next-action"><strong>Next action:</strong> {advice}</div>'
    return '<div class="next-action">Status available</div>'


def add_viewport(html: str) -> str:
    """Add viewport meta tag for mobile if missing."""
    if "<head>" in html and "viewport" not in html:
        html = html.replace(
            "<head>",
            '<head>\n  <meta name="viewport" content="width=device-width, initial-scale=1.0">',
        )
    return html


def check_sensitive_leaks(html: str) -> list[str]:
    """Check for sensitive data leaks in HTML."""
    found = []
    for pattern in SENSITIVE_PATTERNS:
        if re.search(pattern, html, re.IGNORECASE):
            found.append(pattern)
    return found


def build_public_json(
    status: dict,
    positions: list[dict],
    scorecard: dict,
    sample_gate: dict,
) -> dict[str, Any]:
    """Build public-safe JSON data."""
    # Strategy metrics
    strategies = {}
    for sc in scorecard.get("strategy_scorecards", []):
        strategies[sc["strategy_id"]] = {
            "strategy_id": sc.get("strategy_id"),
            "closed_count": sc.get("closed_count"),
            "win_rate": round(sc.get("win_rate", 0) * 100, 1),
            "profit_factor": round(sc.get("profit_factor", 0), 2),
            "expectancy_r": round(sc.get("expectancy_r", 0), 4),
            "avg_r": round(sc.get("avg_r_multiple", 0), 4),
            "cumulative_r": round(sc.get("avg_r_multiple", 0) * sc.get("closed_count", 0), 2),
            "max_drawdown_r": round(sc.get("max_drawdown_r", 0), 4),
            "max_losing_streak": sc.get("max_losing_streak", 0),
        }

    # Current positions (open only, limited fields)
    current_positions = []
    for p in positions:
        if p.get("status") != "OPEN":
            continue
        current_positions.append({
            "symbol": p.get("symbol"),
            "timeframe": p.get("timeframe"),
            "side": p.get("side"),
            "entry_price": p.get("entry_price"),
            "stop_loss": p.get("stop_loss"),
            "take_profit": p.get("take_profit"),
            "opened_at": p.get("opened_at"),
            "strategy_id": p.get("strategy_id"),
        })

    # Recent closed (last 20)
    closed = sorted(
        [p for p in positions if p.get("status") != "OPEN"],
        key=lambda p: p.get("closed_at", ""),
        reverse=True,
    )[:20]
    recent_closed = []
    for p in closed:
        recent_closed.append({
            "symbol": p.get("symbol"),
            "strategy_id": p.get("strategy_id"),
            "timeframe": p.get("timeframe"),
            "side": p.get("side"),
            "exit_reason": p.get("exit_reason"),
            "r_multiple": round(p.get("r_multiple", 0), 4),
            "closed_at": p.get("closed_at"),
        })

    # Freshness
    lc_date = status.get("lifecycle_date", "")
    data_age_minutes = None
    freshness_status = "unknown"
    if lc_date:
        try:
            lc_dt = datetime.fromisoformat(lc_date.replace("Z", "+00:00"))
            now = datetime.now(timezone.utc)
            age = (now - lc_dt).total_seconds() / 60
            data_age_minutes = round(age, 1)
            if age <= 90:
                freshness_status = "fresh"
            elif age <= 180:
                freshness_status = "stale"
            else:
                freshness_status = "expired"
        except (ValueError, TypeError):
            freshness_status = "unknown"

    global_metrics = scorecard.get("global_metrics", {})

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "latest_run_at": lc_date,
        "freshness_status": freshness_status,
        "data_age_minutes": data_age_minutes,
        "sample_status": status.get("sample_status", "UNKNOWN"),
        "gate_status": status.get("testnet_gate_status", "UNKNOWN"),
        "eligible_closed_clean": status.get("closed_clean_positions", 0),
        "open_positions": status.get("open_positions", 0),
        "take_profit_count": global_metrics.get("take_profit_hit", 0),
        "stop_loss_count": global_metrics.get("stop_loss_hit", 0),
        "timeout_count": global_metrics.get("timeout_exit", 0),
        "fee_adjusted": False,
        "slippage_adjusted": False,
        "testnet_enabled": False,
        "live_enabled": False,
        "strategies": strategies,
        "recent_closed": recent_closed,
        "current_positions": current_positions,
    }


def generate_console(
    report_dir: str,
    output_dir: str,
) -> dict[str, Any]:
    """Generate static console files. Returns result dict."""
    result = {
        "success": False,
        "files_written": [],
        "errors": [],
    }

    # Load data
    status = load_console_status(report_dir)
    positions = load_latest_positions(report_dir)
    scorecard = load_latest_scorecard(report_dir)
    sample_gate = load_latest_sample_gate(report_dir)

    # Generate content in memory
    html_zh = render_dashboard_html(
        status, positions=positions, scorecard=scorecard,
        sample_gate=sample_gate, lang="zh",
    )
    html_en = render_dashboard_html(
        status, positions=positions, scorecard=scorecard,
        sample_gate=sample_gate, lang="en",
    )

    # Strip control buttons
    html_zh = strip_control_elements(html_zh)
    html_en = strip_control_elements(html_en)

    # Add viewport
    html_zh = add_viewport(html_zh)
    html_en = add_viewport(html_en)

    # Check for sensitive leaks
    for label, html in [("zh", html_zh), ("en", html_en)]:
        leaks = check_sensitive_leaks(html)
        if leaks:
            result["errors"].append(f"Sensitive data in {label}: {leaks}")
            return result

    # Build JSON
    public_json = build_public_json(status, positions, scorecard, sample_gate)
    json_str = json.dumps(public_json, ensure_ascii=False, indent=2)

    # Validate JSON roundtrip
    try:
        json.loads(json_str)
    except json.JSONDecodeError as e:
        result["errors"].append(f"JSON validation failed: {e}")
        return result

    # Prepare file specs
    files = {
        "index.html": html_zh,
        "index_en.html": html_en,
        "console_data.json": json_str,
    }

    # Atomic write: write to temp files first, then replace
    os.makedirs(output_dir, exist_ok=True)
    temp_paths = {}

    try:
        for filename, content in files.items():
            target = os.path.join(output_dir, filename)
            fd, tmp_path = tempfile.mkstemp(dir=output_dir, suffix=".tmp")
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as f:
                    f.write(content)
                    f.flush()
                    os.fsync(f.fileno())
                temp_paths[filename] = (tmp_path, target)
            except Exception as e:
                # Clean up this temp file
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass
                result["errors"].append(f"Failed to write temp {filename}: {e}")
                return result

        # All temp files written successfully — atomic replace
        for filename, (tmp_path, target) in temp_paths.items():
            os.replace(tmp_path, target)
            result["files_written"].append(filename)

        result["success"] = True

    except Exception as e:
        # Clean up any remaining temp files
        for filename, (tmp_path, _) in temp_paths.items():
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
        result["errors"].append(f"Atomic write failed: {e}")

    return result


def main():
    parser = argparse.ArgumentParser(description="Generate static shadow console")
    parser.add_argument("--report-dir", default=REPORT_DIR)
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args()

    result = generate_console(args.report_dir, args.output_dir)

    if result["success"]:
        print(f"Console generated: {', '.join(result['files_written'])}")
        return 0
    else:
        print(f"Console generation FAILED:")
        for err in result["errors"]:
            print(f"  - {err}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
