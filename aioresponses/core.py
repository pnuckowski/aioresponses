# -*- coding: utf-8 -*-

import asyncio
import json
from typing import Dict, Tuple
from unittest.mock import patch
from urllib.parse import urlparse, parse_qsl, urlencode

from aiohttp import (
    hdrs, ClientResponse, ClientConnectionError, StreamReader, client
)
from collections import namedtuple
from functools import wraps
from multidict import CIMultiDict

from .compat import URL, merge_url_params


class UrlResponse(object):
    resp = None

    def __init__(self, url: str, method: str = hdrs.METH_GET,
                 status: int = 200, body: str = '',
                 exception: 'Exception' = None,
                 headers: Dict = None, payload: Dict = None,
                 content_type: str = 'application/json',
                 response_class=None):
        self.url = self.parse_url(url)
        self.method = method.lower()
        self.status = status
        if payload is not None:
            body = json.dumps(payload)
        if not isinstance(body, bytes):
            body = str.encode(body)
        self.body = body
        self.exception = exception
        self.headers = headers
        self.content_type = content_type
        self.response_class = response_class or ClientResponse

    def parse_url(self, url: str) -> str:
        """Normalize url to make comparisons."""
        url = str(url)
        _url = url.split('?')[0]
        query = urlencode(sorted(parse_qsl(urlparse(url).query)))

        return '{}?{}'.format(_url, query) if query else _url

    def match(self, method: str, url: str) -> bool:
        if self.method != method.lower():
            return False
        return self.url == self.parse_url(url)

    def build_response(self) -> 'ClientResponse':
        if isinstance(self.exception, Exception):
            raise self.exception
        self.resp = self.response_class(self.method, URL(self.url))
        # we need to initialize headers manually
        self.resp.headers = CIMultiDict({hdrs.CONTENT_TYPE: self.content_type})
        if self.headers:
            self.resp.headers.update(self.headers)
            self.resp.raw_headers = self._build_raw_headers(self.resp.headers)
        self.resp.status = self.status
        self.resp.content = StreamReader()
        self.resp.content.feed_data(self.body)
        self.resp.content.feed_eof()

        return self.resp

    def _build_raw_headers(self, headers):
        """
        Convert a dict of headers to a tuple of tuples

        Mimics the format of ClientResponse.
        """
        raw_headers = []
        for k, v in headers.items():
            raw_headers.append((k.encode('utf8'), v.encode('utf8')))
        return tuple(raw_headers)


class aioresponses(object):
    """Mock aiohttp requests made by ClientSession."""
    _responses = None
    method_call = namedtuple('method_call', ['args', 'kwargs'])

    def __init__(self, **kwargs):
        self._param = kwargs.pop('param', None)
        self._passthrough = kwargs.pop('passthrough', [])
        self.patcher = patch('aiohttp.client.ClientSession._request',
                             side_effect=self._request_mock,
                             autospec=True)
        self.requests = {}

    def __enter__(self) -> 'aioresponses':
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()

    def __call__(self, f):
        def _pack_arguments(ctx, *args, **kwargs) -> Tuple[Tuple, Dict]:
            if self._param:
                kwargs[self._param] = ctx
            else:
                args += (ctx,)
            return args, kwargs

        if asyncio.iscoroutinefunction(f):
            @wraps(f)
            @asyncio.coroutine
            def wrapped(*args, **kwargs):
                with self as ctx:
                    args, kwargs = _pack_arguments(ctx, *args, **kwargs)
                    return (yield from f(*args, **kwargs))
        else:
            @wraps(f)
            def wrapped(*args, **kwargs):
                with self as ctx:
                    args, kwargs = _pack_arguments(ctx, *args, **kwargs)
                    return f(*args, **kwargs)
        return wrapped

    def start(self):
        self._responses = []
        self.patcher.start()
        self.patcher.return_value = self._request_mock

    def stop(self) -> None:
        for r in self._responses:
            if r.resp is not None:
                r.resp.close()
        self.patcher.stop()
        self._responses = []

    def head(self, url: str, **kwargs):
        self.add(url, method=hdrs.METH_HEAD, **kwargs)

    def get(self, url: str, **kwargs):
        self.add(url, method=hdrs.METH_GET, **kwargs)

    def post(self, url: str, **kwargs):
        self.add(url, method=hdrs.METH_POST, **kwargs)

    def put(self, url: str, **kwargs):
        self.add(url, method=hdrs.METH_PUT, **kwargs)

    def patch(self, url: str, **kwargs):
        self.add(url, method=hdrs.METH_PATCH, **kwargs)

    def delete(self, url: str, **kwargs):
        self.add(url, method=hdrs.METH_DELETE, **kwargs)

    def options(self, url: str, **kwargs):
        self.add(url, method=hdrs.METH_OPTIONS, **kwargs)

    def add(self, url: str, method: str = hdrs.METH_GET, status: int = 200,
            body: str = '',
            exception: 'Exception' = None,
            content_type: str = 'application/json',
            payload: Dict = None,
            headers: Dict = None,
            response_class=None) -> None:
        self._responses.append(UrlResponse(
            url,
            method=method,
            status=status,
            content_type=content_type,
            body=body,
            exception=exception,
            payload=payload,
            headers=headers,
            response_class=response_class,
        ))

    def match(self, method: str, url: str) -> 'ClientResponse':
        i, resp = next(
            iter(
                [(i, r.build_response())
                 for i, r in enumerate(self._responses)
                 if r.match(method, url)]
            ),
            (None, None)
        )

        if i is not None:
            del self._responses[i]
        return resp

    @asyncio.coroutine
    def _request_mock(self, orig_self: client.ClientSession,
                      method: str, url: str, *args: Tuple,
                      **kwargs: Dict) -> 'ClientResponse':
        """Return mocked response object or raise connection error."""

        url = merge_url_params(url, kwargs.get('params'))

        for prefix in self._passthrough:
            if str(url).startswith(prefix):
                return (yield from self.patcher.temp_original(
                    orig_self, method, url, *args, **kwargs
                ))

        response = self.match(method, url)
        if response is None:
            raise ClientConnectionError(
                'Connection refused: {} {}'.format(method, url)
            )
        key = (method, url)
        self.requests.setdefault(key, list())
        self.requests[key].append(self.method_call(args, kwargs))
        return response
