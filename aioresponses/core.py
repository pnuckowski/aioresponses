# -*- coding: utf-8 -*-
import asyncio
import json
from collections import namedtuple
from distutils.version import StrictVersion
from functools import wraps
from typing import Dict, Tuple, Union, Optional, List  # noqa
from unittest.mock import Mock, patch

from aiohttp import (
    ClientConnectionError,
    ClientResponse,
    ClientSession,
    hdrs,
    http
)
from aiohttp.helpers import TimerNoop
from multidict import CIMultiDict

from .compat import (
    URL,
    Pattern,
    stream_reader_factory,
    merge_params,
    normalize_url,
    AIOHTTP_VERSION
)


class RequestMatch(object):
    url_or_pattern = None  # type: Union[URL, Pattern]

    def __init__(self, url: Union[str, Pattern],
                 method: str = hdrs.METH_GET,
                 status: int = 200,
                 body: str = '',
                 payload: Dict = None,
                 exception: 'Exception' = None,
                 headers: Dict = None,
                 content_type: str = 'application/json',
                 response_class: 'ClientResponse' = None,
                 timeout: bool = False,
                 repeat: bool = False,
                 reason: Optional[str] = None):
        if isinstance(url, Pattern):
            self.url_or_pattern = url
            self.match_func = self.match_regexp
        else:
            self.url_or_pattern = normalize_url(url)
            self.match_func = self.match_str
        self.method = method.lower()
        self.status = status
        if payload is not None:
            body = json.dumps(payload)
        if not isinstance(body, bytes):
            body = str.encode(body)
        self.body = body
        self.exception = exception
        if timeout:
            self.exception = asyncio.TimeoutError('Connection timeout test')
        self.headers = headers
        self.content_type = content_type
        self.response_class = response_class or ClientResponse
        self.repeat = repeat
        self.reason = reason
        if self.reason is None:
            try:
                self.reason = http.RESPONSES[self.status][0]
            except (IndexError, KeyError):
                self.reason = ''

    def match_str(self, url: URL) -> bool:
        return self.url_or_pattern == url

    def match_regexp(self, url: URL) -> bool:
        return bool(self.url_or_pattern.match(str(url)))

    def match(self, method: str, url: URL) -> bool:
        if self.method != method.lower():
            return False
        return self.match_func(url)

    async def build_response(
            self, url: URL
    ) -> 'Union[ClientResponse, Exception]':
        if isinstance(self.exception, Exception):
            return self.exception
        kwargs = {}
        if AIOHTTP_VERSION >= StrictVersion('3.1.0'):
            loop = Mock()
            loop.get_debug = Mock()
            loop.get_debug.return_value = True
            kwargs['request_info'] = Mock()
            kwargs['writer'] = Mock()
            kwargs['continue100'] = None
            kwargs['timer'] = TimerNoop()
            if AIOHTTP_VERSION >= StrictVersion('3.3.0'):
                pass
            else:
                kwargs['auto_decompress'] = True
            kwargs['traces'] = []
            kwargs['loop'] = loop
            kwargs['session'] = None
        resp = self.response_class(self.method, url, **kwargs)
        # we need to initialize headers manually
        headers = CIMultiDict({hdrs.CONTENT_TYPE: self.content_type})
        if self.headers:
            headers.update(self.headers)
        raw_headers = self._build_raw_headers(headers)
        if AIOHTTP_VERSION >= StrictVersion('3.3.0'):
            # Reified attributes
            resp._headers = headers
            resp._raw_headers = raw_headers
        else:
            resp.headers = headers
            resp.raw_headers = raw_headers
        resp.status = self.status
        resp.reason = self.reason
        resp.content = stream_reader_factory()
        resp.content.feed_data(self.body)
        resp.content.feed_eof()
        return resp

    def _build_raw_headers(self, headers: Dict) -> Tuple:
        """
        Convert a dict of headers to a tuple of tuples

        Mimics the format of ClientResponse.
        """
        raw_headers = []
        for k, v in headers.items():
            raw_headers.append((k.encode('utf8'), v.encode('utf8')))
        return tuple(raw_headers)


RequestCall = namedtuple('RequestCall', ['args', 'kwargs'])


class aioresponses(object):
    """Mock aiohttp requests made by ClientSession."""
    _matches = None  # type: List[RequestMatch]
    _responses = None  # type: List[ClientResponse]
    requests = None  # type: Dict

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
            async def wrapped(*args, **kwargs):
                with self as ctx:
                    args, kwargs = _pack_arguments(ctx, *args, **kwargs)
                    return await f(*args, **kwargs)
        else:
            @wraps(f)
            def wrapped(*args, **kwargs):
                with self as ctx:
                    args, kwargs = _pack_arguments(ctx, *args, **kwargs)
                    return f(*args, **kwargs)
        return wrapped

    def clear(self):
        self._responses.clear()
        self._matches.clear()

    def start(self):
        self._responses = []
        self._matches = []
        self.patcher.start()
        self.patcher.return_value = self._request_mock

    def stop(self) -> None:
        for response in self._responses:
            response.close()
        self.patcher.stop()
        self.clear()

    def head(self, url: 'Union[URL, str]', **kwargs):
        self.add(url, method=hdrs.METH_HEAD, **kwargs)

    def get(self, url: 'Union[URL, str]', **kwargs):
        self.add(url, method=hdrs.METH_GET, **kwargs)

    def post(self, url: 'Union[URL, str]', **kwargs):
        self.add(url, method=hdrs.METH_POST, **kwargs)

    def put(self, url: 'Union[URL, str]', **kwargs):
        self.add(url, method=hdrs.METH_PUT, **kwargs)

    def patch(self, url: 'Union[URL, str]', **kwargs):
        self.add(url, method=hdrs.METH_PATCH, **kwargs)

    def delete(self, url: 'Union[URL, str]', **kwargs):
        self.add(url, method=hdrs.METH_DELETE, **kwargs)

    def options(self, url: 'Union[URL, str]', **kwargs):
        self.add(url, method=hdrs.METH_OPTIONS, **kwargs)

    def add(self, url: 'Union[URL, str]', method: str = hdrs.METH_GET,
            status: int = 200,
            body: str = '',
            exception: 'Exception' = None,
            content_type: str = 'application/json',
            payload: Dict = None,
            headers: Dict = None,
            response_class: 'ClientResponse' = None,
            repeat: bool = False,
            timeout: bool = False,
            reason: Optional[str] = None) -> None:
        self._matches.append(RequestMatch(
            url,
            method=method,
            status=status,
            content_type=content_type,
            body=body,
            exception=exception,
            payload=payload,
            headers=headers,
            response_class=response_class,
            repeat=repeat,
            timeout=timeout,
            reason=reason,
        ))

    async def match(self, method: str, url: URL) -> Optional['ClientResponse']:
        for i, matcher in enumerate(self._matches):
            if matcher.match(method, url):
                response = await matcher.build_response(url)
                break
        else:
            return None

        if matcher.repeat is False:
            del self._matches[i]
        if isinstance(response, Exception):
            raise response
        return response

    async def _request_mock(self, orig_self: ClientSession,
                            method: str, url: 'Union[URL, str]',
                            *args: Tuple,
                            **kwargs: Dict) -> 'ClientResponse':
        """Return mocked response object or raise connection error."""
        url = normalize_url(merge_params(url, kwargs.get('params')))
        url_str = str(url)
        for prefix in self._passthrough:
            if url_str.startswith(prefix):
                return (await self.patcher.temp_original(
                    orig_self, method, url, *args, **kwargs
                ))

        response = await self.match(method, url)
        if response is None:
            raise ClientConnectionError(
                'Connection refused: {} {}'.format(method, url)
            )
        self._responses.append(response)
        key = (method, url)
        self.requests.setdefault(key, [])
        self.requests[key].append(RequestCall(args, kwargs))
        return response
