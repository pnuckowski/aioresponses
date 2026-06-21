import asyncio
from unittest import IsolatedAsyncioTestCase

import pytest


@pytest.fixture
def fail_on(**kw):
    """No-op decorator kept for test compatibility."""

    def outer(fn):
        def inner(*args, **kwargs):
            return fn(*args, **kwargs)

        return inner

    return outer


class AsyncTestCase(IsolatedAsyncioTestCase):
    """Async test case with setup/teardown hooks matching the original API."""

    async def setup(self):
        pass

    async def teardown(self):
        pass

    async def asyncSetUp(self):
        self.loop = asyncio.get_event_loop()
        await self.setup()

    async def asyncTearDown(self):
        await self.teardown()
