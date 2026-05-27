"""Tests for historical compatibility — existing PRD modules still importable."""
from __future__ import annotations

import importlib
import pytest


class TestHistoricalCompatibility:
    def test_prd_tests_still_pass(self):
        """Verify key PRD modules are still importable."""
        modules = [
            "core.runtime_governance_readonly_hook_spec",
            "core.runtime_governance_contract",
            "core.runtime_governance_frozen_boundary_map",
            "core.runtime_governance_permission_envelope",
            "core.runtime_governance_invariant_checker",
            "core.runtime_governance_reason_codes",
            "core.runtime_governance_readonly_adapter_contract",
            "core.runtime_governance_readonly_approval_form",
            "core.runtime_governance_readonly_artifact_manifest",
            "core.runtime_governance_readonly_batch_summary_packet",
            "core.runtime_governance_readonly_blocker_summary",
            "core.runtime_governance_readonly_closeout_bundle",
            "core.runtime_governance_readonly_engineering_closeout",
            "core.runtime_governance_readonly_evidence_packet",
        ]
        for mod_name in modules:
            mod = importlib.import_module(mod_name)
            assert mod is not None, f"Failed to import {mod_name}"

    def test_hook_modules_independent(self):
        """Verify governance packets module has no imports from prd_* except task_model."""
        import ast
        import inspect

        from core import read_only_hook_governance_packets as mod

        source = inspect.getsource(mod)
        tree = ast.parse(source)

        forbidden_prefixes = ("prd_",)
        allowed_exceptions = ("task_model",)

        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        name = alias.name
                        for prefix in forbidden_prefixes:
                            if name.startswith(prefix):
                                assert name in allowed_exceptions, (
                                    f"Forbidden import: {name}"
                                )
                elif isinstance(node, ast.ImportFrom) and node.module:
                    name = node.module
                    for prefix in forbidden_prefixes:
                        if name.startswith(prefix):
                            assert name in allowed_exceptions, (
                                f"Forbidden import: {name}"
                            )
