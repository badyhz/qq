"""Tests for T913 — prd_500_backlog_json_pack.

Deterministic. No I/O. No timestamps. No random.
"""

import json
import unittest
from typing import List

from core.prd_backlog_schema import PrdBacklog, PrdBacklogItem, build_backlog_item
from core.prd_500_backlog_json_pack import (
    Prd500JsonPack,
    build_prd_500_json_pack,
    json_pack_to_dict,
    json_pack_to_string,
)


def _make_backlog(n: int) -> PrdBacklog:
    """Build a backlog with n items. Deterministic."""
    items: List[PrdBacklogItem] = []
    for i in range(n):
        tid = f"T{i:04d}"
        items.append(
            build_backlog_item(
                task_id=tid,
                title=f"Task {tid}",
                milestone_id=f"M{(i // 50):02d}",
                wave_id=f"W{(i // 25):02d}",
                batch_id=f"B{(i // 10):04d}",
                risk_level="LOW",
                status="NOT_STARTED",
                dependencies=[],
                allowed_file_patterns=[],
                forbidden_file_patterns=[],
                acceptance_command_ids=[],
                notes=[],
            )
        )
    return PrdBacklog(
        backlog_id="TEST-500",
        items=items,
        total_expected_tasks=n,
        status="OPEN",
        notes=[],
    )


class TestPrd500JsonPack(unittest.TestCase):
    """T913 test suite."""

    def test_json_serializable(self):
        """json_pack_to_string must produce valid JSON."""
        backlog = _make_backlog(500)
        pack = build_prd_500_json_pack(backlog)
        raw = json_pack_to_string(pack)
        parsed = json.loads(raw)
        self.assertIsInstance(parsed, dict)
        self.assertIn("backlog", parsed)
        self.assertIn("milestone_map", parsed)
        self.assertIn("final_verdict", parsed)

    def test_deterministic_string(self):
        """Two calls must produce identical JSON strings."""
        backlog = _make_backlog(500)
        pack = build_prd_500_json_pack(backlog)
        s1 = json_pack_to_string(pack)
        s2 = json_pack_to_string(pack)
        self.assertEqual(s1, s2)

    def test_item_count_gte_500(self):
        """Pack must contain >= 500 backlog items."""
        backlog = _make_backlog(500)
        pack = build_prd_500_json_pack(backlog)
        item_count = len(pack.backlog["items"])
        self.assertGreaterEqual(item_count, 500)

    def test_no_live_authorization(self):
        """Pack must not contain any live trade authorization."""
        backlog = _make_backlog(500)
        pack = build_prd_500_json_pack(backlog)
        raw = json_pack_to_string(pack)
        forbidden = ["LIVE_ORDER", "REAL_TRADE", "LIVE_TRADING"]
        for keyword in forbidden:
            self.assertNotIn(keyword, raw, f"Pack contains forbidden keyword: {keyword}")


if __name__ == "__main__":
    unittest.main()
