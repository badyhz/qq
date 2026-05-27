"""T902 — tests for 500 backlog task factory.

Deterministic. No I/O. No timestamps. No random.
"""

from core.prd_500_backlog_task_factory import (
    LIVE_AUTHORIZATION_PHRASES,
    build_default_500_task_factory_config,
    generate_prd_500_backlog_tasks,
    generate_tasks_for_domain,
    summarize_generated_tasks,
    task_factory_config_to_dict,
)
from core.prd_500_backlog_domain_catalog import build_prd_500_backlog_domain_catalog


class TestTaskFactory:
    def test_generates_500_plus_tasks(self):
        tasks = generate_prd_500_backlog_tasks()
        assert len(tasks) >= 550

    def test_sequential_ids(self):
        tasks = generate_prd_500_backlog_tasks()
        for i, t in enumerate(tasks):
            expected = f"T{901 + i}"
            assert t.task_id == expected, f"Expected {expected}, got {t.task_id}"

    def test_no_duplicates(self):
        tasks = generate_prd_500_backlog_tasks()
        ids = [t.task_id for t in tasks]
        assert len(ids) == len(set(ids))

    def test_frozen_not_executable(self):
        tasks = generate_prd_500_backlog_tasks()
        domains = build_prd_500_backlog_domain_catalog()
        frozen_ids = {d.domain_id for d in domains if d.default_risk_level == "FROZEN"}
        for t in tasks:
            if t.milestone_id in frozen_ids:
                assert t.status == "HUMAN_REVIEW_REQUIRED", (
                    f"Frozen task {t.task_id} should be HUMAN_REVIEW_REQUIRED, got {t.status}"
                )
                assert t.acceptance_command_ids == [], (
                    f"Frozen task {t.task_id} should have no acceptance commands"
                )

    def test_no_live_authorization(self):
        tasks = generate_prd_500_backlog_tasks()
        for t in tasks:
            combined = t.title.lower() + " " + " ".join(n.lower() for n in t.notes)
            for phrase in LIVE_AUTHORIZATION_PHRASES:
                assert phrase not in combined, (
                    f"Task {t.task_id} contains forbidden phrase: {phrase!r}"
                )

    def test_deterministic(self):
        a = generate_prd_500_backlog_tasks()
        b = generate_prd_500_backlog_tasks()
        assert len(a) == len(b)
        for ta, tb in zip(a, b):
            assert ta.task_id == tb.task_id
            assert ta.title == tb.title
            assert ta.status == tb.status
            assert ta.risk_level == tb.risk_level
            assert ta.milestone_id == tb.milestone_id
            assert ta.wave_id == tb.wave_id
            assert ta.batch_id == tb.batch_id
            assert ta.dependencies == tb.dependencies
            assert ta.acceptance_command_ids == tb.acceptance_command_ids
            assert ta.notes == tb.notes

    def test_dependency_acyclic(self):
        tasks = generate_prd_500_backlog_tasks()
        task_map = {t.task_id: t for t in tasks}
        for t in tasks:
            visited = set()
            current = t.task_id
            while current:
                assert current not in visited, f"Cycle detected at {current}"
                visited.add(current)
                deps = task_map[current].dependencies
                current = deps[0] if deps else None


class TestTaskFactoryHelpers:
    def test_default_config(self):
        cfg = build_default_500_task_factory_config()
        assert cfg.start_task_number == 901
        assert cfg.target_task_count == 550
        assert cfg.default_status == "NOT_STARTED"

    def test_config_to_dict(self):
        cfg = build_default_500_task_factory_config()
        d = task_factory_config_to_dict(cfg)
        assert d["start_task_number"] == 901
        assert d["target_task_count"] == 550
        assert d["default_status"] == "NOT_STARTED"
        assert isinstance(d["notes"], list)

    def test_summarize_generated_tasks(self):
        tasks = generate_prd_500_backlog_tasks()
        summary = summarize_generated_tasks(tasks)
        assert summary["total_tasks"] >= 550
        assert summary["min_task_number"] == 901
        assert summary["unique_task_ids"] == summary["total_tasks"]
        assert "HUMAN_REVIEW_REQUIRED" in summary["status_counts"]

    def test_generate_for_single_domain(self):
        domains = build_prd_500_backlog_domain_catalog()
        tasks = generate_tasks_for_domain(domains[0], 901, 5)
        assert len(tasks) == 5
        assert tasks[0].task_id == "T901"
        assert tasks[4].task_id == "T905"
        assert tasks[0].dependencies == []
        assert tasks[1].dependencies == ["T901"]

    def test_non_frozen_has_pytest(self):
        tasks = generate_prd_500_backlog_tasks()
        domains = build_prd_500_backlog_domain_catalog()
        non_frozen_ids = {d.domain_id for d in domains if d.default_risk_level != "FROZEN"}
        for t in tasks:
            if t.milestone_id in non_frozen_ids:
                assert t.acceptance_command_ids == ["pytest"]
