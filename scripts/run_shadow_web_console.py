"""Shadow Web Console runner — local-only web dashboard for shadow trading.

Starts a local HTTP server on 127.0.0.1 only.
Provides dashboard, action buttons, and report viewer.
No public binding, no orders, no accounts, no secrets.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core.paper_trading.shadow_web_console import (
    load_console_status, render_dashboard_html, run_allowed_action,
    render_report_file, is_safe_report_name, ALLOWED_ACTIONS, SAFETY_FLAGS,
    _find_latest, _today_str, _ts,
    load_latest_positions, load_latest_scorecard,
    load_latest_sample_gate, load_recent_actions,
    load_strategy_switchboard,
)

REPO_ROOT = os.path.join(os.path.dirname(__file__), "..")
REPORT_DIR = os.path.join(REPO_ROOT, "reports", "strategies")
CONFIG_PATH = os.path.join(REPO_ROOT, "config", "strategies.yaml")


class ShadowConsoleHandler(BaseHTTPRequestHandler):
    """HTTP handler for shadow web console."""

    repo_root: str = REPO_ROOT
    report_dir: str = REPORT_DIR
    config_path: str = CONFIG_PATH

    def log_message(self, format, *args):
        """Suppress default HTTP logging."""
        pass

    def _send_html(self, html: str, code: int = 200):
        self.send_response(code)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(html.encode("utf-8"))

    def _send_json(self, data: dict, code: int = 200):
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode("utf-8"))

    def _send_text(self, text: str, code: int = 200):
        self.send_response(code)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.end_headers()
        self.wfile.write(text.encode("utf-8"))

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        query = parse_qs(parsed.query)

        if path == "/":
            status = load_console_status(self.report_dir)
            positions = load_latest_positions(self.report_dir)
            scorecard = load_latest_scorecard(self.report_dir)
            sample_gate = load_latest_sample_gate(self.report_dir)
            recent_actions = load_recent_actions(self.report_dir)
            switchboard = load_strategy_switchboard(self.config_path, scorecard)
            html = render_dashboard_html(
                status,
                positions=positions,
                scorecard=scorecard,
                sample_gate=sample_gate,
                recent_actions=recent_actions,
                strategy_switchboard=switchboard,
            )
            self._send_html(html)
        elif path == "/report":
            name_param = query.get("name", [""])[0]
            # Map logical names to report suffixes
            name_map = {
                "latest_lifecycle": "_shadow_lifecycle_result.md",
                "latest_update": "_shadow_position_update_result.md",
                "latest_gate": "_shadow_sample_gate.md",
                "latest_scorecard": "_paper_performance_scorecard.md",
            }
            if name_param in name_map:
                suffix = name_map[name_param]
                latest = _find_latest(self.report_dir, suffix)
                if latest:
                    name = os.path.basename(latest)
                else:
                    self._send_text("Report not found.", 404)
                    return
            elif name_param:
                name = name_param
            else:
                self._send_text("Missing name parameter.", 400)
                return

            content = render_report_file(self.report_dir, name)
            if content is None:
                self._send_text("Report not found or unsafe path.", 404)
            else:
                self._send_text(content)
        else:
            self._send_text("Not found.", 404)

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path.startswith("/action/"):
            action = path[len("/action/"):]
            result = run_allowed_action(action, self.repo_root, self.report_dir)
            self._send_json(result)
        else:
            self._send_json({"error": "Not found."}, 404)


def main():
    parser = argparse.ArgumentParser(
        description="Shadow Web Console — local-only dashboard",
    )
    parser.add_argument("--host", type=str, default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--report-dir", type=str, default=REPORT_DIR)
    parser.add_argument("--smoke-render", action="store_true",
                        help="Render dashboard HTML and exit without starting server")
    args = parser.parse_args()

    # Enforce local-only binding
    if args.host not in ("127.0.0.1", "localhost"):
        print(f"ERROR: host must be 127.0.0.1 or localhost, got: {args.host}")
        return 1

    report_dir = os.path.abspath(args.report_dir)
    repo_root = os.path.abspath(REPO_ROOT)

    if args.smoke_render:
        status = load_console_status(report_dir)
        positions = load_latest_positions(report_dir)
        scorecard = load_latest_scorecard(report_dir)
        sample_gate = load_latest_sample_gate(report_dir)
        recent_actions = load_recent_actions(report_dir)
        config_path = os.path.join(repo_root, "config", "strategies.yaml")
        switchboard = load_strategy_switchboard(config_path, scorecard)
        html = render_dashboard_html(
            status,
            positions=positions,
            scorecard=scorecard,
            sample_gate=sample_gate,
            recent_actions=recent_actions,
            strategy_switchboard=switchboard,
        )
        print(html[:500])
        print("...")
        print(f"HTML length: {len(html)} chars")
        print("Contains 'Shadow Trading Console':", "Shadow Trading Console" in html)
        print("Contains 'sample_status':", "sample_status" in html)
        print("Contains 'testnet_gate_status':", "testnet_gate_status" in html)
        print("Contains buttons:", "扫描新机会" in html and "只更新已有持仓" in html)
        print("Contains 'Paper Positions':", "Paper Positions" in html)
        print("Contains 'Strategy Scorecard':", "Strategy Scorecard" in html)
        print("Contains 'Sample Gate':", "Sample Gate" in html)
        print("Contains 'Recent Actions':", "Recent Actions" in html)
        print("Contains 'Strategy Switchboard':", "Strategy Switchboard" in html)
        print("Contains 'read-only':", "read-only" in html.lower() or "Read-only" in html)
        return 0

    # Update handler class attributes
    ShadowConsoleHandler.repo_root = repo_root
    ShadowConsoleHandler.report_dir = report_dir

    print(f"Shadow Web Console")
    print(f"Host: {args.host}")
    print(f"Port: {args.port}")
    print(f"Reports: {report_dir}")
    print(f"URL: http://{args.host}:{args.port}")
    print()
    print("Press Ctrl+C to stop.")
    print()

    server = HTTPServer((args.host, args.port), ShadowConsoleHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down.")
        server.shutdown()
    return 0


if __name__ == "__main__":
    sys.exit(main())
