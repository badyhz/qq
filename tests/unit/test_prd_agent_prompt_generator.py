"""Tests for PRD agent prompt generator — T868."""

import pytest
from core.prd_task_model import PrdTask
from core.prd_agent_prompt_generator import (
    PrdAgentPrompt,
    generate_agent_prompt_for_task_range,
    prd_agent_prompt_to_dict,
    prd_agent_prompt_to_markdown,
)


# --- Fixtures ---


def _make_task(task_id: str, title: str = "Test Task", status: str = "NOT_STARTED") -> PrdTask:
    """Helper to create a minimal PrdTask."""
    return PrdTask(
        task_id=task_id,
        title=title,
        status=status,
        allowed_files=["core/foo.py", "tests/unit/test_foo.py"],
        dependencies=[],
        acceptance_commands=["python3 -m pytest tests/unit/test_foo.py -v"],
        risk_level="LOW",
        notes=[],
    )


TASKS = [_make_task("T100", "Task A"), _make_task("T101", "Task B")]
REQUIRED_DOCS = ["PROJECT_STATE.md", "TASKS.md", "acceptance.json"]


# --- Tests ---


class TestGenerateAgentPromptForTaskRange:
    """Tests for generate_agent_prompt_for_task_range."""

    def test_required_docs_in_prompt(self):
        """Prompt text includes all required docs."""
        prompt = generate_agent_prompt_for_task_range(TASKS, "T100", "T101", REQUIRED_DOCS)
        for doc in REQUIRED_DOCS:
            assert doc in prompt.prompt_text
        assert prompt.required_docs == REQUIRED_DOCS

    def test_hard_stop_in_prompt(self):
        """Prompt text includes hard stop instruction."""
        prompt = generate_agent_prompt_for_task_range(TASKS, "T100", "T101", REQUIRED_DOCS)
        assert "HARD STOP" in prompt.prompt_text
        assert "T101" in prompt.prompt_text
        assert prompt.hard_stop_task_id == "T101"

    def test_frozen_module_warning(self):
        """Prompt includes frozen module warning."""
        prompt = generate_agent_prompt_for_task_range(TASKS, "T100", "T101", REQUIRED_DOCS)
        assert "frozen" in prompt.prompt_text.lower()
        assert any("frozen" in w.lower() for w in prompt.safety_warnings)

    def test_no_live_submit_planner_secrets(self):
        """Prompt includes no-live/submit/planner/secrets warning."""
        prompt = generate_agent_prompt_for_task_range(TASKS, "T100", "T101", REQUIRED_DOCS)
        text = prompt.prompt_text.lower()
        assert "live trading" in text
        assert "submit" in text
        assert "planner" in text
        assert "secrets" in text
        assert "exchange" in text
        assert "runtime execution" in text

    def test_deterministic_output(self):
        """Same inputs produce identical output."""
        p1 = generate_agent_prompt_for_task_range(TASKS, "T100", "T101", REQUIRED_DOCS)
        p2 = generate_agent_prompt_for_task_range(TASKS, "T100", "T101", REQUIRED_DOCS)
        assert p1 == p2
        assert p1.prompt_text == p2.prompt_text

    def test_caveman_mode_in_prompt(self):
        """Prompt includes caveman mode instruction."""
        prompt = generate_agent_prompt_for_task_range(TASKS, "T100", "T101", REQUIRED_DOCS)
        assert "Caveman" in prompt.prompt_text or "caveman" in prompt.prompt_text

    def test_output_format_section(self):
        """Prompt includes output format section."""
        prompt = generate_agent_prompt_for_task_range(TASKS, "T100", "T101", REQUIRED_DOCS)
        assert "FILES" in prompt.prompt_text
        assert "TESTS" in prompt.prompt_text
        assert "RESULT" in prompt.prompt_text
        assert "NOTES" in prompt.prompt_text

    def test_task_range_field(self):
        """Prompt task_range field is correct."""
        prompt = generate_agent_prompt_for_task_range(TASKS, "T100", "T101", REQUIRED_DOCS)
        assert prompt.task_range == "T100..T101"

    def test_commit_per_task(self):
        """Prompt includes commit per task instruction."""
        prompt = generate_agent_prompt_for_task_range(TASKS, "T100", "T101", REQUIRED_DOCS)
        assert "commit per task" in prompt.prompt_text.lower()

    def test_frozen_dataclass(self):
        """PrdAgentPrompt is frozen."""
        prompt = generate_agent_prompt_for_task_range(TASKS, "T100", "T101", REQUIRED_DOCS)
        with pytest.raises(AttributeError):
            prompt.task_range = "changed"


class TestPrdAgentPromptToDict:
    """Tests for prd_agent_prompt_to_dict."""

    def test_roundtrip_keys(self):
        """Dict has expected keys."""
        prompt = generate_agent_prompt_for_task_range(TASKS, "T100", "T101", REQUIRED_DOCS)
        d = prd_agent_prompt_to_dict(prompt)
        assert "task_range" in d
        assert "prompt_text" in d
        assert "required_docs" in d
        assert "hard_stop_task_id" in d
        assert "safety_warnings" in d
        assert "notes" in d

    def test_values_match(self):
        """Dict values match prompt fields."""
        prompt = generate_agent_prompt_for_task_range(TASKS, "T100", "T101", REQUIRED_DOCS)
        d = prd_agent_prompt_to_dict(prompt)
        assert d["task_range"] == prompt.task_range
        assert d["prompt_text"] == prompt.prompt_text
        assert d["required_docs"] == list(prompt.required_docs)
        assert d["hard_stop_task_id"] == prompt.hard_stop_task_id


class TestPrdAgentPromptToMarkdown:
    """Tests for prd_agent_prompt_to_markdown."""

    def test_contains_hard_stop(self):
        """Markdown includes hard stop."""
        prompt = generate_agent_prompt_for_task_range(TASKS, "T100", "T101", REQUIRED_DOCS)
        md = prd_agent_prompt_to_markdown(prompt)
        assert "T101" in md
        assert "Hard stop" in md or "hard stop" in md.lower()

    def test_contains_required_docs(self):
        """Markdown includes required docs."""
        prompt = generate_agent_prompt_for_task_range(TASKS, "T100", "T101", REQUIRED_DOCS)
        md = prd_agent_prompt_to_markdown(prompt)
        for doc in REQUIRED_DOCS:
            assert doc in md

    def test_contains_safety_warnings(self):
        """Markdown includes safety warnings."""
        prompt = generate_agent_prompt_for_task_range(TASKS, "T100", "T101", REQUIRED_DOCS)
        md = prd_agent_prompt_to_markdown(prompt)
        assert "Safety" in md or "safety" in md.lower()
