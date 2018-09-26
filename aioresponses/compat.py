# -*- coding: utf-8 -*-
import re
from typing import Optional, Union, Dict
from urllib.parse import (
    urlsplit,
    urlencode,
    SplitResult,
    urlunsplit,
    parse_qsl,
)

from aiohttp import __version__ as aiohttp_version, StreamReader
from multidict.__init__ import MultiDict

try:
    Pattern = re._pattern_type
except AttributeError:
    # Python 3.7
    Pattern = re.Pattern
yarl_available = False
from yarl import URL

if int(aiohttp_version.split('.')[0]) >= 3:
    from aiohttp.client_proto import ResponseHandler


    def stream_reader_factory():
        protocol = ResponseHandler()
        return StreamReader(protocol)


else:

    def stream_reader_factory():
        return StreamReader()


def merge_params(url: Union[URL, str], params: Dict = None) -> 'URL':
    url = URL(url)
    if params:
        multi_params = MultiDict(url.query)
        multi_params.extend(url.with_query(params).query)
        url = url.with_query(multi_params)
    return url


def normalize_url(url: Union[URL, str]) -> 'URL':
    """Normalize url to make comparisons."""
    url = URL(url)
    return url.with_query(urlencode(sorted(parse_qsl(url.query_string))))


__all__ = ['URL', 'Pattern', 'merge_params', 'stream_reader_factory']
