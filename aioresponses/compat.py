# -*- coding: utf-8 -*-
import re
from distutils.version import StrictVersion
from typing import Union, Dict  # noqa
from urllib.parse import urlencode, parse_qsl

from aiohttp import __version__ as __aioversion__, StreamReader
from multidict import MultiDict
from yarl import URL

try:
    Pattern = re._pattern_type
except AttributeError:  # pragma: no cover
    # Python 3.7
    Pattern = re.Pattern

VERSION = StrictVersion(__aioversion__)

if VERSION >= StrictVersion('3.0.0'):
    from aiohttp.client_proto import ResponseHandler

    def stream_reader_factory():
        protocol = ResponseHandler()
        return StreamReader(protocol)


else:  # pragma: no cover

    def stream_reader_factory():
        return StreamReader()


def merge_params(url: 'Union[URL, str]', params: 'Dict' = None) -> 'URL':
    url = URL(url)
    if params:
        multi_params = MultiDict(url.query)
        multi_params.extend(url.with_query(params).query)
        url = url.with_query(multi_params)
    return url


def normalize_url(url: 'Union[URL, str]') -> 'URL':
    """Normalize url to make comparisons."""
    url = URL(url)
    return url.with_query(urlencode(sorted(parse_qsl(url.query_string))))


__all__ = [
    'URL',
    'Pattern',
    'VERSION',
    'merge_params',
    'stream_reader_factory',
    'normalize_url',
]
