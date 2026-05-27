"""Boundary tests for read-only hook acceptance layer (T1021-T1040).

Verifies no forbidden imports or file boundary violations in read_only_hook_* modules.
"""

import os
import re

import pytest

# Root of the project
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CORE_DIR = os.path.join(PROJECT_ROOT, "core")


def _read_hook_module_basenames():
    """Return list of read_only_hook_*.py filenames in core/."""
    results = []
    if not os.path.isdir(CORE_DIR):
        return results
    for name in os.listdir(CORE_DIR):
        if name.startswith("read_only_hook_") and name.endswith(".py"):
            results.append(name)
    return results


def _read_hook_module_paths():
    """Return full paths to read_only_hook_*.py files."""
    return [
        os.path.join(CORE_DIR, name)
        for name in _read_hook_module_basenames()
    ]


def _read_file_content(path):
    """Read file content as string."""
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


# ---------------------------------------------------------------------------
# Forbidden import tests
# ---------------------------------------------------------------------------

class TestForbiddenImports:

    def test_no_exchange_imports(self):
        """read_only_hook_* must not import exchange, execution, or live_runner."""
        forbidden_patterns = [
            r"from\s+core\.exchange",
            r"from\s+core\.execution",
            r"from\s+core\.live_runner",
            r"import\s+core\.exchange",
            r"import\s+core\.execution",
            r"import\s+core\.live_runner",
        ]
        violations = []
        for path in _read_hook_module_paths():
            content = _read_file_content(path)
            for pattern in forbidden_patterns:
                matches = re.findall(pattern, content)
                if matches:
                    violations.append(
                        f"{os.path.basename(path)}: {matches[0]}"
                    )
        assert not violations, f"Forbidden exchange/execution imports: {violations}"

    def test_no_planner_imports(self):
        """read_only_hook_* must not import planner modules."""
        forbidden_patterns = [
            r"^from\s+.*planner",
            r"^import\s+.*planner",
        ]
        violations = []
        for path in _read_hook_module_paths():
            content = _read_file_content(path)
            for line in content.splitlines():
                stripped = line.strip()
                for pattern in forbidden_patterns:
                    if re.match(pattern, stripped):
                        violations.append(
                            f"{os.path.basename(path)}: {stripped}"
                        )
        assert not violations, f"Forbidden planner imports: {violations}"

    def test_no_order_manager_imports(self):
        """read_only_hook_* must not import order_manager."""
        forbidden_patterns = [
            r"from\s+core\.order_manager",
            r"import\s+core\.order_manager",
        ]
        violations = []
        for path in _read_hook_module_paths():
            content = _read_file_content(path)
            for pattern in forbidden_patterns:
                matches = re.findall(pattern, content)
                if matches:
                    violations.append(
                        f"{os.path.basename(path)}: {matches[0]}"
                    )
        assert not violations, f"Forbidden order_manager imports: {violations}"

    def test_no_binance_client_imports(self):
        """read_only_hook_* must not import binance client modules."""
        forbidden_patterns = [
            r"from\s+core\.binance",
            r"import\s+core\.binance",
        ]
        violations = []
        for path in _read_hook_module_paths():
            content = _read_file_content(path)
            for pattern in forbidden_patterns:
                matches = re.findall(pattern, content)
                if matches:
                    violations.append(
                        f"{os.path.basename(path)}: {matches[0]}"
                    )
        assert not violations, f"Forbidden binance imports: {violations}"


# ---------------------------------------------------------------------------
# Forbidden file boundary tests
# ---------------------------------------------------------------------------

class TestForbiddenFiles:

    def test_no_core_runtime_files(self):
        """read_only_hook_* files must not reference live runtime modules
        by file write operations."""
        runtime_modules = [
            "live_runner",
            "order_manager",
            "execution.py",
            "binance_testnet_client",
            "binance_http",
        ]
        violations = []
        for path in _read_hook_module_paths():
            content = _read_file_content(path)
            for mod in runtime_modules:
                # Check for open(..., 'w') targeting runtime files
                pattern = rf"open\s*\(\s*['\"].*{re.escape(mod)}"
                matches = re.findall(pattern, content)
                if matches:
                    violations.append(
                        f"{os.path.basename(path)}: writes to {mod}"
                    )
        assert not violations, f"Forbidden file writes: {violations}"

    def test_hook_files_are_self_contained(self):
        """read_only_hook_* must only import from read_only_hook_* or stdlib."""
        hook_basenames = set(_read_hook_module_basenames())
        hook_modules = {name.replace(".py", "") for name in hook_basenames}

        # Allow all read_only_hook_* modules (cross-hook imports are valid)
        allowed_internal = hook_modules | {
            "__future__",
            "copy",
            "dataclasses",
            "enum",
            "functools",
            "json",
            "logging",
            "os",
            "pathlib",
            "re",
            "typing",
        }

        violations = []
        for path in _read_hook_module_paths():
            content = _read_file_content(path)
            # Match 'from X import' or 'import X'
            imports = re.findall(
                r"^(?:from\s+(\S+)|import\s+(\S+))",
                content,
                re.MULTILINE,
            )
            for from_mod, import_mod in imports:
                mod = from_mod or import_mod
                top = mod.split(".")[0]
                # Allow stdlib
                if top in allowed_internal:
                    continue
                # Allow core.read_only_hook_* cross-imports
                if mod.startswith("core.read_only_hook_"):
                    continue
                # Flag anything else under core.*
                if top.startswith("core"):
                    violations.append(
                        f"{os.path.basename(path)}: imports {mod}"
                    )
        assert not violations, f"Non-allowed core imports: {violations}"
