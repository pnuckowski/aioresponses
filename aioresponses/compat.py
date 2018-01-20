# -*- coding: utf-8 -*-
from aiohttp import __version__ as aiohttp_version
from typing import Optional
from urllib.parse import urlsplit, urlencode, SplitResult, urlunsplit

try:
    from yarl import URL
    if aiohttp_version.split('.')[:2] == ['1', '0']:
        # yarl was introduced in version 1.1
        raise ImportError
    yarl_available = True
except ImportError:
    class URL(str):
        pass
    yarl_available = False


__all__ = ['URL', 'merge_url_params']


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
