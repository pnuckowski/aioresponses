# -*- coding: utf-8 -*-
"""
Pytest plugin for aioresponses.

Provides the `aioresponse` fixture out-of-the-box after
installing the package — no manual conftest.py needed.

Usage::

    async def test_something(aioresponse):
        m = aioresponse()
        m.get("http://example.com", status=200)
        async with aiohttp.ClientSession() as session:
            resp = await session.get("http://example.com")
        assert resp.status == 200
"""

import pytest

from .core import aioresponses


@pytest.fixture
def aioresponse():
    """Pytest fixture factory for aioresponses.

    Call without arguments for a standard mock::

        async def test_get(aioresponse):
            m = aioresponse()
            m.get("http://example.com", status=200)
            ...

    Pass keyword arguments to configure the mock::

        async def test_passthrough(aioresponse):
            m = aioresponse(passthrough_unmatched=True)
            m.get("http://example.com", status=200)
            ...

        async def test_passthrough_list(aioresponse):
            m = aioresponse(passthrough=["http://real-backend"])
            ...
    """
    mocks = []

    def factory(**kwargs):
        mocked = aioresponses(**kwargs)
        mocked.start()
        mocks.append(mocked)
        return mocked

    yield factory

    for mocked in mocks:
        mocked.stop()

