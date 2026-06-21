from re import Pattern
from urllib.parse import urlencode  # noqa: F401

from aiohttp import StreamReader
from aiohttp import __version__ as aiohttp_version
from aiohttp.client_proto import ResponseHandler
from multidict import MultiDict
from packaging.version import Version
from yarl import URL

AIOHTTP_VERSION = Version(aiohttp_version)


def stream_reader_factory(loop=None) -> StreamReader:
    # The ``loop`` parameter was removed from ResponseHandler and StreamReader
    # in aiohttp 3.10. Pass it only on older versions.
    if AIOHTTP_VERSION >= Version("3.10.0"):
        protocol = ResponseHandler(loop)
        return StreamReader(protocol, limit=2**16)
    protocol = ResponseHandler(loop=loop)
    return StreamReader(protocol, limit=2**16, loop=loop)


def merge_params(url: URL | str, params: dict | None = None) -> URL:
    url = URL(url)
    if params:
        query_params = MultiDict(url.query)
        query_params.extend(url.with_query(params).query)
        return url.with_query(query_params)
    return url


def normalize_url(url: URL | str) -> URL:
    """Normalize url to make comparisons."""
    url = URL(url)
    return url.with_query(sorted(url.query.items()))


__all__ = [
    "URL",
    "Pattern",
    "AIOHTTP_VERSION",
    "merge_params",
    "stream_reader_factory",
    "normalize_url",
]
