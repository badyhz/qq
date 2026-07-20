"""P1-02 closed-bar selection, propagation and cohort contract tests."""
from __future__ import annotations

import json
import hashlib
import os
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from core.paper_trading.data_source import (
    CLOSED_BAR_CONTRACT_VERSION,
    MarketBar,
    select_closed_bars,
)
from core.paper_trading.paper_position import (
    OVERLAP_MANIFEST_FILENAME,
    activate_closed_bar_trusted_cohort,
    build_overlap_exclusion_manifest,
    dict_to_position,
    load_canonical_closed_clean_positions,
    open_position,
    stable_signal_key,
)
from scripts.generate_static_console import build_public_json
from core.paper_trading.shadow_run_registry import build_run_record
from core.paper_trading.strategy_config import (
    AlertConfig,
    DataApiConfig,
    StrategyConfig,
    StrategyLibrary,
)
from core.paper_trading.strategy_registry import StrategyRunResult
from core.paper_trading.strategy_switchboard import run_switchboard
from core.paper_trading.trade_intent import build_trade_intent


UTC = timezone.utc
BASE = datetime(2026, 7, 20, 12, 0, tzinfo=UTC)
REPO_ROOT = Path(__file__).resolve().parents[2]
FULL_COMMIT = "8164e8f1a4352f4d0884378869881d6c76cebda1"
ACTIVATION_AT = "2026-07-20T12:05:30+00:00"
ACTIVATION_RUN_ID = "SHADOW-RUN-20260720-120000"
SPLIT_DAY_RUN_ID = "20260720T181030Z_shadow_lifecycle"
SPLIT_DAY_STARTED_AT = "2026-07-20T18:10:29+00:00"
SPLIT_DAY_REPORT_DATE = "2026-07-21"
SPLIT_DAY_ACTIVATION_AT = "2026-07-20T18:10:45+00:00"


def _bar(index=0, timeframe="5m", close_time=None, close=100.0, **overrides):
    seconds = {"5m": 300, "15m": 900, "1h": 3600}[timeframe]
    opened = BASE + timedelta(seconds=index * seconds)
    value = {
        "timestamp": opened.timestamp(),
        "open": close,
        "high": close + 1,
        "low": close - 1,
        "close": close,
        "volume": 10.0,
        "symbol": "BTCUSDT",
        "timeframe": timeframe,
        "close_time": close_time if close_time is not None else opened + timedelta(seconds=seconds),
    }
    value.update(overrides)
    return MarketBar(**value)


@pytest.mark.parametrize("timeframe", ["5m", "1h"])
def test_inclusive_boundary_and_multiple_timeframes(timeframe):
    bar = _bar(timeframe=timeframe)
    result = select_closed_bars([bar], bar.close_time)
    assert result.bars == [bar.__class__(**{**bar.__dict__, "provider_closed": True})]
    assert result.signal_bar_close_time.endswith("+00:00")
    assert result.contract_version == CLOSED_BAR_CONTRACT_VERSION


def test_forming_and_future_bars_are_excluded_before_use():
    closed = _bar(0)
    forming = _bar(1, close=999.0)
    result = select_closed_bars([closed, forming], closed.close_time)
    assert [bar.close for bar in result.bars] == [100.0]
    assert result.rejected_forming_or_future == 1


def test_missing_close_time_derives_only_from_declared_interval():
    derived = _bar(close_time=None)
    derived = MarketBar(**{**derived.__dict__, "close_time": None})
    result = select_closed_bars([derived], BASE + timedelta(minutes=5))
    assert result.eligible_count == 1
    ambiguous = MarketBar(**{**derived.__dict__, "timeframe": ""})
    rejected = select_closed_bars([ambiguous], BASE + timedelta(minutes=5))
    assert rejected.eligible_count == 0
    assert rejected.rejected_malformed == 1


def test_naive_and_inconsistent_close_times_fail_closed():
    naive = _bar(close_time=datetime(2026, 7, 20, 12, 5))
    inconsistent = _bar(close_time=BASE + timedelta(hours=2))
    result = select_closed_bars([naive, inconsistent], BASE + timedelta(hours=3))
    assert result.eligible_count == 0
    assert result.rejected_malformed == 2


def test_ordering_identical_dedup_and_conflicting_duplicate_rejection():
    first = _bar(0)
    second = _bar(1)
    ordered = select_closed_bars(
        [second, first, first], second.close_time,
    )
    assert [bar.timestamp for bar in ordered.bars] == [first.timestamp, second.timestamp]
    conflicting = MarketBar(**{**first.__dict__, "close": 101.0, "high": 102.0})
    rejected = select_closed_bars([first, conflicting, second], second.close_time)
    assert [bar.timestamp for bar in rejected.bars] == [second.timestamp]
    assert rejected.rejected_conflicting_duplicate == 1


def _library():
    api = DataApiConfig(
        name="public", api_type="binance_public_klines", market="usdm",
        readonly=True, requires_secret=False, allows_orders=False, default_limit=120,
    )
    strategy = StrategyConfig(
        strategy_id="macd_rebound_watch", strategy_type="macd_rebound_watch",
        description="test", enabled=True, data_api="public", symbols=["BTCUSDT"],
        timeframes=["5m"], mode="paper",
        alert=AlertConfig(feishu_payload=True, auto_send=False),
    )
    return StrategyLibrary(
        version=1, default_mode="paper", default_alert="payload",
        data_apis={"public": api}, strategies={strategy.strategy_id: strategy},
        enabled_strategies={strategy.strategy_id: strategy}, disabled_strategies={},
    )


class _Adapter:
    def __init__(self, bars):
        self.bars = bars

    def get_bars(self, _symbol, timeframe="1h", limit=100):
        return self.bars[:limit]


def test_switchboard_filters_before_indicator_calculation(monkeypatch):
    bars = [_bar(i) for i in range(30)]
    forming = _bar(30, close=10000.0)
    captured = {}

    def fake_analyze(strategy_id, strategy_type, selected, **kwargs):
        captured["bars"] = selected
        captured.update(kwargs)
        return StrategyRunResult(
            strategy_id=strategy_id, strategy_type=strategy_type,
            symbol="BTCUSDT", timeframe="5m", success=True,
            candidate=None, error=None,
        )

    monkeypatch.setattr("core.paper_trading.strategy_switchboard.analyze_for_strategy", fake_analyze)
    monkeypatch.setattr("core.paper_trading.strategy_switchboard.time.sleep", lambda _x: None)
    result = run_switchboard(
        _library(), _Adapter(bars + [forming]), "2026-07-20",
        decision_cutoff=bars[-1].close_time,
    )
    assert len(captured["bars"]) == 30
    assert captured["bars"][-1].close == 100.0
    assert captured["signal_bar_close_time"] == result.closed_bar_audits[0]["signal_bar_close_time"]
    assert result.closed_bar_audits[0]["rejected_forming_or_future"] == 1


def _plan(signal_close="2026-07-20T12:05:00.000+00:00"):
    return {
        "direction": "LONG_OBSERVE",
        "symbol": "BTCUSDT",
        "timeframe": "5m",
        "entry_observation": 100.0,
        "invalidation_level": 95.0,
        "take_profit_observation": 110.0,
        "rr_ratio": 2.0,
        "risk_distance_pct": 5.0,
        "reward_distance_pct": 10.0,
        "reason": "macd_rebound_watch: test",
        "signal_bar_close_time": signal_close,
        "signal_bar_contract_version": CLOSED_BAR_CONTRACT_VERSION,
    }


def test_same_closed_bar_identity_stable_and_next_bar_different():
    first = build_trade_intent(_plan(), "2026-07-20").to_dict()
    retry = build_trade_intent(_plan(), "2026-07-20").to_dict()
    next_bar = build_trade_intent(
        _plan("2026-07-20T12:10:00.000+00:00"), "2026-07-20"
    ).to_dict()
    assert stable_signal_key(first) == stable_signal_key(retry)
    assert stable_signal_key(first) != stable_signal_key(next_bar)


def test_open_ledger_round_trip_preserves_closed_bar_contract():
    intent = build_trade_intent(_plan(), "2026-07-20").to_dict()
    position = open_position(intent)
    assert position is not None
    restored = dict_to_position(json.loads(json.dumps(position.to_dict())))
    assert restored.signal_bar_close_time == "2026-07-20T12:05:00.000+00:00"
    assert restored.signal_bar_contract_version == CLOSED_BAR_CONTRACT_VERSION
    assert restored.signal_key == stable_signal_key(intent)


def test_open_rejects_future_or_incomplete_closed_bar_contract():
    future = build_trade_intent(
        _plan("2099-07-20T12:05:00.000+00:00"), "2026-07-20"
    ).to_dict()
    assert open_position(future) is None
    missing = build_trade_intent(_plan(), "2026-07-20").to_dict()
    missing["signal_bar_close_time"] = None
    assert open_position(missing) is None


def test_legacy_and_p1_02_trusted_cohorts_remain_distinct(tmp_path):
    trusted = open_position(build_trade_intent(_plan(), "2026-07-20").to_dict()).to_dict()
    trusted.update({
        "position_id": "P_TRUSTED", "opened_at": "2026-07-20T12:06:00+00:00",
        "created_at": "2026-07-20T12:06:00+00:00", "recorded_at": "2026-07-20T12:07:00+00:00",
        "status": "TAKE_PROFIT_HIT", "closed_at": "2026-07-20T12:07:00+00:00",
        "exit_price": 110.0, "r_multiple": 2.0, "quarantine_status": "CLEAN",
    })
    legacy = dict(trusted)
    legacy.update({
        "position_id": "P_LEGACY", "intent_id": "TI_LEGACY", "symbol": "ETHUSDT",
        "signal_bar_close_time": None, "signal_bar_contract_version": "legacy_missing",
        "opened_at": "2026-07-20T12:08:00+00:00", "created_at": "2026-07-20T12:08:00+00:00",
        "recorded_at": "2026-07-20T12:09:00+00:00", "closed_at": "2026-07-20T12:09:00+00:00",
    })
    records = [trusted, legacy]
    (tmp_path / "2026-07-20_paper_position_ledger.jsonl").write_text(
        "".join(json.dumps(item) + "\n" for item in records)
    )
    (tmp_path / "2026-07-20_shadow_lifecycle_result.json").write_text(json.dumps({
        "date": "2026-07-20", "mode": "real_public_readonly",
        "safety_flags": ["PAPER_ONLY", "SHADOW_ONLY"],
    }))
    manifest = build_overlap_exclusion_manifest(records, "2026-07-20T12:00:00+00:00")
    manifest["closed_bar_trusted_cohort_start_at"] = ACTIVATION_AT
    manifest["closed_bar_trusted_cohort_rule_version"] = CLOSED_BAR_CONTRACT_VERSION
    manifest["closed_bar_trusted_cohort_start_run_id"] = ACTIVATION_RUN_ID
    manifest["closed_bar_trusted_cohort_start_commit"] = FULL_COMMIT
    (tmp_path / OVERLAP_MANIFEST_FILENAME).write_text(json.dumps(manifest))
    eligible, _all, diag = load_canonical_closed_clean_positions(str(tmp_path))
    assert len(eligible) == 2
    assert diag["trusted_cohort_closed"] == 2
    assert diag["p1_02_trusted_cohort_closed"] == 1
    assert diag["p1_02_trusted_cohort_start_run_id"] == ACTIVATION_RUN_ID
    assert diag["p1_02_trusted_cohort_start_commit"] == FULL_COMMIT
    assert diag["closed_bar_trusted_cohort_start_at"] == ACTIVATION_AT
    assert diag["closed_bar_trusted_cohort_rule_version"] == CLOSED_BAR_CONTRACT_VERSION
    assert diag["closed_bar_trusted_cohort_start_run_id"] == ACTIVATION_RUN_ID
    assert diag["closed_bar_trusted_cohort_start_commit"] == FULL_COMMIT
    assert diag["legacy_closed_without_closed_bar_contract"] == 1


def test_p1_02_cohort_is_not_locally_activated(tmp_path):
    manifest = build_overlap_exclusion_manifest([], "2026-07-20T12:00:00+00:00")
    (tmp_path / OVERLAP_MANIFEST_FILENAME).write_text(json.dumps(manifest))
    _eligible, _all, diag = load_canonical_closed_clean_positions(str(tmp_path))
    assert diag["p1_02_trusted_cohort_start_at"] is None
    assert diag["p1_02_trusted_cohort_closed"] == 0


def test_p1_02_cohort_uses_open_boundary_and_requires_complete_contract(tmp_path):
    cases = [
        ("P_PRE", "BTCUSDT", "2026-07-20T12:04:00+00:00", "2026-07-20T12:03:00+00:00", CLOSED_BAR_CONTRACT_VERSION),
        ("P_POST", "ETHUSDT", "2026-07-20T12:06:00+00:00", "2026-07-20T12:05:00+00:00", CLOSED_BAR_CONTRACT_VERSION),
        ("P_NO_TIME", "SOLUSDT", "2026-07-20T12:07:00+00:00", None, CLOSED_BAR_CONTRACT_VERSION),
        ("P_NO_VERSION", "BNBUSDT", "2026-07-20T12:08:00+00:00", "2026-07-20T12:05:00+00:00", "legacy_missing"),
    ]
    records = []
    for pid, symbol, opened_at, signal_time, version in cases:
        position = open_position(
            build_trade_intent(_plan(), "2026-07-20").to_dict()
        ).to_dict()
        position.update({
            "position_id": pid, "symbol": symbol, "opened_at": opened_at,
            "created_at": opened_at, "recorded_at": "2026-07-20T12:10:00+00:00",
            "status": "TAKE_PROFIT_HIT", "closed_at": "2026-07-20T12:09:00+00:00",
            "exit_price": 110.0, "r_multiple": 2.0, "quarantine_status": "CLEAN",
            "signal_bar_close_time": signal_time,
            "signal_bar_contract_version": version,
        })
        records.append(position)
    (tmp_path / "2026-07-20_paper_position_ledger.jsonl").write_text(
        "".join(json.dumps(item) + "\n" for item in records)
    )
    (tmp_path / "2026-07-20_shadow_lifecycle_result.json").write_text(json.dumps({
        "date": "2026-07-20", "mode": "real_public_readonly",
        "safety_flags": ["PAPER_ONLY", "SHADOW_ONLY"],
    }))
    manifest = build_overlap_exclusion_manifest(
        records, "2026-07-20T12:00:00+00:00",
    )
    manifest.update({
        "closed_bar_trusted_cohort_start_at": ACTIVATION_AT,
        "closed_bar_trusted_cohort_rule_version": CLOSED_BAR_CONTRACT_VERSION,
        "closed_bar_trusted_cohort_start_run_id": ACTIVATION_RUN_ID,
        "closed_bar_trusted_cohort_start_commit": FULL_COMMIT,
    })
    (tmp_path / OVERLAP_MANIFEST_FILENAME).write_text(json.dumps(manifest))

    eligible, _all, diag = load_canonical_closed_clean_positions(str(tmp_path))
    assert len(eligible) == 4
    assert diag["p1_02_trusted_cohort_closed"] == 1
    assert records[1]["position_id"] == "P_POST"


def test_accepted_overlap_fixture_remains_exactly_200():
    positions = []
    for index in range(201):
        opened = BASE + timedelta(seconds=index)
        positions.append({
            "position_id": f"P{index}", "strategy_id": "macd_rebound_watch",
            "symbol": "BTCUSDT", "timeframe": "5m", "side": "LONG",
            "opened_at": opened.isoformat(),
            "closed_at": (BASE + timedelta(hours=1)).isoformat(),
        })
    manifest = build_overlap_exclusion_manifest(
        positions, "2026-07-20T14:00:00+00:00"
    )
    assert manifest["excluded_overlap_positions"] == 200


def test_run_registry_propagates_closed_bar_summary():
    record = build_run_record({
        "date": "2026-07-20", "mode": "real_public_readonly",
        "pipeline_status": "PASS", "summary": {
            "closed_bar_contract_version": CLOSED_BAR_CONTRACT_VERSION,
            "decision_cutoff": "2026-07-20T12:00:00.000+00:00",
            "closed_bar_counts": {"raw_candles": 120, "eligible_closed_candles": 119},
        }, "safety_flags": ["SHADOW_ONLY", "NO_TESTNET", "NO_LIVE"],
    }, run_id="RUN")
    data = record.to_dict()
    assert data["closed_bar_contract_version"] == CLOSED_BAR_CONTRACT_VERSION
    assert data["decision_cutoff"].endswith("+00:00")
    assert data["closed_bar_counts"]["eligible_closed_candles"] == 119
    assert "NO_TESTNET" in data["safety_flags"] and "NO_LIVE" in data["safety_flags"]


def _activation_manifest(tmp_path, exclusion_count=200):
    positions = []
    for index in range(exclusion_count + 1):
        opened = BASE + timedelta(seconds=index)
        positions.append({
            "position_id": f"P{index}", "strategy_id": "macd_rebound_watch",
            "symbol": "BTCUSDT", "timeframe": "5m", "side": "LONG",
            "opened_at": opened.isoformat(),
            "closed_at": (BASE + timedelta(hours=1)).isoformat(),
        })
    manifest = build_overlap_exclusion_manifest(
        positions, "2026-07-20T12:05:00+00:00",
    )
    manifest["unrelated_audit_note"] = {"preserve": [1, 2, 3]}
    path = tmp_path / OVERLAP_MANIFEST_FILENAME
    path.write_text(json.dumps(manifest, indent=2) + "\n")
    return path, manifest


def _activate(path, **overrides):
    values = {
        "start_at": ACTIVATION_AT,
        "start_run_id": ACTIVATION_RUN_ID,
        "start_commit": FULL_COMMIT,
        "rule_version": CLOSED_BAR_CONTRACT_VERSION,
    }
    values.update(overrides)
    return activate_closed_bar_trusted_cohort(str(path), **values)


def _sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_activation_success_preserves_all_200_exclusions_and_unrelated_fields(tmp_path):
    path, before = _activation_manifest(tmp_path)
    result = _activate(path)
    after = json.loads(path.read_text())
    assert result.status == "ACTIVATED"
    assert after["closed_bar_trusted_cohort_start_at"] == ACTIVATION_AT
    assert after["closed_bar_trusted_cohort_rule_version"] == CLOSED_BAR_CONTRACT_VERSION
    assert after["closed_bar_trusted_cohort_start_run_id"] == ACTIVATION_RUN_ID
    assert after["closed_bar_trusted_cohort_start_commit"] == FULL_COMMIT
    assert len(after["exclusions"]) == 200
    assert after["exclusions"] == before["exclusions"]
    assert after["unrelated_audit_note"] == before["unrelated_audit_note"]


def test_exact_reactivation_is_hash_stable_noop(tmp_path):
    path, _manifest = _activation_manifest(tmp_path)
    assert _activate(path).status == "ACTIVATED"
    before_hash = _sha256(path)
    result = _activate(path)
    assert result.status == "ALREADY_ACTIVE_SAME_METADATA"
    assert _sha256(path) == before_hash


@pytest.mark.parametrize("changed", [
    {"start_at": "2026-07-20T12:05:31+00:00"},
    {"start_run_id": "SHADOW-RUN-CONFLICT"},
    {"start_commit": "a" * 40},
])
def test_conflicting_reactivation_fails_without_mutation(tmp_path, changed):
    path, _manifest = _activation_manifest(tmp_path)
    assert _activate(path).status == "ACTIVATED"
    before = path.read_bytes()
    result = _activate(path, **changed)
    assert result.status == "CONFLICTING_ACTIVATION"
    assert path.read_bytes() == before


@pytest.mark.parametrize(("changed", "message"), [
    ({"start_at": "2026-07-20T12:05:30"}, "timezone-aware"),
    ({"start_at": "not-a-time"}, "valid RFC3339"),
    ({"start_at": "2026-07-20T20:05:30+08:00"}, "must use UTC"),
    ({"start_run_id": ""}, "non-empty"),
    ({"start_commit": "8164e8f"}, "full 40-character"),
    ({"start_commit": "z" * 40}, "full 40-character"),
    ({"rule_version": "closed_bar_v2"}, "closed_bar_v1"),
])
def test_invalid_activation_metadata_is_rejected(tmp_path, changed, message):
    path, _manifest = _activation_manifest(tmp_path)
    before = path.read_bytes()
    result = _activate(path, **changed)
    assert result.status == "INVALID_METADATA"
    assert message in result.error
    assert path.read_bytes() == before


def test_atomic_replace_failure_preserves_original_manifest(tmp_path, monkeypatch):
    path, before = _activation_manifest(tmp_path)
    original = path.read_bytes()

    def fail_replace(_source, _destination):
        raise OSError("simulated replace failure")

    monkeypatch.setattr("core.paper_trading.paper_position.os.replace", fail_replace)
    result = _activate(path)
    assert result.status == "ATOMIC_WRITE_FAILED"
    assert path.read_bytes() == original
    assert json.loads(path.read_text())["exclusions"] == before["exclusions"]


def _run_activation_cli(path, **overrides):
    values = {
        "start_at": ACTIVATION_AT,
        "run_id": ACTIVATION_RUN_ID,
        "commit": FULL_COMMIT,
    }
    values.update(overrides)
    return subprocess.run([
        sys.executable, "scripts/run_paper_position_simulator.py",
        "--output-dir", str(path.parent),
        "--activate-closed-bar-cohort",
        "--cohort-start-at", values["start_at"],
        "--cohort-start-run-id", values["run_id"],
        "--cohort-start-commit", values["commit"],
    ], cwd=REPO_ROOT, capture_output=True, text=True)


def test_production_cli_activation_repeat_and_conflict(tmp_path):
    path, _manifest = _activation_manifest(tmp_path)
    first = _run_activation_cli(path)
    assert first.returncode == 0 and '"status": "ACTIVATED"' in first.stdout
    activated = path.read_bytes()
    repeat = _run_activation_cli(path)
    assert repeat.returncode == 0
    assert '"status": "ALREADY_ACTIVE_SAME_METADATA"' in repeat.stdout
    assert path.read_bytes() == activated
    conflict = _run_activation_cli(path, run_id="DIFFERENT-RUN")
    assert conflict.returncode != 0
    assert '"status": "CONFLICTING_ACTIVATION"' in conflict.stdout
    assert path.read_bytes() == activated


def test_cli_metadata_without_explicit_activation_flag_is_rejected(tmp_path):
    result = subprocess.run([
        sys.executable, "scripts/run_paper_position_simulator.py",
        "--output-dir", str(tmp_path), "--cohort-start-at", ACTIVATION_AT,
    ], cwd=REPO_ROOT, capture_output=True, text=True)
    assert result.returncode != 0
    assert "requires --activate-closed-bar-cohort" in result.stdout
    assert not (tmp_path / OVERLAP_MANIFEST_FILENAME).exists()


def _fake_wrapper_project(tmp_path, fail_pattern="", fail_code=0):
    project = tmp_path / "project"
    fakebin = project / "fakebin"
    (project / ".venv" / "bin").mkdir(parents=True)
    (project / "logs" / "cloud_shadow").mkdir(parents=True)
    fakebin.mkdir()
    call_log = tmp_path / "wrapper_calls.log"
    (project / ".venv" / "bin" / "activate").write_text(
        f'export PATH="{fakebin}:$PATH"\n'
    )
    fake_python = fakebin / "python3"
    fake_python.write_text(
        "#!/usr/bin/env bash\n"
        "printf '%s\\n' \"$*\" >> \"$CALL_LOG\"\n"
        "if [[ \"$*\" == *build_pipeline_context* ]]; then\n"
        f"  echo '{SPLIT_DAY_RUN_ID} {SPLIT_DAY_STARTED_AT} {SPLIT_DAY_REPORT_DATE}'\n"
        "elif [ \"${1:-}\" = '-c' ]; then\n"
        f"  echo '{SPLIT_DAY_ACTIVATION_AT}'\n"
        "fi\n"
        f"if [ -n {json.dumps(fail_pattern)} ] && [[ \"$*\" == *{fail_pattern}* ]]; then exit {fail_code}; fi\n"
    )
    fake_python.chmod(0o755)
    fake_git = fakebin / "git"
    fake_git.write_text(f"#!/usr/bin/env bash\necho {FULL_COMMIT}\n")
    fake_git.chmod(0o755)
    env = os.environ.copy()
    env.update({
        "PROJECT_DIR": str(project),
        "CALL_LOG": str(call_log),
        "PATH": f"{fakebin}:{env['PATH']}",
    })
    return project, call_log, env


def _run_wrapper(env, activate=False):
    command = ["bash", str(REPO_ROOT / "scripts/run_cloud_shadow_collection_once.sh")]
    if activate:
        command.append("--activate-closed-bar-cohort")
    return subprocess.run(command, capture_output=True, text=True, env=env)


def test_wrapper_activates_after_gate_with_same_run_id_and_head(tmp_path):
    _project, call_log, env = _fake_wrapper_project(tmp_path)
    result = _run_wrapper(env, activate=True)
    assert result.returncode == 0, result.stdout + result.stderr
    calls = call_log.read_text()
    gate = calls.index("run_sample_collection_gate.py")
    activation = calls.index("--activate-closed-bar-cohort")
    post_scorecard = calls.rindex("run_paper_performance_scorecard.py")
    console = calls.index("generate_static_console.py")
    assert gate < activation < post_scorecard < console
    assert f"report_date={SPLIT_DAY_REPORT_DATE}" in result.stdout
    lifecycle_call = next(
        line for line in calls.splitlines() if "run_shadow_trading_lifecycle.py" in line
    )
    assert f"--date {SPLIT_DAY_REPORT_DATE}" in lifecycle_call
    assert f"--run-id {SPLIT_DAY_RUN_ID}" in lifecycle_call
    assert f"--decision-cutoff {SPLIT_DAY_STARTED_AT}" in lifecycle_call
    activation_call = next(
        line for line in calls.splitlines() if "--activate-closed-bar-cohort" in line
    )
    assert f"--cohort-start-at {SPLIT_DAY_ACTIVATION_AT}" in activation_call
    assert f"--cohort-start-run-id {SPLIT_DAY_RUN_ID}" in activation_call
    assert f"--cohort-start-commit {FULL_COMMIT}" in activation_call
    gate_call = next(
        line for line in calls.splitlines() if "run_sample_collection_gate.py" in line
    )
    console_call = next(
        line for line in calls.splitlines() if "generate_static_console.py" in line
    )
    assert f"--date {SPLIT_DAY_REPORT_DATE}" in gate_call
    assert f"--report-date {SPLIT_DAY_REPORT_DATE}" in console_call


def test_wrapper_pipeline_failure_never_activates(tmp_path):
    _project, call_log, env = _fake_wrapper_project(
        tmp_path, "run_shadow_position_update_only.py", 23,
    )
    result = _run_wrapper(env, activate=True)
    assert result.returncode == 23
    assert "--activate-closed-bar-cohort" not in call_log.read_text()


def test_wrapper_activation_failure_blocks_console_and_final_success(tmp_path):
    _project, call_log, env = _fake_wrapper_project(
        tmp_path, "--activate-closed-bar-cohort", 42,
    )
    result = _run_wrapper(env, activate=True)
    assert result.returncode == 42
    calls = call_log.read_text()
    assert "--activate-closed-bar-cohort" in calls
    assert "generate_static_console.py" not in calls


def test_ordinary_wrapper_run_does_not_invent_activation(tmp_path):
    project, call_log, env = _fake_wrapper_project(tmp_path)
    report_dir = project / "reports" / "strategies"
    report_dir.mkdir(parents=True)
    manifest_path, _manifest = _activation_manifest(report_dir)
    assert _activate(manifest_path).status == "ACTIVATED"
    activated_hash = _sha256(manifest_path)
    result = _run_wrapper(env, activate=False)
    assert result.returncode == 0
    assert "--activate-closed-bar-cohort" not in call_log.read_text()
    assert _sha256(manifest_path) == activated_hash


def test_public_console_payload_propagates_all_activation_fields():
    diagnostics = {
        "p1_02_trusted_cohort_closed": 0,
        "p1_02_trusted_cohort_start_at": ACTIVATION_AT,
        "p1_02_trusted_cohort_rule_version": CLOSED_BAR_CONTRACT_VERSION,
        "p1_02_trusted_cohort_start_run_id": ACTIVATION_RUN_ID,
        "p1_02_trusted_cohort_start_commit": FULL_COMMIT,
        "closed_bar_trusted_cohort_start_at": ACTIVATION_AT,
        "closed_bar_trusted_cohort_rule_version": CLOSED_BAR_CONTRACT_VERSION,
        "closed_bar_trusted_cohort_start_run_id": ACTIVATION_RUN_ID,
        "closed_bar_trusted_cohort_start_commit": FULL_COMMIT,
    }
    payload = build_public_json({
        "scorecard": {"diagnostics": diagnostics, "global_metrics": {}},
        "gate": {}, "counts": {}, "all_canonical": [],
    }, server_commit=FULL_COMMIT)
    assert payload["p1_02_trusted_cohort_start_at"] == ACTIVATION_AT
    assert payload["p1_02_trusted_cohort_rule_version"] == CLOSED_BAR_CONTRACT_VERSION
    assert payload["p1_02_trusted_cohort_start_run_id"] == ACTIVATION_RUN_ID
    assert payload["p1_02_trusted_cohort_start_commit"] == FULL_COMMIT
    assert payload["closed_bar_trusted_cohort_start_at"] == ACTIVATION_AT
    assert payload["closed_bar_trusted_cohort_rule_version"] == CLOSED_BAR_CONTRACT_VERSION
    assert payload["closed_bar_trusted_cohort_start_run_id"] == ACTIVATION_RUN_ID
    assert payload["closed_bar_trusted_cohort_start_commit"] == FULL_COMMIT
