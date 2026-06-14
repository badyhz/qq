"""Integration test: MACD rebound config."""
from __future__ import annotations
import pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent.parent))
from src.external_scanner_integrations.macd_rebound_config import create_config, detect_scanner_path, check_expected_files

FIXTURE = pathlib.Path(__file__).resolve().parent.parent / "fixtures" / "macd_rebound_scanner"


def test_detect_scanner_path_found(tmp_path: None = None) -> None:
    candidates = [str(FIXTURE)]
    cfg = {"local_path_candidates": candidates}
    result = detect_scanner_path(cfg)
    assert result == str(FIXTURE), f"Expected {FIXTURE}, got {result}"


def test_detect_scanner_path_not_found() -> None:
    cfg = {"local_path_candidates": ["/nonexistent/path"]}
    result = detect_scanner_path(cfg)
    assert result is None


def test_check_expected_files() -> None:
    files = ["main.py", "config.yaml", "requirements.txt"]
    result = check_expected_files(str(FIXTURE), files)
    assert all(result.values()), f"Missing files: {result}"


def test_check_expected_files_missing() -> None:
    files = ["main.py", "nonexistent.txt"]
    result = check_expected_files(str(FIXTURE), files)
    assert result["main.py"] is True
    assert result["nonexistent.txt"] is False


def test_create_config() -> None:
    cfg = create_config()
    assert cfg.scanner_name == "macd_rebound_scanner"
    assert cfg.real_order_submit_allowed is False
    assert "REAL_ORDER_SUBMIT_NOT_ALLOWED" in cfg.final_verdict


def main() -> None:
    test_detect_scanner_path_found()
    test_detect_scanner_path_not_found()
    test_check_expected_files()
    test_check_expected_files_missing()
    test_create_config()
    print("test_macd_rebound_config: ALL PASS")


if __name__ == "__main__":
    main()
