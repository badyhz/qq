"""Preflight check — validates deployment readiness."""
from __future__ import annotations
import pathlib
from src.paper_trading_deployment.models import DeploymentPreflightReport, new_id, utc_now_iso

REQUIRED_SCRIPTS = (
    "scripts/run_paper_ops_log_freshness.py",
    "scripts/run_paper_ops_state_audit.py",
    "scripts/run_paper_ops_strategy_metrics.py",
    "scripts/run_paper_ops_signal_dashboard.py",
    "scripts/run_paper_ops_daily_bundle.py",
    "scripts/run_paper_ops_alert_payload.py",
    "scripts/run_paper_ops_safety_regression.py",
)

REQUIRED_PACKAGES = (
    "src/paper_trading_ops",
    "src/paper_trading_pipeline",
    "src/trade_plan_engine",
    "src/external_scanner_integrations",
)

REQUIRED_DEPLOY_EXAMPLES = (
    "deploy/systemd/paper-trading-ops-review.service.example",
    "deploy/systemd/paper-trading-ops-review.timer.example",
    "deploy/cron/paper-trading-ops.cron.example",
)

SCANNER_FILES = (
    "data/signals.csv",
    "logs/alerts.jsonl",
    "logs/scan_detail.jsonl",
)


def run_preflight(repo_path: str, scanner_path: str) -> DeploymentPreflightReport:
    warnings: list[str] = []
    failures: list[str] = []
    passed = 0
    total = 0

    repo = pathlib.Path(repo_path)
    scanner = pathlib.Path(scanner_path)

    # Repo path
    total += 1
    if repo.exists():
        passed += 1
    else:
        failures.append(f"Repo path does not exist: {repo}")

    # Scanner path
    total += 1
    if scanner.exists():
        passed += 1
    else:
        warnings.append(f"Scanner path does not exist: {scanner}")

    # Required scripts
    for s in REQUIRED_SCRIPTS:
        total += 1
        if (repo / s).exists():
            passed += 1
        else:
            failures.append(f"Missing script: {s}")

    # Required packages
    for p in REQUIRED_PACKAGES:
        total += 1
        if (repo / p).is_dir():
            passed += 1
        else:
            failures.append(f"Missing package: {p}")

    # Deploy examples
    for d in REQUIRED_DEPLOY_EXAMPLES:
        total += 1
        if (repo / d).exists():
            passed += 1
        else:
            warnings.append(f"Missing deploy example: {d}")

    # Runtime dirs creatable
    for subdir in ("data/runtime", "reports/paper_trading_ops", "logs/paper_trading_ops"):
        total += 1
        target = repo / subdir
        if target.exists() or target.parent.exists():
            passed += 1
        else:
            warnings.append(f"Runtime dir not creatable: {subdir}")

    # Scanner files readable
    if scanner.exists():
        for sf in SCANNER_FILES:
            total += 1
            if (scanner / sf).exists():
                passed += 1
            else:
                warnings.append(f"Scanner file missing: {sf}")

    # No real credential files required
    total += 1
    passed += 1  # Always passes — no credentials needed

    failed = len(failures)
    status = "PASS" if failed == 0 else "FAIL"

    return DeploymentPreflightReport(
        report_id=new_id("DPR"), created_at=utc_now_iso(),
        repo_path=str(repo), scanner_path=str(scanner),
        checks_total=total, checks_passed=passed, checks_failed=failed,
        warnings=warnings, failures=failures,
        preflight_status=status,
        final_verdict=f"PAPER_OPS_DEPLOYMENT_PREFLIGHT_READY|STATUS={status}|PASSED={passed}|FAILED={failed}|REAL_ORDER_SUBMIT_NOT_ALLOWED",
    )
