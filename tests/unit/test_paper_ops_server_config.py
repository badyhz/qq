"""Unit test: paper ops server config."""
from __future__ import annotations
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent.parent))
from src.paper_trading_deployment.server_config import build_server_config, load_config

FIXTURE_CFG = str(pathlib.Path(__file__).resolve().parent.parent / "fixtures" / "paper_trading_deployment" / "config" / "paper_trading_ops_server.example.yaml")


def test_load_fixture_config() -> None:
    cfg = load_config(FIXTURE_CFG)
    assert cfg["deployment_name"] == "paper_trading_ops_server_test"
    assert cfg["mode"] == "dry_run_only"


def test_build_config_from_fixture() -> None:
    cfg = build_server_config(FIXTURE_CFG)
    assert cfg.deployment_name == "paper_trading_ops_server_test"
    assert cfg.host_alias == "test_monitor"


def test_safety_flags_all_false() -> None:
    cfg = build_server_config(FIXTURE_CFG)
    for k, v in cfg.safety_flags.items():
        assert v is False, f"Safety flag {k} is not False"


def test_safety_verdict() -> None:
    cfg = build_server_config(FIXTURE_CFG)
    assert "SAFETY_FLAGS_ALL_FALSE" in cfg.final_verdict
    assert "REAL_ORDER_SUBMIT_NOT_ALLOWED" in cfg.final_verdict


def test_config_has_schedule() -> None:
    cfg = build_server_config(FIXTURE_CFG)
    assert "every_15m" in cfg.schedule
    assert "daily_2355" in cfg.schedule


def test_config_verdict_format() -> None:
    cfg = build_server_config(FIXTURE_CFG)
    assert "PAPER_OPS_SERVER_CONFIG_READY" in cfg.final_verdict


def main() -> None:
    test_load_fixture_config()
    test_build_config_from_fixture()
    test_safety_flags_all_false()
    test_safety_verdict()
    test_config_has_schedule()
    test_config_verdict_format()
    print("test_paper_ops_server_config: ALL PASS")


if __name__ == "__main__":
    main()
