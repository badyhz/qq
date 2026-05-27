from core.runtime_governance_final_closeout_doc import build_runtime_governance_final_closeout_markdown


class TestRuntimeGovernanceFinalCloseoutDoc:

    def setup_method(self):
        self.md = build_runtime_governance_final_closeout_markdown()

    def test_deterministic(self):
        assert build_runtime_governance_final_closeout_markdown() == self.md

    def test_contains_no_live_trading(self):
        assert "no live trading" in self.md.lower()

    def test_contains_frozen_boundaries(self):
        lower = self.md.lower()
        assert "live submit" in lower
        assert "secrets" in lower
        assert "planner" in lower
        assert "exchange client" in lower
        assert "runtime execution" in lower

    def test_contains_next_safe_phase(self):
        assert "manual review / read-only hook design" in self.md.lower()

    def test_no_timestamps(self):
        import re
        iso_pattern = r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}"
        time_pattern = r"\d{2}:\d{2}:\d{2}"
        assert not re.search(iso_pattern, self.md), "found ISO timestamp"
        assert not re.search(time_pattern, self.md), "found time timestamp"
