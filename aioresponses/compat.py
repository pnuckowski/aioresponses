# -*- coding: utf-8 -*-
import asyncio  # noqa: F401
from re import Pattern
from typing import Dict, Optional, Union  # noqa
from urllib.parse import parse_qsl, urlencode

from aiohttp import __version__ as aiohttp_version, StreamReader
from aiohttp.client_proto import ResponseHandler
from multidict import MultiDict
from packaging.version import Version
from yarl import URL

AIOHTTP_VERSION = Version(aiohttp_version)


def stream_reader_factory(  # noqa
    loop: 'Optional[asyncio.AbstractEventLoop]' = None
) -> StreamReader:
    protocol = ResponseHandler(loop=loop)
    return StreamReader(protocol, limit=2 ** 16, loop=loop)


def merge_params(
    url: 'Union[URL, str]',
    params: Optional[Dict] = None
) -> 'URL':
    url = URL(url)
    if params:
        query_params = MultiDict(url.query)
        query_params.extend(url.with_query(params).query)
        return url.with_query(query_params)
    return url


def normalize_url(url: 'Union[URL, str]') -> 'URL':
    """Normalize url to make comparisons."""
    url = URL(url)
    return url.with_query(sorted(url.query.items()))


__all__ = [
    'URL',
    'Pattern',
    'AIOHTTP_VERSION',
    'merge_params',
    'stream_reader_factory',
    'normalize_url',
]
