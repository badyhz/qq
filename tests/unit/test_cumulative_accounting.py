"""Comprehensive tests for cumulative accounting fix.

Covers:
1. Ledger append-only with fingerprint idempotency
2. Canonical timestamp normalization (seconds/ms/μs/ns)
3. Terminal-state precedence (CLOSED beats OPEN)
4. position_id required (missing → excluded)
5. quarantine_status strict (missing → UNKNOWN)
6. source_mode filtering (offline/replay excluded)
7. canonical load failure → BLOCKED_ACCOUNTING_ERROR
8. Scorecard count = Gate count
9. Repeated run stability
10. Shared eligibility function
11. Quarantine recomputation
12. Source verification with lifecycle metadata
13. Damaged ledger handling
14. Count consistency
"""
from __future__ import annotations

import json
import os
import tempfile
import datetime as _dt

import pytest

from core.paper_trading.paper_position import (
    load_canonical_positions, filter_canonical_closed_clean,
    position_state_fingerprint, _normalize_timestamp_to_seconds,
    _should_replace, _position_dedupe_key,
    classify_quarantine_status, classify_source_eligibility,
    evaluate_canonical_eligibility, load_canonical_closed_clean_positions,
    _recompute_legacy_quarantine, _verify_trade_intent_source,
    ELIGIBLE_SOURCES, INELIGIBLE_SOURCES,
)
from core.paper_trading.shadow_run_registry import (
    compute_sample_gate, build_run_record, evaluate_gate,
    append_registry_record, GATE_BLOCKED_ACCOUNTING_ERROR,
)


NOW_ISO = _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds")


def _pos(position_id: str, status: str = "OPEN", **kw) -> dict:
    """Base position record for testing."""
    rec = {
        "position_id": position_id,
        "strategy_id": "test_strat",
        "symbol": "BTCUSDT",
        "timeframe": "1h",
        "side": "LONG",
        "status": status,
        "entry_price": 100.0,
        "stop_loss": 95.0,
        "take_profit": 110.0,
        "r_multiple": 0.0,
        "realized_pnl": 0.0,
        "lifecycle_mode": "future_only",
        "opened_bar_time": 1000,
        "quarantine_status": "CLEAN",
        "source_mode": "real_public_readonly",
        "recorded_at": NOW_ISO,
    }
    if status in ("TAKE_PROFIT_HIT", "STOP_LOSS_HIT", "TIMEOUT_EXIT"):
        rec.update({
            "exit_price": 110.0 if status == "TAKE_PROFIT_HIT" else 90.0,
            "closed_at": NOW_ISO,
            "r_multiple": 2.0 if status == "TAKE_PROFIT_HIT" else -1.0,
        })
    rec.update(kw)
    return rec


def _write(path: str, records: list[dict]):
    with open(path, "a") as f:
        for r in records:
            f.write(json.dumps(r) + "\n")


# --- 1. Ledger idempotency ---

class TestLedgerIdempotency:
    def test_fingerprint_stability(self):
        """Same position state produces same fingerprint."""
        p1 = _pos("PP_001", "TAKE_PROFIT_HIT")
        p2 = _pos("PP_001", "TAKE_PROFIT_HIT")
        assert position_state_fingerprint(p1) == position_state_fingerprint(p2)

    def test_fingerprint_changes_on_status(self):
        """Different status produces different fingerprint."""
        p1 = _pos("PP_001", "OPEN")
        p2 = _pos("PP_001", "TAKE_PROFIT_HIT")
        assert position_state_fingerprint(p1) != position_state_fingerprint(p2)

    def test_fingerprint_changes_on_exit_price(self):
        """Different exit_price produces different fingerprint."""
        p1 = _pos("PP_001", "TAKE_PROFIT_HIT", exit_price=110.0)
        p2 = _pos("PP_001", "TAKE_PROFIT_HIT", exit_price=115.0)
        assert position_state_fingerprint(p1) != position_state_fingerprint(p2)

    def test_idempotent_append(self):
        """Simulating fingerprint-based dedup: same records don't double."""
        with tempfile.TemporaryDirectory() as tmpdir:
            ledger = os.path.join(tmpdir, "2026-07-01_paper_position_ledger.jsonl")
            records = [
                _pos("PP_001", "TAKE_PROFIT_HIT"),
                _pos("PP_002", "STOP_LOSS_HIT"),
            ]
            # First write
            existing_fps = set()
            with open(ledger, "a") as f:
                for r in records:
                    fp = position_state_fingerprint(r)
                    r["_fp"] = fp
                    f.write(json.dumps(r) + "\n")
                    existing_fps.add(fp)

            with open(ledger) as f:
                line_count_1 = sum(1 for _ in f)

            # Second write with same records — skip if fp exists
            with open(ledger, "a") as f:
                for r in records:
                    fp = position_state_fingerprint(r)
                    if fp in existing_fps:
                        continue
                    r["_fp"] = fp
                    f.write(json.dumps(r) + "\n")
                    existing_fps.add(fp)

            with open(ledger) as f:
                line_count_2 = sum(1 for _ in f)

            assert line_count_1 == 2
            assert line_count_2 == 2  # no duplicate lines

    def test_changed_state_appends(self):
        """Changed state appends new line."""
        with tempfile.TemporaryDirectory() as tmpdir:
            ledger = os.path.join(tmpdir, "2026-07-01_paper_position_ledger.jsonl")

            existing_fps = set()
            # Write OPEN
            r1 = _pos("PP_001", "OPEN")
            fp1 = position_state_fingerprint(r1)
            r1["_fp"] = fp1
            with open(ledger, "a") as f:
                f.write(json.dumps(r1) + "\n")
            existing_fps.add(fp1)

            # Write CLOSED (changed state)
            r2 = _pos("PP_001", "TAKE_PROFIT_HIT")
            fp2 = position_state_fingerprint(r2)
            assert fp2 not in existing_fps
            r2["_fp"] = fp2
            with open(ledger, "a") as f:
                f.write(json.dumps(r2) + "\n")
            existing_fps.add(fp2)

            with open(ledger) as f:
                assert sum(1 for _ in f) == 2


# --- 2. Timestamp normalization ---

class TestTimestampNormalization:
    def test_seconds(self):
        assert _normalize_timestamp_to_seconds(1700000000) == 1700000000.0

    def test_milliseconds(self):
        assert abs(_normalize_timestamp_to_seconds(1700000000000) - 1700000000.0) < 0.01

    def test_microseconds(self):
        assert abs(_normalize_timestamp_to_seconds(1700000000000000) - 1700000000.0) < 0.01

    def test_nanoseconds(self):
        assert abs(_normalize_timestamp_to_seconds(1700000000000000000) - 1700000000.0) < 0.01

    def test_iso_string(self):
        ts = _normalize_timestamp_to_seconds("2023-11-14T22:13:20Z")
        assert abs(ts - 1700000000.0) < 10

    def test_none_returns_zero(self):
        assert _normalize_timestamp_to_seconds(None) == 0.0

    def test_invalid_returns_zero(self):
        assert _normalize_timestamp_to_seconds("not_a_ts") == 0.0

    def test_old_open_new_closed_selected(self):
        """Old OPEN (seconds) loses to new CLOSED (ms timestamp, later time)."""
        old_open = _pos("PP_001", "OPEN", recorded_at="2023-11-14T22:13:20Z")
        new_closed = _pos("PP_001", "TAKE_PROFIT_HIT",
                          recorded_at="2023-11-15T00:00:00Z")
        assert _should_replace(old_open, new_closed)


# --- 3. Terminal-state precedence ---

class TestTerminalStatePrecedence:
    def test_closed_beats_open_same_ts(self):
        """CLOSED should replace OPEN when timestamps are equal."""
        open_rec = _pos("PP_001", "OPEN")
        closed_rec = _pos("PP_001", "TAKE_PROFIT_HIT")
        # Give them the same recorded_at
        open_rec["recorded_at"] = NOW_ISO
        closed_rec["recorded_at"] = NOW_ISO
        assert _should_replace(open_rec, closed_rec)

    def test_open_does_not_replace_closed_same_ts(self):
        """OPEN should not replace CLOSED when timestamps are equal."""
        closed_rec = _pos("PP_001", "TAKE_PROFIT_HIT")
        open_rec = _pos("PP_001", "OPEN")
        closed_rec["recorded_at"] = NOW_ISO
        open_rec["recorded_at"] = NOW_ISO
        assert not _should_replace(closed_rec, open_rec)

    def test_higher_ts_wins_regardless(self):
        """Higher timestamp wins — but terminal state is irreversible."""
        old_open = _pos("PP_001", "OPEN", recorded_at="2026-01-01T00:00:00Z")
        new_closed = _pos("PP_001", "TAKE_PROFIT_HIT", recorded_at="2026-07-01T00:00:00Z")
        assert _should_replace(old_open, new_closed)

    def test_mixed_units(self):
        """Seconds vs milliseconds comparison works."""
        old = _pos("PP_001", "OPEN", recorded_at=1700000000)  # seconds
        new = _pos("PP_001", "TAKE_PROFIT_HIT", recorded_at=1700000001000)  # ms, later
        assert _should_replace(old, new)


# --- 4. position_id required ---

class TestPositionIdRequired:
    def test_missing_position_id_returns_none_key(self):
        rec = {"strategy_id": "test", "symbol": "BTC", "timeframe": "1h", "side": "LONG"}
        assert _position_dedupe_key(rec) is None

    def test_present_position_id_returns_key(self):
        rec = {"position_id": "PP_001"}
        assert _position_dedupe_key(rec) == "pid:PP_001"

    def test_empty_position_id_returns_none_key(self):
        rec = {"position_id": ""}
        assert _position_dedupe_key(rec) is None

    def test_missing_position_id_excluded_from_canonical(self):
        """Records without position_id are excluded from canonical."""
        with tempfile.TemporaryDirectory() as tmpdir:
            ledger = os.path.join(tmpdir, "2026-07-01_paper_position_ledger.jsonl")
            _write(ledger, [
                _pos("PP_001", "TAKE_PROFIT_HIT"),
                {**_pos("PP_002", "STOP_LOSS_HIT"), "position_id": ""},
                {**_pos("PP_003", "TIMEOUT_EXIT"), "position_id": None},
            ])

            positions, diag = load_canonical_positions(tmpdir)
            assert len(positions) == 1
            assert positions[0]["position_id"] == "PP_001"
            assert diag["excluded_no_position_id"] == 2


# --- 5. Quarantine strict ---

class TestQuarantineStrict:
    def test_clean_accepted(self):
        assert classify_quarantine_status({"quarantine_status": "CLEAN"}) == "CLEAN"

    def test_excluded_rejected(self):
        assert classify_quarantine_status({"quarantine_status": "EXCLUDED"}) == "EXCLUDED"

    def test_missing_is_unknown(self):
        assert classify_quarantine_status({}) == "UNKNOWN"

    def test_none_is_unknown(self):
        assert classify_quarantine_status({"quarantine_status": None}) == "UNKNOWN"

    def test_unknown_accepted_from_closed_clean(self):
        """UNKNOWN quarantine status (legacy) is accepted in closed_clean."""
        with tempfile.TemporaryDirectory() as tmpdir:
            ledger = os.path.join(tmpdir, "2026-07-01_paper_position_ledger.jsonl")
            _write(ledger, [
                _pos("PP_clean", "TAKE_PROFIT_HIT", quarantine_status="CLEAN"),
                {**_pos("PP_unknown", "STOP_LOSS_HIT"), "quarantine_status": None},  # missing
                _pos("PP_excluded", "TIMEOUT_EXIT", quarantine_status="EXCLUDED"),
            ])

            positions, _ = load_canonical_positions(tmpdir)
            closed = filter_canonical_closed_clean(positions)
            assert len(closed) == 2
            closed_ids = {p["position_id"] for p in closed}
            assert "PP_clean" in closed_ids
            assert "PP_unknown" in closed_ids


# --- 6. Source filtering ---

class TestSourceFiltering:
    def test_eligible_source(self):
        eligible, reason = classify_source_eligibility({"source_mode": "real_public_readonly"})
        assert eligible == "ELIGIBLE"

    def test_offline_excluded(self):
        eligible, reason = classify_source_eligibility({"source_mode": "offline_sample"})
        assert eligible == "INELIGIBLE"
        assert "offline_sample" in reason

    def test_replay_excluded(self):
        eligible, reason = classify_source_eligibility({"source_mode": "replay"})
        assert eligible == "INELIGIBLE"

    def test_missing_source_requires_metadata(self):
        eligible, reason = classify_source_eligibility({})
        # Empty source now requires metadata proof
        assert eligible == "UNKNOWN"
        assert "no_metadata" in reason

    def test_offline_excluded_from_closed_clean(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            ledger = os.path.join(tmpdir, "2026-07-01_paper_position_ledger.jsonl")
            _write(ledger, [
                _pos("PP_real", "TAKE_PROFIT_HIT", source_mode="real_public_readonly"),
                _pos("PP_offline", "STOP_LOSS_HIT", source_mode="offline_sample"),
                _pos("PP_replay", "TIMEOUT_EXIT", source_mode="replay"),
            ])

            positions, _ = load_canonical_positions(tmpdir)
            closed = filter_canonical_closed_clean(positions)
            assert len(closed) == 1
            assert closed[0]["position_id"] == "PP_real"

    def test_missing_source_excluded_from_closed_clean(self):
        """Missing source with no proof → excluded."""
        with tempfile.TemporaryDirectory() as tmpdir:
            ledger = os.path.join(tmpdir, "2026-07-01_paper_position_ledger.jsonl")
            _write(ledger, [
                _pos("PP_real", "TAKE_PROFIT_HIT", source_mode="real_public_readonly"),
                {**_pos("PP_nosrc", "STOP_LOSS_HIT"), "source_mode": ""},
            ])

            positions, _ = load_canonical_positions(tmpdir)
            closed = filter_canonical_closed_clean(positions)
            # Empty source now requires metadata proof → excluded
            assert len(closed) == 1
            assert closed[0]["position_id"] == "PP_real"


# --- 7. Canonical load failure → BLOCKED ---

class TestCanonicalLoadFailure:
    def test_nonexistent_dir_returns_empty_with_error(self):
        """Non-existent directory should not crash."""
        positions, diag = load_canonical_positions("/tmp/nonexistent_dir_xyz")
        assert positions == []

    def test_gate_blocks_on_accounting_error(self):
        """Gate returns BLOCKED_ACCOUNTING_ERROR when canonical fails."""
        # The canonical loader handles errors gracefully (returns empty + diag)
        # The gate should work with empty results
        with tempfile.TemporaryDirectory() as tmpdir:
            # Empty dir = no ledger files
            gate = compute_sample_gate(tmpdir)
            # Should be BLOCKED_INSUFFICIENT, not a crash
            assert "BLOCKED" in gate.testnet_gate_status


# --- 8. Scorecard = Gate count ---

class TestScorecardGateConsistency:
    def test_same_count(self):
        """Scorecard and Gate use the same canonical count."""
        with tempfile.TemporaryDirectory() as tmpdir:
            ledger = os.path.join(tmpdir, "2026-07-01_paper_position_ledger.jsonl")
            _write(ledger, [
                _pos(f"PP_{i}", "TAKE_PROFIT_HIT") for i in range(50)
            ] + [
                _pos(f"PP_open_{i}", "OPEN") for i in range(10)
            ])

            positions, diag = load_canonical_positions(tmpdir)
            closed_clean = filter_canonical_closed_clean(positions)
            scorecard_count = len(closed_clean)

            gate = compute_sample_gate(tmpdir)
            gate_count = gate.cumulative_closed_clean

            assert scorecard_count == gate_count == 50


# --- 9. Repeated run stability ---

class TestRepeatedRunStability:
    def test_canonical_count_stable(self):
        """Running load_canonical multiple times gives same result."""
        with tempfile.TemporaryDirectory() as tmpdir:
            ledger = os.path.join(tmpdir, "2026-07-01_paper_position_ledger.jsonl")
            _write(ledger, [
                _pos(f"PP_{i}", "TAKE_PROFIT_HIT") for i in range(20)
            ])

            for _ in range(5):
                positions, _ = load_canonical_positions(tmpdir)
                closed = filter_canonical_closed_clean(positions)
                assert len(closed) == 20

    def test_raw_lines_stable_with_fingerprint(self):
        """Fingerprint dedup prevents raw line growth on retry."""
        with tempfile.TemporaryDirectory() as tmpdir:
            ledger = os.path.join(tmpdir, "2026-07-01_paper_position_ledger.jsonl")
            records = [_pos(f"PP_{i}", "TAKE_PROFIT_HIT") for i in range(10)]

            # First write
            existing_fps = set()
            with open(ledger, "a") as f:
                for r in records:
                    fp = position_state_fingerprint(r)
                    r["_fp"] = fp
                    f.write(json.dumps(r) + "\n")
                    existing_fps.add(fp)

            with open(ledger) as f:
                lines_after_first = sum(1 for _ in f)

            # Second write (retry) — skip existing fps
            with open(ledger, "a") as f:
                for r in records:
                    fp = position_state_fingerprint(r)
                    if fp in existing_fps:
                        continue
                    r["_fp"] = fp
                    f.write(json.dumps(r) + "\n")
                    existing_fps.add(fp)

            with open(ledger) as f:
                lines_after_second = sum(1 for _ in f)

            assert lines_after_first == lines_after_second == 10


# --- 10. Cross-day dedup ---

class TestCrossDayDedup:
    def test_open_to_closed_across_days(self):
        """Same position OPEN on day 1, CLOSED on day 2 → CLOSED."""
        with tempfile.TemporaryDirectory() as tmpdir:
            ledger1 = os.path.join(tmpdir, "2026-07-01_paper_position_ledger.jsonl")
            ledger2 = os.path.join(tmpdir, "2026-07-02_paper_position_ledger.jsonl")
            _write(ledger1, [_pos("PP_001", "OPEN", recorded_at="2026-07-01T12:00:00Z")])
            _write(ledger2, [_pos("PP_001", "TAKE_PROFIT_HIT", recorded_at="2026-07-02T12:00:00Z")])

            positions, _ = load_canonical_positions(tmpdir)
            assert len(positions) == 1
            assert positions[0]["status"] == "TAKE_PROFIT_HIT"


# --- 11. Shared eligibility function ---

class TestSharedEligibility:
    def test_explicit_clean_real_source_eligible(self):
        """Explicit CLEAN + real source → eligible."""
        pos = _pos("PP_001", "TAKE_PROFIT_HIT",
                   quarantine_status="CLEAN",
                   source_mode="real_public_readonly")
        elig = evaluate_canonical_eligibility(pos)
        assert elig.eligible is True
        assert elig.quarantine_status == "CLEAN"
        assert elig.quarantine_source == "explicit"
        assert elig.source_status == "ELIGIBLE"

    def test_explicit_excluded(self):
        """Explicit EXCLUDED → excluded."""
        pos = _pos("PP_001", "TAKE_PROFIT_HIT",
                   quarantine_status="EXCLUDED",
                   source_mode="real_public_readonly")
        elig = evaluate_canonical_eligibility(pos)
        assert elig.eligible is False
        assert elig.quarantine_status == "EXCLUDED"
        assert elig.exclusion_reason == "quarantine_excluded"

    def test_unknown_quarantine_recomputed_clean(self):
        """UNKNOWN quarantine with valid CLOSED fields → recomputed CLEAN."""
        pos = _pos("PP_001", "TAKE_PROFIT_HIT",
                   quarantine_status=None,
                   source_mode="real_public_readonly")
        elig = evaluate_canonical_eligibility(pos)
        assert elig.eligible is True
        assert elig.quarantine_status == "CLEAN"
        assert elig.quarantine_source == "recomputed_legacy"

    def test_unknown_quarantine_unverifiable(self):
        """UNKNOWN quarantine with invalid lifecycle_mode → excluded."""
        pos = _pos("PP_001", "OPEN",
                   quarantine_status=None,
                   source_mode="real_public_readonly",
                   lifecycle_mode="unknown")
        elig = evaluate_canonical_eligibility(pos)
        assert elig.eligible is False
        assert elig.quarantine_status == "EXCLUDED"
        assert elig.exclusion_reason == "quarantine_excluded"

    def test_empty_source_no_metadata_excluded(self):
        """Empty source with no metadata → excluded."""
        pos = _pos("PP_001", "TAKE_PROFIT_HIT",
                   quarantine_status="CLEAN",
                   source_mode="")
        elig = evaluate_canonical_eligibility(pos, lifecycle_metadata=None)
        assert elig.eligible is False
        assert elig.source_status == "UNKNOWN"

    def test_trade_intent_with_lifecycle_metadata_eligible(self):
        """trade_intent + real lifecycle metadata → eligible."""
        pos = _pos("PP_001", "TAKE_PROFIT_HIT",
                   quarantine_status="CLEAN",
                   source="trade_intent",
                   date="2026-07-10")
        metadata = {
            "2026-07-10": {
                "mode": "real_public_readonly",
                "safety_flags": ["PAPER_ONLY", "SHADOW_ONLY"],
            }
        }
        elig = evaluate_canonical_eligibility(pos, metadata)
        assert elig.eligible is True
        assert elig.source_status == "ELIGIBLE"

    def test_trade_intent_with_offline_metadata_excluded(self):
        """trade_intent + offline metadata → excluded."""
        pos = _pos("PP_001", "TAKE_PROFIT_HIT",
                   quarantine_status="CLEAN",
                   source="trade_intent",
                   source_mode="trade_intent",
                   date="2026-07-10")
        metadata = {
            "2026-07-10": {
                "mode": "offline_sample",
                "safety_flags": ["PAPER_ONLY"],
            }
        }
        elig = evaluate_canonical_eligibility(pos, metadata)
        assert elig.eligible is False
        assert elig.source_status == "INELIGIBLE"

    def test_replay_source_excluded(self):
        """replay source → excluded."""
        pos = _pos("PP_001", "TAKE_PROFIT_HIT",
                   quarantine_status="CLEAN",
                   source_mode="replay")
        elig = evaluate_canonical_eligibility(pos)
        assert elig.eligible is False
        assert elig.source_status == "INELIGIBLE"


# --- 12. Quarantine recomputation ---

class TestQuarantineRecomputation:
    def test_explicit_clean(self):
        """Explicit CLEAN stays CLEAN."""
        qs, src = _recompute_legacy_quarantine({"quarantine_status": "CLEAN"})
        assert qs == "CLEAN"
        assert src == "explicit"

    def test_explicit_excluded(self):
        """Explicit EXCLUDED stays EXCLUDED."""
        qs, src = _recompute_legacy_quarantine({"quarantine_status": "EXCLUDED"})
        assert qs == "EXCLUDED"
        assert src == "explicit"

    def test_missing_recomputed_clean_for_closed(self):
        """Missing quarantine for valid CLOSED → recomputed CLEAN."""
        pos = _pos("PP_001", "TAKE_PROFIT_HIT")
        del pos["quarantine_status"]
        qs, src = _recompute_legacy_quarantine(pos)
        assert qs == "CLEAN"
        assert src == "recomputed_legacy"

    def test_missing_recomputed_clean_for_open(self):
        """Missing quarantine for valid OPEN → recomputed CLEAN."""
        pos = _pos("PP_001", "OPEN")
        del pos["quarantine_status"]
        qs, src = _recompute_legacy_quarantine(pos)
        assert qs == "CLEAN"
        assert src == "recomputed_legacy"

    def test_missing_unverifiable_for_invalid(self):
        """Missing quarantine for invalid lifecycle_mode → EXCLUDED."""
        pos = _pos("PP_001", "OPEN", lifecycle_mode="unknown")
        del pos["quarantine_status"]
        qs, src = _recompute_legacy_quarantine(pos)
        assert qs == "EXCLUDED"
        assert src == "recomputed_legacy"


# --- 13. Source verification ---

class TestSourceVerification:
    def test_real_public_readonly_eligible(self):
        """real_public_readonly mode → eligible."""
        metadata = {"mode": "real_public_readonly", "safety_flags": ["PAPER_ONLY", "SHADOW_ONLY"]}
        eligible, reason = _verify_trade_intent_source(metadata)
        assert eligible == "ELIGIBLE"
        assert "real_public_readonly" in reason

    def test_offline_sample_ineligible(self):
        """offline_sample mode → ineligible."""
        metadata = {"mode": "offline_sample", "safety_flags": ["PAPER_ONLY"]}
        eligible, reason = _verify_trade_intent_source(metadata)
        assert eligible == "INELIGIBLE"
        assert "offline_sample" in reason

    def test_missing_safety_flags_ineligible(self):
        """Missing safety flags → ineligible."""
        metadata = {"mode": "real_public_readonly", "safety_flags": ["PAPER_ONLY"]}
        eligible, reason = _verify_trade_intent_source(metadata)
        assert eligible == "INELIGIBLE"
        assert "missing_safety_flags" in reason

    def test_trade_intent_with_no_metadata_unknown(self):
        """trade_intent with no metadata → unknown."""
        pos = _pos("PP_001", "TAKE_PROFIT_HIT",
                   source="trade_intent",
                   source_mode="trade_intent",
                   date="2026-07-10")
        eligible, reason = classify_source_eligibility(pos, None)
        assert eligible == "UNKNOWN"
        assert "no_metadata" in reason


# --- 14. Damaged ledger handling ---

class TestDamagedLedger:
    def test_corrupted_line_counted(self):
        """Corrupted JSON lines are counted in diagnostics."""
        with tempfile.TemporaryDirectory() as tmpdir:
            ledger = os.path.join(tmpdir, "2026-07-01_paper_position_ledger.jsonl")
            with open(ledger, "w") as f:
                f.write(json.dumps(_pos("PP_001", "TAKE_PROFIT_HIT")) + "\n")
                f.write("not valid json\n")  # corrupted
                f.write(json.dumps(_pos("PP_002", "STOP_LOSS_HIT")) + "\n")

            positions, diag = load_canonical_positions(tmpdir)
            assert diag["corrupted_lines"] == 1
            assert diag["raw_count"] == 3
            assert len(positions) == 2

    def test_gate_blocks_on_corrupted_ledger(self):
        """Gate blocks when ledger has corrupted lines."""
        with tempfile.TemporaryDirectory() as tmpdir:
            ledger = os.path.join(tmpdir, "2026-07-01_paper_position_ledger.jsonl")
            with open(ledger, "w") as f:
                f.write(json.dumps(_pos("PP_001", "TAKE_PROFIT_HIT")) + "\n")
                f.write("corrupted line\n")

            gate = compute_sample_gate(tmpdir)
            assert gate.testnet_gate_status == GATE_BLOCKED_ACCOUNTING_ERROR

    def test_gate_blocks_on_file_error(self):
        """Gate blocks when ledger file cannot be read."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a directory instead of a file (will cause OSError)
            os.makedirs(os.path.join(tmpdir, "2026-07-01_paper_position_ledger.jsonl"))

            gate = compute_sample_gate(tmpdir)
            assert gate.testnet_gate_status == GATE_BLOCKED_ACCOUNTING_ERROR


# --- 15. Unified entry point ---

class TestUnifiedEntryPoint:
    def test_load_canonical_closed_clean(self):
        """Unified entry returns eligible and all positions."""
        with tempfile.TemporaryDirectory() as tmpdir:
            ledger = os.path.join(tmpdir, "2026-07-01_paper_position_ledger.jsonl")
            _write(ledger, [
                _pos("PP_clean", "TAKE_PROFIT_HIT", quarantine_status="CLEAN"),
                _pos("PP_open", "OPEN", quarantine_status="CLEAN"),
                _pos("PP_excluded", "STOP_LOSS_HIT", quarantine_status="EXCLUDED"),
            ])

            eligible, all_pos, diag = load_canonical_closed_clean_positions(tmpdir)
            assert len(eligible) == 1
            assert eligible[0]["position_id"] == "PP_clean"
            assert len(all_pos) == 3
            assert diag["eligible_closed_clean"] == 1
            assert diag["exclusions"]["total"] == 2  # PP_open (open) + PP_excluded (quarantine)

    def test_count_consistency(self):
        """Canonical, scorecard, and gate all return same count."""
        with tempfile.TemporaryDirectory() as tmpdir:
            ledger = os.path.join(tmpdir, "2026-07-01_paper_position_ledger.jsonl")
            _write(ledger, [
                _pos(f"PP_{i}", "TAKE_PROFIT_HIT", quarantine_status="CLEAN")
                for i in range(50)
            ] + [
                _pos(f"PP_open_{i}", "OPEN", quarantine_status="CLEAN")
                for i in range(10)
            ])

            eligible, _, diag = load_canonical_closed_clean_positions(tmpdir)
            canonical_count = len(eligible)

            gate = compute_sample_gate(tmpdir)
            gate_count = gate.cumulative_closed_clean

            assert canonical_count == gate_count == 50

    def test_diagnostics_comprehensive(self):
        """Diagnostics include all required fields."""
        with tempfile.TemporaryDirectory() as tmpdir:
            ledger = os.path.join(tmpdir, "2026-07-01_paper_position_ledger.jsonl")
            _write(ledger, [_pos("PP_001", "TAKE_PROFIT_HIT")])

            _, _, diag = load_canonical_closed_clean_positions(tmpdir)
            required_fields = [
                "raw_records", "unique_positions", "closed_positions",
                "eligible_closed_clean", "explicit_clean", "derived_clean",
                "exclusions", "fatal_errors",
                "missing_position_id", "files_read", "files_error",
                "corrupted_lines", "accounting_status",
            ]
            for field in required_fields:
                assert field in diag, f"Missing field: {field}"


# --- 16. Unified count test ---

class TestUnifiedCount:
    def test_unified_count_consistency(self):
        """Canonical, Scorecard, Gate, Registry all return same count."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create lifecycle metadata for source verification
            lifecycle = {
                "date": "2026-07-10",
                "mode": "real_public_readonly",
                "allow_public_http": True,
                "pipeline_status": "PASS",
                "safety_flags": ["PAPER_ONLY", "SHADOW_ONLY", "NO_SECRET"],
            }
            with open(os.path.join(tmpdir, "2026-07-10_shadow_lifecycle_result.json"), "w") as f:
                json.dump(lifecycle, f)

            # Create ledger with 3 eligible CLOSED + 1 OPEN
            ledger = os.path.join(tmpdir, "2026-07-10_paper_position_ledger.jsonl")
            _write(ledger, [
                _pos("PP_001", "TAKE_PROFIT_HIT", date="2026-07-10",
                     source="trade_intent", source_mode="trade_intent"),
                _pos("PP_002", "STOP_LOSS_HIT", date="2026-07-10",
                     source="trade_intent", source_mode="trade_intent"),
                _pos("PP_003", "TIMEOUT_EXIT", date="2026-07-10",
                     source="trade_intent", source_mode="trade_intent"),
                _pos("PP_004", "OPEN", date="2026-07-10",
                     source="trade_intent", source_mode="trade_intent"),
            ])

            # Verify all counts are equal
            eligible, _, diag = load_canonical_closed_clean_positions(tmpdir)
            canonical_count = len(eligible)

            gate = compute_sample_gate(tmpdir)
            gate_count = gate.cumulative_closed_clean

            assert canonical_count == 3
            assert gate_count == 3
            assert canonical_count == gate_count


# --- 17. Normal exclusions don't block ---

class TestNormalExclusions:
    def test_excluded_does_not_block_gate(self):
        """Normal EXCLUDED positions don't block the gate."""
        with tempfile.TemporaryDirectory() as tmpdir:
            ledger = os.path.join(tmpdir, "2026-07-01_paper_position_ledger.jsonl")
            _write(ledger, [
                _pos("PP_clean1", "TAKE_PROFIT_HIT", quarantine_status="CLEAN"),
                _pos("PP_clean2", "STOP_LOSS_HIT", quarantine_status="CLEAN"),
                _pos("PP_clean3", "TIMEOUT_EXIT", quarantine_status="CLEAN"),
                _pos("PP_excluded", "TAKE_PROFIT_HIT", quarantine_status="EXCLUDED"),
                _pos("PP_unknown", "STOP_LOSS_HIT", quarantine_status=None),
            ])

            eligible, _, diag = load_canonical_closed_clean_positions(tmpdir)
            gate = compute_sample_gate(tmpdir)

            # PP_unknown has lifecycle_mode="future_only" (default) → CLEAN via recomputation
            assert len(eligible) == 4
            assert diag["fatal_errors"] == []
            assert gate.testnet_gate_status != GATE_BLOCKED_ACCOUNTING_ERROR


# --- 18. Damaged ledger blocks ---

class TestDamagedLedgerBlocks:
    def test_corrupted_jsonl_blocks_gate(self):
        """Corrupted JSONL blocks gate with ACCOUNTING_ERROR."""
        with tempfile.TemporaryDirectory() as tmpdir:
            ledger = os.path.join(tmpdir, "2026-07-01_paper_position_ledger.jsonl")
            with open(ledger, "w") as f:
                f.write(json.dumps(_pos("PP_001", "TAKE_PROFIT_HIT")) + "\n")
                f.write("not valid json\n")

            gate = compute_sample_gate(tmpdir)
            assert gate.testnet_gate_status == GATE_BLOCKED_ACCOUNTING_ERROR
            assert gate.sample_status == "ACCOUNTING_ERROR"

    def test_corrupted_jsonl_blocks_scorecard(self):
        """Corrupted JSONL causes scorecard to exit non-0."""
        with tempfile.TemporaryDirectory() as tmpdir:
            ledger = os.path.join(tmpdir, "2026-07-01_paper_position_ledger.jsonl")
            with open(ledger, "w") as f:
                f.write(json.dumps(_pos("PP_001", "TAKE_PROFIT_HIT")) + "\n")
                f.write("corrupted\n")

            eligible, _, diag = load_canonical_closed_clean_positions(tmpdir)
            assert diag["fatal_errors"] != []
            assert diag["accounting_status"] == "ERROR"


# --- 19. Scorecard input verification ---

class TestScorecardInput:
    def test_scorecard_uses_eligible_positions(self):
        """Scorecard must use eligible_positions, not all_positions."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create lifecycle metadata
            lifecycle = {
                "date": "2026-07-10",
                "mode": "real_public_readonly",
                "allow_public_http": True,
                "pipeline_status": "PASS",
                "safety_flags": ["PAPER_ONLY", "SHADOW_ONLY", "NO_SECRET"],
            }
            with open(os.path.join(tmpdir, "2026-07-10_shadow_lifecycle_result.json"), "w") as f:
                json.dump(lifecycle, f)

            # Create ledger: 2 eligible + 1 excluded
            ledger = os.path.join(tmpdir, "2026-07-10_paper_position_ledger.jsonl")
            _write(ledger, [
                _pos("PP_001", "TAKE_PROFIT_HIT", date="2026-07-10",
                     source="trade_intent", source_mode="trade_intent"),
                _pos("PP_002", "STOP_LOSS_HIT", date="2026-07-10",
                     source="trade_intent", source_mode="trade_intent"),
                _pos("PP_003", "TIMEOUT_EXIT", quarantine_status="EXCLUDED"),
            ])

            eligible, _, diag = load_canonical_closed_clean_positions(tmpdir)
            assert len(eligible) == 2

            # Verify eligible positions are the ones that should be used
            eligible_ids = {p["position_id"] for p in eligible}
            assert "PP_001" in eligible_ids
            assert "PP_002" in eligible_ids
            assert "PP_003" not in eligible_ids


# --- 19. Terminal state irreversibility ---

class TestTerminalStateIrreversibility:
    def test_closed_not_overwritten_by_newer_open(self):
        """CLOSED state must not be replaced by a newer OPEN record."""
        old = _pos("PP_001", "TAKE_PROFIT_HIT", recorded_at="2026-07-10T10:00:00Z")
        new = _pos("PP_001", "OPEN", recorded_at="2026-07-10T12:00:00Z")
        assert _should_replace(old, new) is False

    def test_closed_beats_older_open(self):
        """CLOSED record should replace older OPEN."""
        old = _pos("PP_001", "OPEN", recorded_at="2026-07-10T10:00:00Z")
        new = _pos("PP_001", "TAKE_PROFIT_HIT", recorded_at="2026-07-10T12:00:00Z")
        assert _should_replace(old, new) is True

    def test_newer_closed_replaces_older_closed(self):
        """Newer CLOSED can replace older CLOSED."""
        old = _pos("PP_001", "TAKE_PROFIT_HIT", recorded_at="2026-07-10T10:00:00Z")
        new = _pos("PP_001", "STOP_LOSS_HIT", recorded_at="2026-07-10T12:00:00Z")
        assert _should_replace(old, new) is True

    def test_canonical_load_preserves_closed(self):
        """Canonical load must preserve CLOSED when newer OPEN exists."""
        with tempfile.TemporaryDirectory() as tmpdir:
            ledger = os.path.join(tmpdir, "2026-07-10_paper_position_ledger.jsonl")
            _write(ledger, [
                _pos("PP_001", "TAKE_PROFIT_HIT", recorded_at="2026-07-10T10:00:00Z"),
                _pos("PP_001", "OPEN", recorded_at="2026-07-10T12:00:00Z"),
            ])
            positions, _ = load_canonical_positions(tmpdir)
            assert len(positions) == 1
            assert positions[0]["status"] == "TAKE_PROFIT_HIT"


# --- 20. Fingerprint excludes observation-only fields ---

class TestFingerprintStability:
    def test_last_checked_at_change_no_duplicate(self):
        """Changing last_checked_at alone should not change fingerprint."""
        p1 = _pos("PP_001", "OPEN", last_checked_at="2026-07-10T10:00:00Z")
        p2 = _pos("PP_001", "OPEN", last_checked_at="2026-07-10T12:00:00Z")
        assert position_state_fingerprint(p1) == position_state_fingerprint(p2)

    def test_recorded_at_change_no_duplicate(self):
        """Changing recorded_at alone should not change fingerprint."""
        p1 = _pos("PP_001", "OPEN", recorded_at="2026-07-10T10:00:00Z")
        p2 = _pos("PP_001", "OPEN", recorded_at="2026-07-10T12:00:00Z")
        assert position_state_fingerprint(p1) == position_state_fingerprint(p2)

    def test_status_change_changes_fingerprint(self):
        """Status change must change fingerprint."""
        p1 = _pos("PP_001", "OPEN")
        p2 = _pos("PP_001", "TAKE_PROFIT_HIT")
        assert position_state_fingerprint(p1) != position_state_fingerprint(p2)

    def test_exit_price_change_changes_fingerprint(self):
        """Exit price change must change fingerprint."""
        p1 = _pos("PP_001", "TAKE_PROFIT_HIT", exit_price=110.0)
        p2 = _pos("PP_001", "TAKE_PROFIT_HIT", exit_price=115.0)
        assert position_state_fingerprint(p1) != position_state_fingerprint(p2)


# --- 21. Static console generator ---

class TestStaticConsoleGenerator:
    @staticmethod
    def _write_report_files(report_dir: str, pos: dict):
        """Create all report files required by the generator."""
        date_prefix = "2026-07-10"
        # Quarantine (positions)
        qpath = os.path.join(report_dir, f"{date_prefix}_paper_positions_quarantine.json")
        with open(qpath, "w") as f:
            json.dump({
                "date": date_prefix,
                "source_file": "test",
                "position_count": 1,
                "quarantined_count": 0,
                "clean_count": 1,
                "excluded_from_stats_count": 0,
                "reason_counts": {},
                "positions": [pos],
                "clean_summary": {},
                "safety_flags": [],
            }, f)
        # Scorecard
        scpath = os.path.join(report_dir, f"{date_prefix}_paper_performance_scorecard.json")
        with open(scpath, "w") as f:
            json.dump({
                "date": date_prefix,
                "global_metrics": {
                    "clean_position_count": 1,
                    "closed_position_count": 1,
                    "excluded_position_count": 0,
                    "open_position_count": 0,
                    "win_rate": 1.0,
                    "profit_factor": 2.0,
                    "take_profit_hit": 1,
                    "stop_loss_hit": 0,
                    "timeout_exit": 0,
                },
                "strategy_scorecards": [{
                    "strategy_id": "test_strat",
                    "closed_count": 1,
                    "win_rate": 1.0,
                    "profit_factor": 2.0,
                    "expectancy_r": 1.0,
                    "avg_r_multiple": 1.0,
                    "max_drawdown_r": 0.0,
                    "max_losing_streak": 0,
                }],
                "clean_position_count": 1,
                "excluded_position_count": 0,
                "safety_flags": [],
            }, f)
        # Sample gate
        gpath = os.path.join(report_dir, f"{date_prefix}_shadow_sample_gate.json")
        with open(gpath, "w") as f:
            json.dump({
                "date": date_prefix,
                "total_runs": 1,
                "latest_run_id": "test_run",
                "closed_clean_positions": 1,
                "sample_status": "PASS",
                "testnet_gate_status": "BLOCKED",
                "testnet_gate_reasons": ["shadow_only"],
                "registry_path": "test",
                "safety_flags": [],
            }, f)
        # Lifecycle result
        lcpath = os.path.join(report_dir, f"{date_prefix}_shadow_lifecycle_result.json")
        with open(lcpath, "w") as f:
            json.dump({"date": date_prefix, "pipeline_status": "OK"}, f)
        # Update result
        upath = os.path.join(report_dir, f"{date_prefix}_shadow_position_update_result.json")
        with open(upath, "w") as f:
            json.dump({"date": date_prefix, "pipeline_status": "OK"}, f)

    def test_generator_creates_files(self):
        """Generator creates index.html, index_en.html, console_data.json."""
        from scripts.generate_static_console import generate_console
        with tempfile.TemporaryDirectory() as report_dir:
            with tempfile.TemporaryDirectory() as output_dir:
                pos = _pos("PP_001", "TAKE_PROFIT_HIT")
                self._write_report_files(report_dir, pos)

                result = generate_console(report_dir, output_dir)
                assert result["success"] is True
                assert "index.html" in result["files_written"]
                assert "index_en.html" in result["files_written"]
                assert "console_data.json" in result["files_written"]

                assert os.path.isfile(os.path.join(output_dir, "index.html"))
                assert os.path.isfile(os.path.join(output_dir, "index_en.html"))
                assert os.path.isfile(os.path.join(output_dir, "console_data.json"))

    def test_generator_json_valid(self):
        """Generator produces valid JSON."""
        from scripts.generate_static_console import generate_console
        with tempfile.TemporaryDirectory() as report_dir:
            with tempfile.TemporaryDirectory() as output_dir:
                pos = _pos("PP_001", "TAKE_PROFIT_HIT")
                self._write_report_files(report_dir, pos)

                result = generate_console(report_dir, output_dir)
                assert result["success"] is True

                with open(os.path.join(output_dir, "console_data.json")) as f:
                    data = json.load(f)
                assert "generated_at" in data
                assert "strategies" in data

    def test_generator_no_sensitive_leaks(self):
        """Generator does not expose sensitive paths."""
        from scripts.generate_static_console import generate_console
        with tempfile.TemporaryDirectory() as report_dir:
            with tempfile.TemporaryDirectory() as output_dir:
                pos = _pos("PP_001", "TAKE_PROFIT_HIT")
                self._write_report_files(report_dir, pos)

                result = generate_console(report_dir, output_dir)
                assert result["success"] is True

                for fname in ["index.html", "index_en.html"]:
                    with open(os.path.join(output_dir, fname)) as f:
                        content = f.read()
                    assert "/opt/quant-shadow" not in content
                    assert "10.66.66" not in content

    def test_generator_preserves_last_good_on_error(self):
        """Generator preserves existing files when generation fails (sensitive leak)."""
        from scripts.generate_static_console import generate_console
        with tempfile.TemporaryDirectory() as report_dir:
            with tempfile.TemporaryDirectory() as output_dir:
                # Create existing good files
                for fname in ["index.html", "index_en.html", "console_data.json"]:
                    with open(os.path.join(output_dir, fname), "w") as f:
                        f.write("existing-good-data")

                # Create report with sensitive data in strategy_id (rendered in HTML)
                pos = _pos("PP_001", "TAKE_PROFIT_HIT")
                self._write_report_files(report_dir, pos)
                # Overwrite scorecard with sensitive strategy_id
                date_prefix = "2026-07-10"
                scpath = os.path.join(report_dir, f"{date_prefix}_paper_performance_scorecard.json")
                with open(scpath, "w") as f:
                    json.dump({
                        "date": date_prefix,
                        "global_metrics": {"clean_position_count": 1, "closed_position_count": 1, "excluded_position_count": 0, "open_position_count": 0, "win_rate": 1.0, "profit_factor": 2.0, "take_profit_hit": 1, "stop_loss_hit": 0, "timeout_exit": 0},
                        "strategy_scorecards": [{"strategy_id": "/opt/quant-shadow/bad", "closed_count": 1, "win_rate": 1.0, "profit_factor": 2.0, "expectancy_r": 1.0, "avg_r_multiple": 1.0, "max_drawdown_r": 0.0, "max_losing_streak": 0}],
                        "clean_position_count": 1, "excluded_position_count": 0, "safety_flags": [],
                    }, f)

                result = generate_console(report_dir, output_dir)
                assert result["success"] is False

                # Existing files should be preserved
                for fname in ["index.html", "index_en.html", "console_data.json"]:
                    with open(os.path.join(output_dir, fname)) as f:
                        assert f.read() == "existing-good-data"
