"""Integration test: MACD rebound deployment audit."""
from __future__ import annotations
import pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent.parent))
from src.external_scanner_integrations.macd_rebound_deployment_audit import run_audit, render_report

FIXTURE = str(pathlib.Path(__file__).resolve().parent.parent / "fixtures" / "macd_rebound_scanner")


def test_audit_checks() -> None:
    audit = run_audit(FIXTURE)
    assert len(audit.checks) > 0


def test_audit_systemd_present() -> None:
    audit = run_audit(FIXTURE)
    svc = [c for c in audit.checks if "systemd" in c.component]
    assert len(svc) > 0
    assert svc[0].status == "PRESENT"


def test_audit_logrotate_present() -> None:
    audit = run_audit(FIXTURE)
    lr = [c for c in audit.checks if "logrotate" in c.component]
    assert len(lr) > 0
    assert lr[0].status == "PRESENT"


def test_audit_verdict() -> None:
    audit = run_audit(FIXTURE)
    assert "REAL_ORDER_SUBMIT_NOT_ALLOWED" in audit.final_verdict


def test_render_report() -> None:
    audit = run_audit(FIXTURE)
    md = render_report(audit)
    assert "# MACD Rebound Deployment Audit" in md


def main() -> None:
    test_audit_checks()
    test_audit_systemd_present()
    test_audit_logrotate_present()
    test_audit_verdict()
    test_render_report()
    print("test_macd_rebound_deployment_audit: ALL PASS")


if __name__ == "__main__":
    main()
