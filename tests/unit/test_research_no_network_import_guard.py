"""Tests for research no-network import guard — T8521-T8560.

Forbidden import fixtures, allowed import tests.
"""
from __future__ import annotations

import pytest
import tempfile
from pathlib import Path
from core.research_no_network_import_guard import (
    scan_file_forbidden_imports, scan_directory_forbidden_imports,
)


class TestImportGuardNormal:
    def test_clean_file(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write("import json\nimport os\n")
            f.flush()
            violations = scan_file_forbidden_imports(Path(f.name))
            assert violations == ()


class TestImportGuardAdversarial:
    def test_forbidden_import(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write("import requests\n")
            f.flush()
            violations = scan_file_forbidden_imports(Path(f.name))
            assert len(violations) > 0

    def test_from_import(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write("from binance import Client\n")
            f.flush()
            violations = scan_file_forbidden_imports(Path(f.name))
            assert len(violations) > 0


class TestImportGuardEdge:
    def test_nonexistent_file(self):
        violations = scan_file_forbidden_imports(Path("/tmp/nonexistent.py"))
        assert violations == ()
