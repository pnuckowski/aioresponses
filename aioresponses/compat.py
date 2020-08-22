# -*- coding: utf-8 -*-
import asyncio  # noqa: F401
import sys
from distutils.version import StrictVersion
from typing import Dict, Optional, Tuple, Union  # noqa
from urllib.parse import parse_qsl, urlencode

from aiohttp import __version__ as aiohttp_version, StreamReader
from multidict import MultiDict
from yarl import URL

try:
    # as from Py3.8 unittest supports coroutines as test functions
    from unittest import IsolatedAsyncioTestCase, skipIf


    def fail_on(**kw):  # noqa
        def outer(fn):
            def inner(*args, **kwargs):
                return fn(*args, **kwargs)

            return inner

        return outer


except ImportError:
    # fallback to asynctest
    from asynctest import fail_on, skipIf
    from asynctest.case import TestCase as IsolatedAsyncioTestCase

if sys.version_info < (3, 7):
    from re import _pattern_type as Pattern
else:
    from re import Pattern

AIOHTTP_VERSION = StrictVersion(aiohttp_version)
IS_GTE_PY38 = sys.version_info >= (3, 8)

if AIOHTTP_VERSION >= StrictVersion('3.0.0'):
    from aiohttp.client_proto import ResponseHandler


    def stream_reader_factory(  # noqa
        loop: 'Optional[asyncio.AbstractEventLoop]' = None
    ):
        protocol = ResponseHandler(loop=loop)
        return StreamReader(protocol, loop=loop)

else:

    def stream_reader_factory(loop=None):
        return StreamReader()


def merge_params(url: 'Union[URL, str]', params: 'Dict' = None) -> 'URL':
    url = URL(url)
    if params:
        query_params = MultiDict(url.query)
        query_params.extend(url.with_query(params).query)
        return url.with_query(query_params)
    return url


def normalize_url(url: 'Union[URL, str]') -> 'URL':
    """Normalize url to make comparisons."""
    url = URL(url)
    return url.with_query(urlencode(sorted(parse_qsl(url.query_string))))


class AsyncTestCase(IsolatedAsyncioTestCase):
    """Asynchronous test case class that covers up differences in usage
    between unittest (starting from Python 3.8) and asynctest.

    `setup` and `teardown` is used to be called before each test case
    (note: that they are in lowercase)
    """

    async def setup(self):
        pass

    async def teardown(self):
        pass

    if IS_GTE_PY38:
        # from Python3.8
        async def asyncSetUp(self):
            self.loop = asyncio.get_event_loop()
            await self.setup()

        async def asyncTearDown(self):
            await self.teardown()
    else:
        # asynctest
        use_default_loop = False

        async def setUp(self) -> None:
            await self.setup()

        async def tearDown(self) -> None:
            await self.teardown()


__all__ = [
    'URL',
    'Pattern',
    'skipIf',
    'AIOHTTP_VERSION',
    'AsyncTestCase',
    'merge_params',
    'stream_reader_factory',
    'normalize_url',
    'fail_on',
]
