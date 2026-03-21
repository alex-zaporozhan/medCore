"""
Tiny pytest plugin to run async tests/fixtures without external dependencies.

Why:
- Some environments execute tests with system Python where `pytest-asyncio`
  is not installed. Our suite uses async tests + async fixtures extensively.

This plugin provides a minimal subset:
- run `async def test_*` coroutines;
- support `async def` fixtures and async-generator fixtures (yield fixtures).

It is intentionally small and only targets asyncio.
"""

from __future__ import annotations

import asyncio
import inspect
from typing import Any, Generator

import pytest


_HANDLED_NONE = object()


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Session-scoped event loop (similar to pytest-asyncio default)."""
    loop = asyncio.new_event_loop()
    try:
        yield loop
    finally:
        loop.close()


def pytest_configure(config: pytest.Config) -> None:
    # Register asyncio marker so PytestUnknownMarkWarning doesn't mask real failures.
    config.addinivalue_line("markers", "asyncio: mark async test to run in asyncio loop")


@pytest.hookimpl(tryfirst=True)
def pytest_pyfunc_call(pyfuncitem: pytest.Function) -> bool | None:
    """
    Run coroutine test functions in the session event loop.

    Returning True tells pytest we executed the test.
    """
    testfunc = pyfuncitem.obj
    if inspect.iscoroutinefunction(testfunc):
        # Ensure event_loop fixture exists even if not requested explicitly.
        loop: asyncio.AbstractEventLoop = pyfuncitem._request.getfixturevalue("event_loop")  # type: ignore[attr-defined]
        loop.run_until_complete(testfunc(**pyfuncitem.funcargs))
        return True
    return None


@pytest.hookimpl(tryfirst=True)
def pytest_fixture_setup(
    fixturedef: pytest.FixtureDef[Any],
    request: pytest.FixtureRequest,
) -> Any:
    """
    Execute async fixtures (coroutines / async generators) on the event loop.

    If fixture is not async, defer to default pytest behaviour (return None).
    """
    # Avoid recursion: the event_loop fixture itself must be created by pytest normally.
    if fixturedef.argname == "event_loop":
        return None

    fixturefunc = fixturedef.func
    kwargs = {name: request.getfixturevalue(name) for name in fixturedef.argnames}

    # Fast path for native async fixtures.
    if inspect.iscoroutinefunction(fixturefunc):
        loop: asyncio.AbstractEventLoop = request.getfixturevalue("event_loop")
        value = loop.run_until_complete(fixturefunc(**kwargs))
        # `pytest_fixture_setup` is a "firstresult" hook. If a real fixture value is None,
        # returning None would be interpreted as "not handled", triggering Pytest warnings.
        return _HANDLED_NONE if value is None else value

    if inspect.isasyncgenfunction(fixturefunc):
        loop = request.getfixturevalue("event_loop")
        agen = fixturefunc(**kwargs)

        async def _anext():
            return await agen.__anext__()

        value = loop.run_until_complete(_anext())

        def _finalizer() -> None:
            async def _aclose() -> None:
                await agen.aclose()

            loop.run_until_complete(_aclose())

        request.addfinalizer(_finalizer)
        return _HANDLED_NONE if value is None else value

    # Compatibility path for newer Pytest versions that may wrap async fixtures.
    # If calling fixture returns an awaitable/asyncgen, handle it as async.
    res = fixturefunc(**kwargs)
    if inspect.isawaitable(res):
        loop = request.getfixturevalue("event_loop")
        value = loop.run_until_complete(res)
        return _HANDLED_NONE if value is None else value
    if inspect.isasyncgen(res):
        loop = request.getfixturevalue("event_loop")
        agen = res

        async def _anext2():
            return await agen.__anext__()

        value = loop.run_until_complete(_anext2())

        def _finalizer2() -> None:
            async def _aclose2() -> None:
                await agen.aclose()

            loop.run_until_complete(_aclose2())

        request.addfinalizer(_finalizer2)
        return _HANDLED_NONE if value is None else value

    return None

