"""Integration tests for server dry-run readiness pack."""
from __future__ import annotations
import pathlib, sys
ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))


def test_readme_exists():
    assert (ROOT / "deployment" / "runtime_dry_run" / "README.md").exists()


def test_env_example_exists():
    assert (ROOT / "deployment" / "runtime_dry_run" / "env.example").exists()


def test_safety_checklist_exists():
    assert (ROOT / "deployment" / "runtime_dry_run" / "safety_checklist.md").exists()


def test_systemd_examples_exist():
    svc_dir = ROOT / "deployment" / "runtime_dry_run" / "systemd"
    assert (svc_dir / "quant-system-dry-run-e2e.service.example").exists()
    assert (svc_dir / "quant-alert-dry-run.service.example").exists()
    assert (svc_dir / "quant-dashboard-render.service.example").exists()


def test_env_example_has_safety():
    content = (ROOT / "deployment" / "runtime_dry_run" / "env.example").read_text()
    assert "DRY_RUN" in content
    assert "NO_SUBMIT" in content


def test_readme_has_safety():
    content = (ROOT / "deployment" / "runtime_dry_run" / "README.md").read_text()
    assert "NOT ALLOWED" in content


def test_no_real_secrets():
    for p in (ROOT / "deployment" / "runtime_dry_run").rglob("*"):
        if p.is_file():
            content = p.read_text(encoding="utf-8", errors="ignore")
            assert "sk-" not in content, f"Found potential secret in {p}"
            assert "api_key=" not in content.lower() or "api_key=YOUR" in content or "api_key=<" in content
