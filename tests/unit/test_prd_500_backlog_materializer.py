"""T903 — tests for 500 backlog materializer.

Deterministic. No I/O. No timestamps. No random.
"""

from core.prd_500_backlog_materializer import (
    assert_prd_500_backlog_safety,
    materialize_prd_500_backlog,
    materialized_500_backlog_to_dict,
    summarize_prd_500_backlog,
)


class TestMaterializer:
    def test_materializes_500_plus(self):
        backlog = materialize_prd_500_backlog()
        assert len(backlog.items) >= 550

    def test_summary_deterministic(self):
        backlog = materialize_prd_500_backlog()
        s1 = summarize_prd_500_backlog(backlog)
        s2 = summarize_prd_500_backlog(backlog)
        assert s1 == s2

    def test_safety_assertions_clean(self):
        backlog = materialize_prd_500_backlog()
        issues = assert_prd_500_backlog_safety(backlog)
        assert issues == []

    def test_rejects_unsafe_injection(self):
        from core.prd_backlog_schema import build_backlog_item

        backlog = materialize_prd_500_backlog()

        # Inject a malicious item
        bad_item = build_backlog_item(
            task_id="T99999",
            title="Backdoor — authorized for live trading",
            milestone_id="INJECT",
            wave_id="INJECT-W0",
            batch_id="INJECT-W0-B0",
            risk_level="LOW",
            status="NOT_STARTED",
            dependencies=[],
            allowed_file_patterns=["*"],
            forbidden_file_patterns=[],
            acceptance_command_ids=[],
            notes=["also authorized for real order placement"],
        )

        # Build a new backlog with the bad item injected
        from core.prd_backlog_schema import PrdBacklog

        tainted = PrdBacklog(
            backlog_id=backlog.backlog_id,
            items=list(backlog.items) + [bad_item],
            total_expected_tasks=backlog.total_expected_tasks,
            status=backlog.status,
            notes=list(backlog.notes),
        )

        issues = assert_prd_500_backlog_safety(tainted)
        assert len(issues) >= 3  # title phrase + note phrase + non-sequential id

    def test_serializer_deterministic(self):
        backlog = materialize_prd_500_backlog()
        d1 = materialized_500_backlog_to_dict(backlog)
        d2 = materialized_500_backlog_to_dict(backlog)
        assert d1 == d2
