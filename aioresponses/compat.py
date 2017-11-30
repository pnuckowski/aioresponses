# -*- coding: utf-8 -*-
from urllib.parse import urlsplit, urlencode, SplitResult, urlunsplit

try:
    from yarl import URL
    __yarl_available = True
except ImportError:
    class URL(str):
        pass
    __yarl_available = False


__all__ = ['URL', 'merge_url_params']


def _vanilla_merge_url_params(url: str, params: dict) -> str:
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


def _yarl_merge_url_params(url: str, params: dict) -> str:
    if not params:
        return url

    url = URL(url)
    if url.query_string:
        return str(url.with_query(
            "{}&{}".format(url.query_string, urlencode(params)))
        )
    else:
        return str(url.with_query(params))


if __yarl_available:
    merge_url_params = _yarl_merge_url_params
else:
    merge_url_params = _vanilla_merge_url_params
