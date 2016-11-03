# -*- coding: utf-8 -*-

import asyncio
import json
from functools import wraps
from multidict import CIMultiDict

try:
    from typing import Dict, Tuple
except ImportError:
    Dict = dict
    Tuple = tuple
from unittest.mock import patch
from urllib.parse import urlparse, parse_qsl, urlencode

from aiohttp import hdrs, ClientResponse, ClientConnectionError


class UrlResponse(object):
    resp = None

    def __init__(self, url: str, method: str = hdrs.METH_GET,
                 status: int = 200, body: str = '',
                 headers: Dict = None, payload: Dict = None,
                 content_type: str = 'application/json', ):
        self.url = self.parse_url(url)
        self.method = method.lower()
        self.status = status
        if payload is not None:
            body = json.dumps(payload)
        if not isinstance(body, bytes):
            body = str.encode(body)
        self.body = body
        self.headers = headers
        self.content_type = content_type

    def parse_url(self, url: str) -> str:
        """Normalize url to make comparisons."""
        _url = url.split('?')[0]
        query = urlencode(sorted(parse_qsl(urlparse(url).query)))

        return '{}?{}'.format(_url, query) if query else _url

    def match(self, method: str, url: str) -> bool:
        if self.method != method.lower():
            return False
        return self.url == self.parse_url(url)

    def build_response(self) -> 'ClientResponse':
        self.resp = ClientResponse(self.method, self.url)
        # we need to initialize headers manually
        self.resp.headers = CIMultiDict({hdrs.CONTENT_TYPE: self.content_type})
        if self.headers:
            self.resp.headers.update(self.headers)
        self.resp.status = self.status
        self.resp._content = self.body

        return self.resp


class aioresponses(object):
    """Mock aiohttp requests made by ClientSession."""
    _responses = None

    def __init__(self, **kwargs):
        self._param = kwargs.pop('param', None)
        self.patcher = patch('aiohttp.client.ClientSession._request',
                             side_effect=self._request_mock)

    def __enter__(self) -> 'aioresponses':
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()

    def __call__(self, f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            with self as ctx:
                if self._param:
                    kwargs[self._param] = ctx
                else:
                    args = list(args)
                    args.append(ctx)

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
            content_type: str = 'application/json',
            payload: Dict=None,
            headers: Dict=None) -> None:
        self._responses.append(UrlResponse(
            url,
            method=method,
            status=status,
            content_type=content_type,
            body=body,
            payload=payload,
            headers=headers,
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
    def _request_mock(self, method: str, url: str,
                      *args: Tuple, **kwargs: Dict) -> 'ClientResponse':
        """Return mocked response object or raise connection error."""
        response = self.match(method, url)
        if response is None:
            raise ClientConnectionError(
                'Connection refused: {} {}'.format(method, url)
            )
        return response
