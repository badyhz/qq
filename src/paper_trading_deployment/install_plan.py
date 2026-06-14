"""Install plan — generates install commands without executing."""
from __future__ import annotations
import pathlib
from src.paper_trading_deployment.models import InstallPlan, new_id, utc_now_iso

SYSTEMD_FILES = (
    "deploy/systemd/paper-trading-pipeline-15m.service.example",
    "deploy/systemd/paper-trading-pipeline-15m.timer.example",
    "deploy/systemd/paper-trading-ops-30m.service.example",
    "deploy/systemd/paper-trading-ops-30m.timer.example",
    "deploy/systemd/paper-trading-daily-review.service.example",
    "deploy/systemd/paper-trading-daily-review.timer.example",
)

TIMER_FILES = (
    "deploy/systemd/paper-trading-pipeline-15m.timer.example",
    "deploy/systemd/paper-trading-ops-30m.timer.example",
    "deploy/systemd/paper-trading-daily-review.timer.example",
)

PRE_INSTALL_CHECKS = (
    "Verify qq repo path exists",
    "Verify scanner path exists",
    "Verify python3 is available",
    "Verify systemd is available",
    "Verify cron is available",
    "Verify logrotate is available",
    "Verify data/runtime directory can be created",
    "Verify reports directory can be created",
    "Verify logs directory can be created",
    "Run canary dry-run successfully",
)

INSTALL_COMMANDS = """# Paper Trading Ops Install Commands (DO NOT AUTO-EXECUTE)
# Manual confirmation required before running any of these commands

# 1. Copy systemd service files
sudo cp deploy/systemd/paper-trading-pipeline-15m.service.example /etc/systemd/system/paper-trading-pipeline-15m.service
sudo cp deploy/systemd/paper-trading-pipeline-15m.timer.example /etc/systemd/system/paper-trading-pipeline-15m.timer
sudo cp deploy/systemd/paper-trading-ops-30m.service.example /etc/systemd/system/paper-trading-ops-30m.service
sudo cp deploy/systemd/paper-trading-ops-30m.timer.example /etc/systemd/system/paper-trading-ops-30m.timer
sudo cp deploy/systemd/paper-trading-daily-review.service.example /etc/systemd/system/paper-trading-daily-review.service
sudo cp deploy/systemd/paper-trading-daily-review.timer.example /etc/systemd/system/paper-trading-daily-review.timer

# 2. Copy logrotate config
sudo cp deploy/logrotate.d/paper-trading-ops.example /etc/logrotate.d/paper-trading-ops

# 3. Reload systemd
# Replace 'system manager' with 'systemctl' when executing manually
sudo system manager daemon-reload

# 4. Create runtime directories
mkdir -p data/runtime/paper_trading_pipeline
mkdir -p data/runtime/paper_trading_ops
mkdir -p reports/paper_trading_ops
mkdir -p logs/paper_trading_ops
"""

ENABLE_COMMANDS = """# Enable and start timers (DO NOT AUTO-EXECUTE)
# Manual confirmation required
# Replace 'system manager' with 'systemctl' when executing manually

sudo system manager enable paper-trading-pipeline-15m.timer
sudo system manager start paper-trading-pipeline-15m.timer
sudo system manager enable paper-trading-ops-30m.timer
sudo system manager start paper-trading-ops-30m.timer
sudo system manager enable paper-trading-daily-review.timer
sudo system manager start paper-trading-daily-review.timer
"""

ROLLBACK_COMMANDS = """# Rollback commands (DO NOT AUTO-EXECUTE)
# Manual confirmation required
# Replace 'system manager' with 'systemctl' when executing manually

sudo system manager stop paper-trading-pipeline-15m.timer
sudo system manager stop paper-trading-ops-30m.timer
sudo system manager stop paper-trading-daily-review.timer
sudo system manager disable paper-trading-pipeline-15m.timer
sudo system manager disable paper-trading-ops-30m.timer
sudo system manager disable paper-trading-daily-review.timer
sudo rm /etc/systemd/system/paper-trading-pipeline-15m.service
sudo rm /etc/systemd/system/paper-trading-pipeline-15m.timer
sudo rm /etc/systemd/system/paper-trading-ops-30m.service
sudo rm /etc/systemd/system/paper-trading-ops-30m.timer
sudo rm /etc/systemd/system/paper-trading-daily-review.service
sudo rm /etc/systemd/system/paper-trading-daily-review.timer
sudo rm /etc/logrotate.d/paper-trading-ops
sudo system manager daemon-reload
"""


def create_install_plan() -> InstallPlan:
    return InstallPlan(
        plan_id=new_id("IPL"), created_at=utc_now_iso(),
        systemd_files=SYSTEMD_FILES,
        timer_files=TIMER_FILES,
        cron_example="deploy/cron/paper-trading-full.cron.example",
        logrotate_example="deploy/logrotate.d/paper-trading-ops.example",
        pre_install_checks=PRE_INSTALL_CHECKS,
        install_commands=INSTALL_COMMANDS.strip(),
        enable_commands=ENABLE_COMMANDS.strip(),
        rollback_commands=ROLLBACK_COMMANDS.strip(),
        manual_confirmation_required=True,
        auto_install=False,
        final_verdict="PAPER_OPS_INSTALL_PLAN_READY|manual_confirmation_required=true|auto_install=false|REAL_ORDER_SUBMIT_NOT_ALLOWED",
    )
