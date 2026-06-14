"""Scheduled run plan — generates cron/systemd templates (does not install)."""
from __future__ import annotations
from src.paper_trading_ops.models import ScheduledRunPlan, new_id, utc_now_iso

TASKS = (
    {"interval": "*/5 * * * *", "description": "Scanner runs independently (macd-rebound-scanner service)"},
    {"interval": "*/15 * * * *", "description": "Log source check + signal dedup + trade plan batch + position store update",
     "scripts": "run_paper_trading_log_source_check, run_paper_trading_signal_dedup, run_paper_trade_plan_batch, run_paper_position_store_update"},
    {"interval": "*/30 * * * *", "description": "Paper position replay update",
     "scripts": "run_paper_position_replay_update"},
    {"interval": "55 23 * * *", "description": "Daily review bundle + strategy quality + dashboard + alert payload",
     "scripts": "run_daily_paper_trading_review, run_strategy_quality_metrics, run_signal_quality_dashboard, run_daily_paper_ops_bundle, run_paper_ops_alert_payload_dry_run"},
)

CRON_TEMPLATE = """# Paper Trading Ops Cron (example — do not install automatically)
# Adjust paths to your environment
# QQ_ROOT=/Users/winnie/Documents/trae_projects/qq

# Every 15 minutes: signal pipeline
*/15 * * * * cd $QQ_ROOT && PYTHONPATH=. python3 scripts/run_paper_trading_log_source_check.py >> logs/paper_ops.log 2>&1
*/15 * * * * cd $QQ_ROOT && PYTHONPATH=. python3 scripts/run_paper_trading_signal_dedup.py >> logs/paper_ops.log 2>&1
*/15 * * * * cd $QQ_ROOT && PYTHONPATH=. python3 scripts/run_paper_trade_plan_batch.py >> logs/paper_ops.log 2>&1
*/15 * * * * cd $QQ_ROOT && PYTHONPATH=. python3 scripts/run_paper_position_store_update.py >> logs/paper_ops.log 2>&1

# Every 30 minutes: position replay
*/30 * * * * cd $QQ_ROOT && PYTHONPATH=. python3 scripts/run_paper_position_replay_update.py >> logs/paper_ops.log 2>&1

# Daily 23:55: review bundle
55 23 * * * cd $QQ_ROOT && PYTHONPATH=. python3 scripts/run_daily_paper_trading_review.py >> logs/paper_ops.log 2>&1
55 23 * * * cd $QQ_ROOT && PYTHONPATH=. python3 scripts/run_strategy_quality_metrics.py >> logs/paper_ops.log 2>&1
55 23 * * * cd $QQ_ROOT && PYTHONPATH=. python3 scripts/run_signal_quality_dashboard.py >> logs/paper_ops.log 2>&1
55 23 * * * cd $QQ_ROOT && PYTHONPATH=. python3 scripts/run_daily_paper_ops_bundle.py >> logs/paper_ops.log 2>&1
55 23 * * * cd $QQ_ROOT && PYTHONPATH=. python3 scripts/run_paper_ops_alert_payload_dry_run.py >> logs/paper_ops.log 2>&1
"""

SYSTEMD_SERVICE = """[Unit]
Description=Paper Trading Ops Daily Review
After=network.target

[Service]
Type=oneshot
User=www
WorkingDirectory=/www/wwwroot/qq
Environment=PYTHONPATH=/www/wwwroot/qq
ExecStart=/usr/bin/python3 scripts/run_daily_paper_ops_bundle.py
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
"""

SYSTEMD_TIMER = """[Unit]
Description=Run paper trading ops daily review at 23:55

[Timer]
OnCalendar=*-*-* 23:55:00
Persistent=true

[Install]
WantedBy=timers.target
"""

SYSTEMD_COMBINED = f"{SYSTEMD_SERVICE.strip()}\n\n---\n\n{SYSTEMD_TIMER.strip()}"


def create_scheduled_plan() -> ScheduledRunPlan:
    return ScheduledRunPlan(
        plan_id=new_id("SRP"), created_at=utc_now_iso(),
        tasks=TASKS,
        cron_template=CRON_TEMPLATE.strip(),
        systemd_template=SYSTEMD_COMBINED,
        final_verdict="PAPER_OPS_SCHEDULED_RUN_PLAN_READY|TEMPLATES_ONLY|NOT_INSTALLED|REAL_ORDER_SUBMIT_NOT_ALLOWED",
    )
