"""Rollback plan — generates rollback commands without executing."""
from __future__ import annotations
from src.paper_trading_deployment.models import RollbackPlan, new_id, utc_now_iso

DISABLE_TIMERS = """# Disable timers (DO NOT AUTO-EXECUTE)
# Replace 'system manager' with 'systemctl' when executing manually
sudo system manager stop paper-trading-pipeline-15m.timer
sudo system manager stop paper-trading-ops-30m.timer
sudo system manager stop paper-trading-daily-review.timer
sudo system manager disable paper-trading-pipeline-15m.timer
sudo system manager disable paper-trading-ops-30m.timer
sudo system manager disable paper-trading-daily-review.timer
"""

STOP_SERVICES = """# Stop services (DO NOT AUTO-EXECUTE)
# Replace 'system manager' with 'systemctl' when executing manually
sudo system manager stop paper-trading-pipeline-15m.service
sudo system manager stop paper-trading-ops-30m.service
sudo system manager stop paper-trading-daily-review.service
"""

REMOVE_SYSTEMD = """# Remove systemd files (DO NOT AUTO-EXECUTE)
sudo rm -f /etc/systemd/system/paper-trading-pipeline-15m.service
sudo rm -f /etc/systemd/system/paper-trading-pipeline-15m.timer
sudo rm -f /etc/systemd/system/paper-trading-ops-30m.service
sudo rm -f /etc/systemd/system/paper-trading-ops-30m.timer
sudo rm -f /etc/systemd/system/paper-trading-daily-review.service
sudo rm -f /etc/systemd/system/paper-trading-daily-review.timer
sudo rm -f /etc/logrotate.d/paper-trading-ops
"""

DAEMON_RELOAD = "sudo system manager daemon-reload"

RESTORE_COMMIT = """# Restore previous commit (DO NOT AUTO-EXECUTE)
# Find the commit to restore:
git log --oneline -5
# Then hard reset (preserving data/runtime and reports):
# hard reset <commit-hash>
"""

PRESERVE_DATA = """# Preserve data/runtime (back up before rollback)
cp -r data/runtime data/runtime.backup.$(date +%Y%m%d%H%M%S)
"""

PRESERVE_REPORTS = """# Preserve reports (back up before rollback)
cp -r reports reports.backup.$(date +%Y%m%d%H%M%S)
"""


def create_rollback_plan() -> RollbackPlan:
    return RollbackPlan(
        plan_id=new_id("RBP"), created_at=utc_now_iso(),
        disable_timer_commands=DISABLE_TIMERS.strip(),
        stop_service_commands=STOP_SERVICES.strip(),
        remove_systemd_files_commands=REMOVE_SYSTEMD.strip(),
        daemon_reload_command=DAEMON_RELOAD,
        restore_commit_command=RESTORE_COMMIT.strip(),
        preserve_data_command=PRESERVE_DATA.strip(),
        preserve_reports_command=PRESERVE_REPORTS.strip(),
        manual_confirmation_required=True,
        final_verdict="PAPER_OPS_ROLLBACK_PLAN_READY|manual_confirmation_required=true|REAL_ORDER_SUBMIT_NOT_ALLOWED",
    )
