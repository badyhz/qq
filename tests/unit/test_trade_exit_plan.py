"""Unit test: exit plan."""
from __future__ import annotations
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent.parent))
from src.trade_plan_engine.exit_plan import generate_exit_plan, compute_stop_loss, compute_take_profits


def test_exit_plan_creation() -> None:
    ep = generate_exit_plan(104500.0, 101400.0, ma25=103800.0)
    assert ep.exit_plan_id.startswith("EP_")
    assert "stop_loss" in ep.stop_loss_rule.lower()


def test_compute_stop_loss_with_ma25() -> None:
    sl = compute_stop_loss(100000.0, ma25=98000.0)
    expected = min(100000.0 * 0.97, 98000.0 * 0.995)
    assert sl == round(expected, 8)


def test_compute_stop_loss_without_ma25() -> None:
    sl = compute_stop_loss(100000.0)
    assert sl == round(100000.0 * 0.97, 8)


def test_take_profits_ordering() -> None:
    tp1, tp2, tp3 = compute_take_profits(104500.0, 101400.0)
    assert tp1 < tp2 < tp3
    assert tp1 > 104500.0


def test_take_profits_r_multiples() -> None:
    entry = 104500.0
    sl = 101400.0
    r = entry - sl
    tp1, tp2, tp3 = compute_take_profits(entry, sl)
    assert abs(tp1 - (entry + 1.5 * r)) < 0.01
    assert abs(tp2 - (entry + 2.5 * r)) < 0.01
    assert abs(tp3 - (entry + 4.0 * r)) < 0.01


def test_exit_plan_rules_present() -> None:
    ep = generate_exit_plan(104500.0, 101400.0)
    assert len(ep.tp1_rule) > 0
    assert len(ep.time_stop_rule) > 0
    assert len(ep.signal_failure_rule) > 0
    assert len(ep.trailing_stop_rule) > 0


def main() -> None:
    test_exit_plan_creation()
    test_compute_stop_loss_with_ma25()
    test_compute_stop_loss_without_ma25()
    test_take_profits_ordering()
    test_take_profits_r_multiples()
    test_exit_plan_rules_present()
    print("test_trade_exit_plan: ALL PASS")


if __name__ == "__main__":
    main()
