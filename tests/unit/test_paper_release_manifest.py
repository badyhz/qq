"""Tests for release manifest module."""
from __future__ import annotations

import pytest

from core.paper_trading.release_manifest import (
    generate_manifest, manifest_ready, manifest_to_markdown,
    SAFETY_FLAGS, KNOWN_LIMITS,
)


class TestGenerateManifest:
    def test_manifest_generates(self):
        m = generate_manifest()
        assert m["paper_only"] is True
        assert m["version"]
        assert m["generated_at"]

    def test_key_modules_found(self):
        m = generate_manifest()
        assert m["modules"]["found"] >= 20

    def test_key_scripts_found(self):
        m = generate_manifest()
        assert m["scripts"]["found"] >= 6

    def test_fixtures_found(self):
        m = generate_manifest()
        assert m["fixtures"]["found"] >= 1

    def test_safety_flags_complete(self):
        m = generate_manifest()
        for flag in SAFETY_FLAGS:
            assert flag in m["safety_flags"]

    def test_known_limits_present(self):
        m = generate_manifest()
        assert len(m["known_limits"]) >= 3

    def test_next_phase_blockers(self):
        m = generate_manifest()
        assert len(m["next_phase_blockers"]) >= 2

    def test_no_real_order_field(self):
        m = generate_manifest()
        assert "order_id" not in str(m)
        assert "api_key" not in str(m)

    def test_no_external_links(self):
        m = generate_manifest()
        assert "http://" not in str(m)
        assert "https://" not in str(m)


class TestManifestReady:
    def test_ready(self):
        m = generate_manifest()
        assert manifest_ready(m) is True

    def test_not_ready_missing_safety(self):
        m = generate_manifest()
        m["safety_flags"] = ["NO_REAL_ORDER"]
        assert manifest_ready(m) is False

    def test_not_ready_not_paper_only(self):
        m = generate_manifest()
        m["paper_only"] = False
        assert manifest_ready(m) is False


class TestManifestMarkdown:
    def test_generates_md(self):
        m = generate_manifest()
        md = manifest_to_markdown(m)
        assert "Release Manifest" in md
        assert "Paper Only" in md
        assert "Safety Flags" in md

    def test_contains_modules(self):
        m = generate_manifest()
        md = manifest_to_markdown(m)
        assert "order_plan.py" in md

    def test_contains_safety(self):
        m = generate_manifest()
        md = manifest_to_markdown(m)
        for flag in SAFETY_FLAGS:
            assert flag in md

    def test_contains_limits(self):
        m = generate_manifest()
        md = manifest_to_markdown(m)
        assert "Known Limits" in md
        assert "Fixture-only" in md

    def test_no_external_resources(self):
        m = generate_manifest()
        md = manifest_to_markdown(m)
        assert "http://" not in md
        assert "https://" not in md
