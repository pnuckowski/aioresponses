# -*- coding: utf-8 -*-
import re
from typing import Optional, Union, Dict
from urllib.parse import urlsplit, urlencode, SplitResult, urlunsplit, \
    parse_qsl

from aiohttp import __version__ as aiohttp_version, StreamReader
from multidict.__init__ import MultiDict

try:
    Pattern = re._pattern_type
except AttributeError:
    # Python 3.7
    Pattern = re.Pattern
yarl_available = False
from yarl import URL

# try:
#
#
#     if aiohttp_version.split('.')[:2] == ['1', '0']:
#         # yarl was introduced in version 1.1
#         raise ImportError
#     yarl_available = True
# except ImportError:
#     class URL(str):
#         pass

if int(aiohttp_version.split('.')[0]) >= 3:
    from aiohttp.client_proto import ResponseHandler


    def stream_reader_factory():
        protocol = ResponseHandler()
        return StreamReader(protocol)
else:
    def stream_reader_factory():
        return StreamReader()


def _vanilla_merge_url_params(url: str, params: Optional[dict]) -> str:
    if not params:
        return url
    url_split = urlsplit(url)

    if url_split.query:
        qs = "{}&{}".format(url_split.query, urlencode(params))
    else:
        qs = urlencode(params)

    new = SplitResult(
        scheme=url_split.scheme,
        netloc=url_split.netloc,
        path=url_split.path,
        query=qs,
        fragment=url_split.fragment
    )

    return urlunsplit(new)


def _yarl_merge_url_params(url: str, params: Optional[dict]) -> str:
    if not params:
        return url

    url = URL(url)
    if url.query_string:
        return str(url.with_query(
            "{}&{}".format(url.query_string, urlencode(params)))
        )
    else:
        return str(url.with_query(params))


if yarl_available:
    merge_url_params = _yarl_merge_url_params
else:
    merge_url_params = _vanilla_merge_url_params


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


__all__ = [
    'URL',
    'Pattern',
    'merge_url_params',
    'stream_reader_factory',
]
