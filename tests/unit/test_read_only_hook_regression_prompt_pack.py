"""Tests for read-only hook regression matrix and prompt pack — pure pytest, no I/O."""
from core.read_only_hook_regression_matrix import (
    RegressionTestCase,
    build_default_regression_matrix,
    regression_test_case_to_dict,
)
from core.read_only_hook_prompt_pack import (
    ReadOnlyHookPromptPack,
    build_read_only_hook_prompt_pack,
    prompt_pack_to_dict,
)


class TestRegressionMatrix:
    def test_default_cases(self):
        cases = build_default_regression_matrix()
        assert len(cases) == 20
        assert all(isinstance(c, RegressionTestCase) for c in cases)

    def test_deterministic(self):
        cases = build_default_regression_matrix()
        d1 = [regression_test_case_to_dict(c) for c in cases]
        d2 = [regression_test_case_to_dict(c) for c in cases]
        assert d1 == d2


class TestPromptPack:
    def test_build_pack(self):
        pack = build_read_only_hook_prompt_pack()
        assert isinstance(pack, ReadOnlyHookPromptPack)
        assert pack.task_range == "T981-T1000"
        assert "T981-T1000" in pack.prompt_text or "read-only hook" in pack.prompt_text
        assert len(pack.required_docs) == 5

    def test_safety_warnings(self):
        pack = build_read_only_hook_prompt_pack()
        assert len(pack.safety_warnings) >= 4
        assert any("no real orders" in w.lower() or "never trigger execution" in w.lower()
                    for w in pack.safety_warnings)

    def test_hard_stop(self):
        pack = build_read_only_hook_prompt_pack()
        assert "invariant" in pack.hard_stop.lower()
        assert len(pack.hard_stop) > 0

    def test_deterministic(self):
        pack = build_read_only_hook_prompt_pack()
        d1 = prompt_pack_to_dict(pack)
        d2 = prompt_pack_to_dict(pack)
        assert d1 == d2
