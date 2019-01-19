# -*- coding: utf-8 -*-
import asyncio  # noqa
import json
import re
from distutils.version import StrictVersion
from typing import Dict, Optional, Tuple, Union  # noqa
from unittest.mock import Mock
from urllib.parse import parse_qsl, urlencode

from aiohttp import (
    __version__ as aiohttp_version,
    ClientResponse,
    StreamReader,
    hdrs,
)
from aiohttp.helpers import TimerNoop
from multidict import CIMultiDict, MultiDict
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


def _build_raw_headers(headers: Dict) -> Tuple:
    """
    Convert a dict of headers to a tuple of tuples

    Mimics the format of ClientResponse.
    """
    raw_headers = []
    for k, v in headers.items():
        raw_headers.append((k.encode('utf8'), v.encode('utf8')))
    return tuple(raw_headers)


def build_response(
        url: 'Union[URL, str]',
        method: str = hdrs.METH_GET,
        status: int = 200,
        body: str = '',
        content_type: str = 'application/json',
        payload: Dict = None,
        headers: Dict = None,
        response_class: 'ClientResponse' = None,
        reason: Optional[str] = None) -> ClientResponse:
    if response_class is None:
        response_class = ClientResponse
    if payload is not None:
        body = json.dumps(payload)
    if not isinstance(body, bytes):
        body = str.encode(body)
    kwargs = {}
    if AIOHTTP_VERSION >= StrictVersion('3.1.0'):
        loop = Mock()
        loop.get_debug = Mock()
        loop.get_debug.return_value = True
        kwargs['request_info'] = Mock()
        kwargs['writer'] = Mock()
        kwargs['continue100'] = None
        kwargs['timer'] = TimerNoop()
        if AIOHTTP_VERSION < StrictVersion('3.3.0'):
            kwargs['auto_decompress'] = True
        kwargs['traces'] = []
        kwargs['loop'] = loop
        kwargs['session'] = None
    _headers = CIMultiDict({hdrs.CONTENT_TYPE: content_type})
    if headers:
        _headers.update(headers)
    raw_headers = _build_raw_headers(_headers)
    resp = response_class(method, url, **kwargs)
    if AIOHTTP_VERSION >= StrictVersion('3.3.0'):
        # Reified attributes
        resp._headers = _headers
        resp._raw_headers = raw_headers
    else:
        resp.headers = _headers
        resp.raw_headers = raw_headers
    resp.status = status
    resp.reason = reason
    resp.content = stream_reader_factory()
    resp.content.feed_data(body)
    resp.content.feed_eof()
    return resp


__all__ = [
    'URL',
    'Pattern',
    'AIOHTTP_VERSION',
    'merge_params',
    'stream_reader_factory',
    'normalize_url',
    'build_response',
]
