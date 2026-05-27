"""Root conftest -- local async-test shim for @pytest.mark.anyio.

anyio (and its pytest plugin) are not installed in .venv.
This hook rewrites any @pytest.mark.anyio async test functions
so pytest runs them via asyncio.run() instead of failing with
"async def functions are not natively supported".

Scope: project root only. Does not touch frozen files.
Safety: no network, no exchange, no live trading.
"""

import asyncio
import functools
import inspect

import pytest


def pytest_configure(config):
    config.addinivalue_line("markers", "anyio: run async test via asyncio.run()")


def pytest_collection_modifyitems(items):
    """Wrap async anyio-marked tests so pytest runs them synchronously."""
    for item in items:
        if isinstance(item, pytest.Function) and inspect.iscoroutinefunction(item.obj):
            if any(marker.name == "anyio" for marker in item.iter_markers()):
                fn = item.obj

                @functools.wraps(fn)
                def wrapper(*args, _fn=fn, **kwargs):
                    result = asyncio.run(_fn(*args, **kwargs))
                    # asyncio.run() closes the loop and sets it to None.
                    # Restore a fresh loop so other sync tests that call
                    # asyncio.get_event_loop().run_until_complete() still work.
                    try:
                        asyncio.get_event_loop()
                    except RuntimeError:
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                    return result

                item.obj = wrapper
