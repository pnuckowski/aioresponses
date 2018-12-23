# -*- coding: utf-8 -*-
import asyncio
import re
from distutils.version import StrictVersion
from typing import Dict, Optional, Union  # noqa
from urllib.parse import parse_qsl, urlencode

from aiohttp import StreamReader
from aiohttp import __version__ as aiohttp_version
from multidict import MultiDict
from yarl import URL

try:
    Pattern = re._pattern_type
except AttributeError:  # pragma: no cover
    # Python 3.7
    Pattern = re.Pattern

AIOHTTP_VERSION = StrictVersion(aiohttp_version)

if AIOHTTP_VERSION >= StrictVersion('3.0.0'):
    from aiohttp.client_proto import ResponseHandler

    def stream_reader_factory(
            loop: 'Optional[asyncio.AbstractEventLoop]' = None
    ):
        protocol = ResponseHandler(loop=loop)
        return StreamReader(protocol)


else:  # pragma: no cover

    def stream_reader_factory():
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
