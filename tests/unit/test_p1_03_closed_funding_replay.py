from __future__ import annotations

import copy
import json
import sys
from datetime import datetime, timezone

import pytest

from core.paper_trading.funding_replay import (
    funding_replay_record_fingerprint,
    re_enrich_closed_positions_funding,
    resolve_position_funding_close_boundary,
)
from core.paper_trading.paper_position import select_canonical_position_state


NOW = datetime(2026, 8, 20, 12, 0, tzinfo=timezone.utc)


def position(**overrides):
    base = {
        "position_id": "PP_REPLAY",
        "intent_id": "I1",
        "signal_key": "S1",
        "strategy_id": "weak_short_watch",
        "symbol": "XRPUSDT",
        "timeframe": "1h",
        "side": "SHORT",
        "status": "TAKE_PROFIT_HIT",
        "entry_price": 1.0,
        "stop_loss": 1.1,
        "take_profit": 0.8,
        "position_size_preview": 1.0,
        "opened_at": "2026-08-20T01:00:00+00:00",
        "closed_at": "2026-08-20T04:01:10+00:00",
        "exit_price": 0.8,
        "exit_reason": "take_profit triggered",
        "realized_pnl": 2.0,
        "realized_pnl_pct": 20.0,
        "r_multiple": 2.0,
        "last_checked_at": "2026-08-20T04:01:10+00:00",
        "last_checked_bar_time": 1787194800,
        "funding_events": [],
        "funding_events_verified_complete": False,
        "gap_execution_reference_price": 1.0,
    }
    base.update(overrides)
    return base


def event(at, rate="0.0001", interval=8 * 3600):
    return {
        "symbol": "XRPUSDT",
        "funding_event_at": at,
        "signed_funding_rate": rate,
        "mark_price": "1.0",
        "funding_interval_seconds": interval,
    }


class Adapter:
    def __init__(self, events=None, exc=None):
        self.events = list(events or [])
        self.exc = exc
        self.calls = []

    def get_funding_events(self, symbol, lookback_seconds):
        self.calls.append((symbol, lookback_seconds))
        if self.exc:
            raise self.exc
        return list(self.events)


def replay(p, events):
    return re_enrich_closed_positions_funding([p], Adapter(events), now=NOW)


def test_close_boundary_uses_persisted_then_stop_then_binance_bar_derivation():
    persisted = position(
        funding_attribution_close_time="2026-08-20T04:00:00+00:00"
    )
    boundary, source = resolve_position_funding_close_boundary(persisted)
    assert boundary == "2026-08-20T04:00:00.000+00:00"
    assert source == "persisted_funding_boundary_v1"

    stop = position(
        status="STOP_LOSS_HIT",
        funding_attribution_close_time=None,
        exit_trigger_bar_close_time="2026-08-20T04:00:00+00:00",
    )
    boundary, source = resolve_position_funding_close_boundary(stop)
    assert boundary == "2026-08-20T04:00:00.000+00:00"
    assert source == "exit_trigger_bar_close_time_v1"

    tp = position(funding_attribution_close_time=None)
    boundary, source = resolve_position_funding_close_boundary(tp)
    assert boundary == "2026-08-20T03:59:59.999+00:00"
    assert source == "last_checked_bar_time_plus_timeframe_binance_v1"


def test_just_closed_without_after_bracket_stays_partial_and_emits_no_update():
    p = position(funding_attribution_close_time="2026-08-20T04:00:00+00:00")
    updates, stats = replay(p, [event("2026-08-20T00:00:00+00:00")])
    assert updates == []
    assert stats["funding_replay_completed"] == 0
    assert stats["funding_replay_reason_breakdown"]["NO_AFTER_BRACKET"] == 1


def test_next_funding_event_allows_false_to_true_replay():
    p = position(funding_attribution_close_time="2026-08-20T04:00:00+00:00")
    events = [
        event("2026-08-20T00:00:00+00:00"),
        event("2026-08-20T08:00:00+00:00"),
    ]
    updates, stats = replay(p, events)
    assert len(updates) == 1
    assert updates[0]["funding_events_verified_complete"] is True
    assert updates[0]["funding_events"] == []
    assert updates[0]["funding_replay_version"] == "closed_funding_replay_v1"
    assert stats["funding_replay_completed"] == 1


def test_crossed_event_is_attributed_only_inside_position_window():
    p = position(
        opened_at="2026-08-20T01:00:00+00:00",
        funding_attribution_close_time="2026-08-20T12:00:00+00:00",
    )
    events = [
        event("2026-08-20T00:00:00+00:00"),
        event("2026-08-20T08:00:00+00:00", rate="0.0002"),
        event("2026-08-20T16:00:00+00:00"),
    ]
    updates, _ = replay(p, events)
    assert [item["funding_timestamp"] for item in updates[0]["funding_events"]] == [
        "2026-08-20T08:00:00+00:00"
    ]


@pytest.mark.parametrize(
    "events,reason",
    [
        ([], "NO_EVENTS"),
        (
            [
                event("2026-08-20T08:00:00+00:00"),
                event("2026-08-20T16:00:00+00:00"),
            ],
            "NO_BEFORE_BRACKET",
        ),
        (
            [
                event("2026-08-19T16:00:00+00:00"),
                event("2026-08-20T00:00:00+00:00"),
            ],
            "NO_AFTER_BRACKET",
        ),
        (
            [
                event("2026-08-20T00:00:00+00:00"),
                event("2026-08-20T16:00:00+00:00"),
            ],
            "WINDOW_GAP",
        ),
    ],
)
def test_incomplete_evidence_cases_fail_closed(events, reason):
    p = position(funding_attribution_close_time="2026-08-20T04:00:00+00:00")
    updates, stats = replay(p, events)
    assert updates == []
    assert stats["funding_replay_still_partial"] == 1
    assert stats["funding_replay_reason_breakdown"][reason] == 1


def test_source_failure_fails_closed():
    p = position(funding_attribution_close_time="2026-08-20T04:00:00+00:00")
    updates, stats = re_enrich_closed_positions_funding(
        [p], Adapter(exc=RuntimeError("source down")), now=NOW
    )
    assert updates == []
    assert stats["funding_replay_errors"] == 1
    assert stats["funding_replay_reason_breakdown"]["SOURCE_FAILURE"] == 1


def test_already_complete_skips_without_adapter_call():
    p = position(funding_events_verified_complete=True)
    adapter = Adapter(
        [
            event("2026-08-20T00:00:00+00:00"),
            event("2026-08-20T08:00:00+00:00"),
        ]
    )
    updates, stats = re_enrich_closed_positions_funding([p], adapter, now=NOW)
    assert updates == []
    assert adapter.calls == []
    assert stats["funding_replay_skipped_already_complete"] == 1


def test_legacy_closed_without_prospective_field_is_never_backfilled():
    p = position()
    p.pop("funding_events_verified_complete")
    p.pop("funding_events")
    adapter = Adapter(
        [
            event("2026-08-20T00:00:00+00:00"),
            event("2026-08-20T08:00:00+00:00"),
        ]
    )
    updates, stats = re_enrich_closed_positions_funding([p], adapter, now=NOW)
    assert updates == []
    assert adapter.calls == []
    assert stats["funding_replay_candidates"] == 0
    assert stats["funding_replay_skipped_not_prospective"] == 1


def test_unresolved_boundary_stays_partial_without_source_call():
    p = position(
        last_checked_bar_time=None,
        timeframe="unknown",
        funding_attribution_close_time=None,
    )
    adapter = Adapter()
    updates, stats = re_enrich_closed_positions_funding([p], adapter, now=NOW)
    assert updates == []
    assert adapter.calls == []
    assert stats["funding_replay_unresolved_close_boundary"] == 1
    assert (
        stats["funding_replay_reason_breakdown"]["CLOSE_BOUNDARY_UNRESOLVED"]
        == 1
    )


def test_one_public_query_per_symbol_and_terminal_facts_are_immutable():
    a = position(
        position_id="A",
        funding_attribution_close_time="2026-08-20T04:00:00+00:00",
    )
    b = position(
        position_id="B",
        opened_at="2026-08-20T02:00:00+00:00",
        funding_attribution_close_time="2026-08-20T05:00:00+00:00",
    )
    adapter = Adapter(
        [
            event("2026-08-20T00:00:00+00:00"),
            event("2026-08-20T08:00:00+00:00"),
        ]
    )
    updates, _ = re_enrich_closed_positions_funding([a, b], adapter, now=NOW)
    assert len(adapter.calls) == 1
    assert len(updates) == 2
    protected = [
        "status",
        "entry_price",
        "exit_price",
        "realized_pnl",
        "realized_pnl_pct",
        "r_multiple",
        "opened_at",
        "signal_key",
        "gap_execution_reference_price",
    ]
    originals = {item["position_id"]: item for item in (a, b)}
    for enriched in updates:
        original = originals[enriched["position_id"]]
        for key in protected:
            assert enriched.get(key) == original.get(key)


def test_terminal_canonical_selection_allows_only_monotonic_funding_evidence():
    old = position(funding_attribution_close_time="2026-08-20T04:00:00+00:00")
    new = copy.deepcopy(old)
    new.update(
        {
            "funding_events_verified_complete": True,
            "funding_replay_version": "closed_funding_replay_v1",
            "recorded_at": "2026-08-20T12:01:00+00:00",
            "_fp": "replayfp",
        }
    )
    selected = select_canonical_position_state(old, new)
    assert selected.selected is new
    assert selected.conflict is False

    regression = copy.deepcopy(new)
    regression["funding_events_verified_complete"] = False
    selected = select_canonical_position_state(new, regression)
    assert selected.selected is new
    assert selected.conflict is False

    tampered = copy.deepcopy(new)
    tampered["realized_pnl"] = 999.0
    selected = select_canonical_position_state(old, tampered)
    assert selected.selected is old
    assert selected.conflict is True
    assert selected.conflict_reason == "terminal_field_change"


def test_replay_fingerprint_is_stable_and_second_pass_is_noop_after_promotion():
    p = position(funding_attribution_close_time="2026-08-20T04:00:00+00:00")
    adapter = Adapter(
        [
            event("2026-08-20T00:00:00+00:00"),
            event("2026-08-20T08:00:00+00:00"),
        ]
    )
    first, _ = re_enrich_closed_positions_funding([p], adapter, now=NOW)
    assert len(first) == 1
    fp1 = funding_replay_record_fingerprint(first[0])
    fp2 = funding_replay_record_fingerprint(
        {**first[0], "recorded_at": "later", "_fp": "different"}
    )
    assert fp1 == fp2

    second_adapter = Adapter(adapter.events)
    second, stats = re_enrich_closed_positions_funding(
        first, second_adapter, now=NOW
    )
    assert second == []
    assert second_adapter.calls == []
    assert stats["funding_replay_skipped_already_complete"] == 1


def test_runner_threads_canonical_terminal_positions_and_same_public_adapter(
    tmp_path, monkeypatch
):
    from scripts import run_paper_position_simulator as runner

    terminal = position(
        funding_attribution_close_time="2026-08-20T04:00:00+00:00"
    )
    spy_adapter = Adapter()
    captured = {}

    class Result:
        def to_dict(self):
            return {
                "date": "2026-08-20",
                "mode": "public_readonly_update",
                "position_count": 0,
                "status_counts": {
                    "OPEN": 0,
                    "TAKE_PROFIT_HIT": 0,
                    "STOP_LOSS_HIT": 0,
                    "TIMEOUT_EXIT": 0,
                    "INVALID": 0,
                },
                "positions": [],
                "summary": {},
                "lifecycle_stats": {},
                "safety_flags": [],
            }

    def fake_load(output_dir, date_str):
        del output_dir, date_str
        return [], [terminal], set(), {"canonical_open_count_before_new_entries": 0}

    def fake_replay(canonical, adapter):
        captured["canonical"] = canonical
        captured["adapter"] = adapter
        completed = copy.deepcopy(terminal)
        completed["funding_events_verified_complete"] = True
        completed["funding_replay_version"] = "closed_funding_replay_v1"
        return [completed], {
            "funding_replay_candidates": 1,
            "funding_replay_completed": 1,
            "funding_replay_still_partial": 0,
        }

    input_path = tmp_path / "intents.json"
    input_path.write_text(json.dumps({"intents": []}))
    monkeypatch.setattr(runner, "_load_entry_guard_state", fake_load)
    monkeypatch.setattr(
        runner, "BinancePublicKlineAdapter", lambda config: spy_adapter
    )
    monkeypatch.setattr(
        runner,
        "simulate_existing_positions_update_only",
        lambda *args, **kwargs: Result(),
    )
    monkeypatch.setattr(
        runner, "re_enrich_closed_positions_funding", fake_replay
    )
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "run_paper_position_simulator.py",
            "--input-file",
            str(input_path),
            "--output-dir",
            str(tmp_path),
            "--date",
            "2026-08-20",
            "--allow-public-http",
            "--update-with-klines",
            "--update-existing-only",
        ],
    )

    assert runner.main() == 0
    assert captured["canonical"] == [terminal]
    assert captured["adapter"] is spy_adapter
    ledger = (
        tmp_path / "2026-08-20_paper_position_ledger.jsonl"
    ).read_text().splitlines()
    assert len(ledger) == 1
    record = json.loads(ledger[0])
    assert record["funding_events_verified_complete"] is True
    assert record["_fp"] == funding_replay_record_fingerprint(record)
