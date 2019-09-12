# -*- coding: utf-8 -*-
import asyncio  # noqa: F401
import sys
from distutils.version import StrictVersion
from typing import Dict, Optional, Tuple, Union  # noqa
from urllib.parse import parse_qsl, urlencode

from aiohttp import __version__ as aiohttp_version, StreamReader
from multidict import MultiDict
from yarl import URL

if sys.version_info < (3, 7):
    from re import _pattern_type as Pattern
else:
    from re import Pattern

AIOHTTP_VERSION = StrictVersion(aiohttp_version)

if AIOHTTP_VERSION >= StrictVersion('3.0.0'):
    from aiohttp.client_proto import ResponseHandler

    def stream_reader_factory(
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


__all__ = [
    'URL',
    'Pattern',
    'AIOHTTP_VERSION',
    'merge_params',
    'stream_reader_factory',
    'normalize_url',
]
