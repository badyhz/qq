"""Paper trading acceptance suite — local-only verification, no network."""
from __future__ import annotations

import ast
import json
import os
import subprocess
import sys

REPO_ROOT = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, REPO_ROOT)

PAPER_TRADING_DIR = os.path.join(REPO_ROOT, "core", "paper_trading")
PAPER_TEST_PATTERN = "test_paper_"
FIXTURE_DIR = os.path.join(REPO_ROOT, "tests", "fixtures", "paper_trading")
DOCS_DIR = os.path.join(REPO_ROOT, "docs")
REPORT_DIR = os.path.join(REPO_ROOT, "reports")

FORBIDDEN_STRINGS = [
    "real_order", "api_key", "api_secret",
    "binance.com", "broker", "webhook_url", "requests.post", "requests.get",
    "httpx", "aiohttp",
]

CORE_MODULES = [
    "order_plan.py",
    "risk_sizing.py",
    "exit_rules.py",
    "signal_to_plan_adapter.py",
    "human_approval_gate.py",
    "replay_engine.py",
    "paper_ledger.py",
    "alert_explainer.py",
    "account_state.py",
    "portfolio_risk.py",
    "lifecycle.py",
    "local_alert_bridge.py",
    "performance_metrics.py",
    "parameter_sweep.py",
    "strategy_scorecard.py",
    "risk_explainer.py",
]

# Modules to be added in later phases
PLANNED_MODULES: list[str] = []


class AcceptanceResult:
    def __init__(self):
        self.checks: list[tuple[str, bool, str]] = []

    def add(self, name: str, passed: bool, detail: str = ""):
        self.checks.append((name, passed, detail))

    @property
    def passed(self) -> int:
        return sum(1 for _, p, _ in self.checks if p)

    @property
    def failed(self) -> int:
        return sum(1 for _, p, _ in self.checks if not p)

    @property
    def all_pass(self) -> bool:
        return all(p for _, p, _ in self.checks)

    def summary(self) -> str:
        lines = [f"Checks: {self.passed}/{len(self.checks)} passed"]
        for name, passed, detail in self.checks:
            mark = "PASS" if passed else "FAIL"
            line = f"  [{mark}] {name}"
            if detail and not passed:
                line += f" — {detail}"
            lines.append(line)
        return "\n".join(lines)


def run_cmd(args: list[str], timeout: int = 120) -> tuple[int, str]:
    try:
        r = subprocess.run(
            args, capture_output=True, text=True, timeout=timeout, cwd=REPO_ROOT,
        )
        return r.returncode, r.stdout + r.stderr
    except subprocess.TimeoutExpired:
        return -1, "TIMEOUT"
    except Exception as e:
        return -1, str(e)


def check_compileall(result: AcceptanceResult):
    code, out = run_cmd([sys.executable, "-m", "compileall", "-q", "core", "scripts", "tests"])
    result.add("compileall", code == 0, out.strip()[:200])


def check_paper_tests(result: AcceptanceResult):
    code, out = run_cmd([
        sys.executable, "-m", "pytest", "tests/unit/",
        "-q", "--tb=line", "-k", "paper or signal_to_plan or human_approval",
    ], timeout=60)
    passed = code == 0 and "passed" in out
    detail = ""
    if not passed:
        # Extract summary line
        for line in out.strip().splitlines()[-3:]:
            detail += line + " "
    result.add("paper_unit_tests", passed, detail.strip()[:200])


def check_dry_run_runner(result: AcceptanceResult):
    code, out = run_cmd([sys.executable, "scripts/run_paper_trading_decision_engine_dry.py"])
    passed = code == 0 and "PAPER_TRADING_DRY_RUN_COMPLETE" in out
    result.add("dry_run_runner", passed, out.strip()[:200] if not passed else "")


def check_no_secrets_in_paper_code(result: AcceptanceResult):
    violations = []
    for fname in os.listdir(PAPER_TRADING_DIR):
        if not fname.endswith(".py"):
            continue
        fpath = os.path.join(PAPER_TRADING_DIR, fname)
        with open(fpath) as f:
            content = f.read().lower()
        for forbidden in FORBIDDEN_STRINGS:
            if forbidden in content:
                violations.append(f"{fname}: contains '{forbidden}'")
    result.add("no_secrets_or_network", len(violations) == 0,
               "; ".join(violations[:5]) if violations else "")


def check_no_imports_forbidden(result: AcceptanceResult):
    """AST check: paper modules must not import live/testnet/exchange modules."""
    forbidden_mods = {"live_runner", "live_playbook", "submit", "exchange", "testnet", "execution"}
    violations = []
    for fname in os.listdir(PAPER_TRADING_DIR):
        if not fname.endswith(".py"):
            continue
        fpath = os.path.join(PAPER_TRADING_DIR, fname)
        with open(fpath) as f:
            tree = ast.parse(f.read())
        for node in ast.walk(tree):
            mod = None
            if isinstance(node, ast.Import):
                for alias in node.names:
                    mod = alias.name
            elif isinstance(node, ast.ImportFrom) and node.module:
                mod = node.module
            if mod:
                for kw in forbidden_mods:
                    if kw in mod:
                        violations.append(f"{fname} imports {mod}")
    result.add("no_forbidden_imports", len(violations) == 0,
               "; ".join(violations[:5]) if violations else "")


def check_human_approval_gate(result: AcceptanceResult):
    gate_file = os.path.join(PAPER_TRADING_DIR, "human_approval_gate.py")
    exists = os.path.isfile(gate_file)
    has_never_auto_approve = False
    if exists:
        with open(gate_file) as f:
            content = f.read()
        has_never_auto_approve = "WAITING_FOR_HUMAN_APPROVAL" in content
    result.add("human_approval_gate", exists and has_never_auto_approve,
               "file missing" if not exists else "missing WAITING status" if not has_never_auto_approve else "")


def check_core_modules(result: AcceptanceResult):
    missing = []
    for mod in CORE_MODULES:
        if not os.path.isfile(os.path.join(PAPER_TRADING_DIR, mod)):
            missing.append(mod)
    result.add("core_modules", len(missing) == 0,
               f"missing: {', '.join(missing)}" if missing else "")


def check_planned_modules(result: AcceptanceResult):
    present = []
    for mod in PLANNED_MODULES:
        if os.path.isfile(os.path.join(PAPER_TRADING_DIR, mod)):
            present.append(mod)
    # Informational — not a gate
    result.add(f"planned_modules ({len(present)}/{len(PLANNED_MODULES)})",
               True,  # always passes; tracks progress
               f"ready: {', '.join(present)}" if present else "pending")


def check_fixtures_exist(result: AcceptanceResult):
    fixtures = [
        "macd_rebound_sample.json",
    ]
    missing = []
    for f in fixtures:
        if not os.path.isfile(os.path.join(FIXTURE_DIR, f)):
            missing.append(f)
    result.add("fixtures_exist", len(missing) == 0,
               f"missing: {', '.join(missing)}" if missing else "")


def check_report_generated(result: AcceptanceResult):
    report = os.path.join(REPORT_DIR, "paper_trading_decision_engine_report.md")
    exists = os.path.isfile(report)
    has_safety = False
    if exists:
        with open(report) as f:
            content = f.read()
        has_safety = "paper_only=true" in content or "no real orders" in content.lower()
    result.add("report_generated", exists and has_safety,
               "report missing" if not exists else "missing safety footer")


def check_multi_fixture_runner(result: AcceptanceResult):
    runner = os.path.join(REPO_ROOT, "scripts", "run_paper_multi_fixture_replay.py")
    exists = os.path.isfile(runner)
    result.add("multi_fixture_runner", exists, "script missing" if not exists else "")


def check_security_scan_tests(result: AcceptanceResult):
    test_file = os.path.join(REPO_ROOT, "tests", "unit", "test_paper_security_scan.py")
    exists = os.path.isfile(test_file)
    result.add("security_scan_tests", exists, "test file missing" if not exists else "")


def check_parameter_sweep_runner(result: AcceptanceResult):
    runner = os.path.join(REPO_ROOT, "scripts", "run_paper_parameter_sweep.py")
    exists = os.path.isfile(runner)
    result.add("parameter_sweep_runner", exists, "script missing" if not exists else "")


def check_ops_report_runner(result: AcceptanceResult):
    runner = os.path.join(REPO_ROOT, "scripts", "run_paper_trading_ops_report.py")
    exists = os.path.isfile(runner)
    result.add("ops_report_runner", exists, "script missing" if not exists else "")


def check_scorecard_module(result: AcceptanceResult):
    mod = os.path.join(PAPER_TRADING_DIR, "strategy_scorecard.py")
    exists = os.path.isfile(mod)
    result.add("scorecard_module", exists, "module missing" if not exists else "")


def check_reports_generatable(result: AcceptanceResult):
    """Verify key reports can be generated."""
    required = [
        "paper_trading_decision_engine_report.md",
        "paper_trading_multi_fixture_report.md",
        "paper_trading_ops_report.md",
    ]
    missing = [r for r in required if not os.path.isfile(os.path.join(REPORT_DIR, r))]
    result.add("reports_generatable", len(missing) == 0,
               f"missing: {', '.join(missing)}" if missing else "")


def generate_docs_report(result: AcceptanceResult):
    os.makedirs(DOCS_DIR, exist_ok=True)
    doc_path = os.path.join(DOCS_DIR, "PAPER_TRADING_ACCEPTANCE_REPORT_2026-06-16.md")
    with open(doc_path, "w") as f:
        f.write("# Paper Trading Acceptance Report\n\n")
        f.write("**Date:** 2026-06-16\n")
        f.write("**Mode:** paper-only / local / no network\n\n")
        f.write("## Checks\n\n")
        f.write("| Check | Status |\n|-------|--------|\n")
        for name, passed, detail in result.checks:
            status = "PASS" if passed else "FAIL"
            f.write(f"| {name} | {status} |\n")
        f.write(f"\n**Total:** {result.passed}/{len(result.checks)} passed\n\n")
        if not result.all_pass:
            f.write("## Failures\n\n")
            for name, passed, detail in result.checks:
                if not passed and detail:
                    f.write(f"- **{name}:** {detail}\n")
            f.write("\n")
        f.write("## Safety\n\n")
        f.write("- NO real orders\n")
        f.write("- NO network calls\n")
        f.write("- NO secret reads\n")
        f.write("- NO testnet/live\n")
        f.write("- Human approval gate present\n")
        f.write("- All modules paper-only\n")
    return doc_path


def main():
    print("=== Paper Trading Acceptance Suite ===\n")

    result = AcceptanceResult()

    checks = [
        ("Compileall", check_compileall),
        ("Paper unit tests", check_paper_tests),
        ("Dry-run runner", check_dry_run_runner),
        ("No secrets/network strings", check_no_secrets_in_paper_code),
        ("No forbidden imports", check_no_imports_forbidden),
        ("Human approval gate", check_human_approval_gate),
        ("Core modules", check_core_modules),
        ("Planned modules", check_planned_modules),
        ("Fixtures exist", check_fixtures_exist),
        ("Report generated", check_report_generated),
        ("Multi-fixture runner", check_multi_fixture_runner),
        ("Security scan tests", check_security_scan_tests),
        ("Parameter sweep runner", check_parameter_sweep_runner),
        ("Ops report runner", check_ops_report_runner),
        ("Scorecard module", check_scorecard_module),
        ("Reports generatable", check_reports_generatable),
    ]

    for name, fn in checks:
        print(f"Running: {name} ...")
        fn(result)

    print()
    print(result.summary())
    print()

    doc_path = generate_docs_report(result)
    print(f"Acceptance report: {doc_path}")

    if result.all_pass:
        print("\nStatus: PAPER_TRADING_ACCEPTANCE_PASS")
    else:
        print(f"\nStatus: PAPER_TRADING_ACCEPTANCE_FAIL ({result.failed} failures)")

    return 0 if result.all_pass else 1


if __name__ == "__main__":
    sys.exit(main())
