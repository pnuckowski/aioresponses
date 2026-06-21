import asyncio
import copy
import inspect
import json
from collections.abc import Callable, Mapping, Sequence
from functools import wraps
from typing import Any, NamedTuple, TypeVar, cast
from unittest.mock import Mock, patch
from uuid import uuid4

from aiohttp import (
    ClientConnectionError,
    ClientResponse,
    ClientSession,
    RequestInfo,
    hdrs,
    http,
    typedefs,
)
from aiohttp.helpers import TimerNoop
from multidict import CIMultiDict, CIMultiDictProxy, MultiDict, MultiDictProxy
from packaging.version import Version

from .compat import (
    AIOHTTP_VERSION,
    URL,
    Pattern,
    merge_params,
    normalize_url,
    stream_reader_factory,
)

_FuncT = TypeVar("_FuncT", bound=Callable[..., Any])


class CallbackResult:
    def __init__(
        self,
        method: str = hdrs.METH_GET,
        status: int = 200,
        body: str | bytes = "",
        content_type: str = "application/json",
        payload: dict | None = None,
        headers: dict | None = None,
        response_class: type[ClientResponse] | None = None,
        reason: str | None = None,
    ):
        self.method = method
        self.status = status
        self.body = body
        self.content_type = content_type
        self.payload = payload
        self.headers = headers
        self.response_class = response_class
        self.reason = reason


class RequestMatch:
    url_or_pattern: URL | Pattern | None = None

    def __init__(
        self,
        url: URL | str | Pattern,
        method: str = hdrs.METH_GET,
        status: int = 200,
        body: str | bytes = "",
        payload: dict | None = None,
        exception: Exception | None = None,
        headers: CIMultiDict | dict | None = None,
        content_type: str = "application/json",
        response_class: type[ClientResponse] | None = None,
        timeout: bool = False,
        repeat: bool | int = False,
        reason: str | None = None,
        callback: Callable | None = None,
    ):
        if isinstance(url, Pattern):
            self.url_or_pattern = url
            self.match_func = self.match_regexp
        else:
            self.url_or_pattern = normalize_url(url)
            self.match_func = self.match_str
        self.method = method.lower()
        self.status = status
        self.body = body
        self.payload = payload
        self.exception = exception
        if timeout:
            self.exception = asyncio.TimeoutError("Connection timeout test")
        if headers is None:
            self.headers = CIMultiDict()
        elif isinstance(headers, dict):
            self.headers = CIMultiDict(headers)
        else:
            self.headers = headers
        self.content_type = content_type
        self.response_class = response_class
        self.repeat = repeat
        self.reason = reason
        if self.reason is None:
            try:
                self.reason = http.RESPONSES[self.status][0]
            except (IndexError, KeyError):
                self.reason = ""
        self.callback = callback

    def match_str(self, url: URL) -> bool:
        return self.url_or_pattern == url

    def match_regexp(self, url: URL) -> bool:
        return bool(
            self.url_or_pattern.match(str(url))  # type: ignore[union-attr]
        )

    def match(self, method: str, url: URL) -> bool:
        if self.method != method.lower():
            return False
        return self.match_func(url)

    def _build_raw_headers(self, headers: Mapping[str, str]) -> tuple:
        """
        Convert a multidict of headers to a tuple of tuples.

        Mimics the format of ClientResponse.
        """
        raw_headers = []
        for k, v in headers.items():
            raw_headers.append((k.encode("utf8"), v.encode("utf8")))
        return tuple(raw_headers)

    def _prepare_request_headers(self, headers: typedefs.LooseHeaders | None) -> "CIMultiDict[str]":
        """Convert headers from aiohttp _request method to CIMultiDict."""
        result = CIMultiDict()
        if headers:
            if not isinstance(headers, (MultiDictProxy, MultiDict)):
                headers = CIMultiDict(headers)
            added_names: set[str] = set()
            for key, value in headers.items():
                if key in added_names:
                    result.add(key, value)
                else:
                    result[key] = value
                    added_names.add(key)
        return result

    def _build_response(
        self,
        url: URL | str,
        method: str = hdrs.METH_GET,
        request_headers: typedefs.LooseHeaders | None = None,
        status: int = 200,
        body: str | bytes = "",
        content_type: str = "application/json",
        payload: dict | None = None,
        headers: CIMultiDict | None = None,
        response_class: type[ClientResponse] | None = None,
        reason: str | None = None,
    ) -> ClientResponse:
        if response_class is None:
            response_class = ClientResponse
        if payload is not None:
            body = json.dumps(payload)
        if not isinstance(body, bytes):
            body = str.encode(body)
        if request_headers is None:
            request_headers = CIMultiDict()
        loop = Mock()
        loop.get_debug = Mock()
        loop.get_debug.return_value = True
        kwargs: dict[str, Any] = {}
        kwargs["request_info"] = RequestInfo(
            url=url,
            method=method,
            headers=CIMultiDictProxy(self._prepare_request_headers(request_headers)),
            real_url=url,
        )
        kwargs["writer"] = None
        # aiohttp 3.14 added a required keyword-only ``stream_writer`` argument
        # to ``ClientResponse.__init__``. It is only consulted for its
        # ``output_size`` attribute, so a lightweight mock is sufficient. The
        # signature check keeps this a no-op on aiohttp < 3.14.
        if "stream_writer" in inspect.signature(response_class).parameters:
            kwargs["stream_writer"] = Mock(output_size=0)
        kwargs["continue100"] = None
        kwargs["timer"] = TimerNoop()
        kwargs["traces"] = []
        kwargs["loop"] = loop
        kwargs["session"] = None

        _headers = CIMultiDict({hdrs.CONTENT_TYPE: content_type})
        if headers:
            _headers.update(headers)
        raw_headers = self._build_raw_headers(_headers)
        resp = response_class(method, url, **kwargs)

        for hdr in _headers.getall(hdrs.SET_COOKIE, ()):
            resp.cookies.load(hdr)

        resp._headers = _headers
        resp._raw_headers = raw_headers

        resp.status = status
        resp.reason = reason
        resp.content = stream_reader_factory(loop)
        resp.content.feed_data(body)
        resp.content.feed_eof()
        return resp

    async def build_response(self, url: URL, **kwargs: Any) -> ClientResponse | Exception:
        if callable(self.callback):
            if inspect.iscoroutinefunction(self.callback):
                result = await self.callback(url, **kwargs)
            else:
                result = self.callback(url, **kwargs)
        else:
            result = None

        if self.exception is not None:
            return self.exception

        result = self if result is None else result
        resp = self._build_response(
            url=url,
            method=result.method,
            request_headers=kwargs.get("headers"),
            status=result.status,
            body=result.body,
            content_type=result.content_type,
            payload=result.payload,
            headers=result.headers,
            response_class=result.response_class,
            reason=result.reason,
        )
        return resp

    def __repr__(self) -> str:
        return f"RequestMatch('{self.url_or_pattern}')"


class RequestCall(NamedTuple):
    args: tuple
    kwargs: dict


class aioresponses:
    """Mock aiohttp requests made by ClientSession."""

    _matches: dict[str, RequestMatch] | None = None
    _responses: list[ClientResponse] | None = None
    requests: dict[tuple[str, URL], list[RequestCall]] | None = None

    def __init__(self, **kwargs: Any):
        self._param = kwargs.pop("param", None)
        self._passthrough = kwargs.pop("passthrough", [])
        self.passthrough_unmatched = kwargs.pop("passthrough_unmatched", False)
        self.patcher = patch(
            "aiohttp.client.ClientSession._request",
            side_effect=self._request_mock,
            autospec=True,
        )
        self.requests = {}

    def __enter__(self) -> "aioresponses":
        self.start()
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.stop()

    async def __aenter__(self) -> "aioresponses":
        self.start()
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.stop()

    def __call__(self, f: _FuncT) -> _FuncT:
        def _pack_arguments(ctx, *args, **kwargs) -> tuple[tuple, dict]:
            if self._param:
                kwargs[self._param] = ctx
            else:
                args += (ctx,)
            return args, kwargs

        if inspect.iscoroutinefunction(f):

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

        return cast(_FuncT, wrapped)

    def clear(self) -> None:
        self._responses.clear()
        self._matches.clear()

    def start(self) -> None:
        self._responses = []
        self._matches = {}
        self.patcher.start()
        self.patcher.return_value = self._request_mock

    def stop(self) -> None:
        for response in self._responses:
            response.close()
        self.patcher.stop()
        self.clear()

    def head(self, url: URL | str | Pattern, **kwargs: Any) -> None:
        self.add(url, method=hdrs.METH_HEAD, **kwargs)

    def get(self, url: URL | str | Pattern, **kwargs: Any) -> None:
        self.add(url, method=hdrs.METH_GET, **kwargs)

    def post(self, url: URL | str | Pattern, **kwargs: Any) -> None:
        self.add(url, method=hdrs.METH_POST, **kwargs)

    def put(self, url: URL | str | Pattern, **kwargs: Any) -> None:
        self.add(url, method=hdrs.METH_PUT, **kwargs)

    def patch(self, url: URL | str | Pattern, **kwargs: Any) -> None:
        self.add(url, method=hdrs.METH_PATCH, **kwargs)

    def delete(self, url: URL | str | Pattern, **kwargs: Any) -> None:
        self.add(url, method=hdrs.METH_DELETE, **kwargs)

    def options(self, url: URL | str | Pattern, **kwargs: Any) -> None:
        self.add(url, method=hdrs.METH_OPTIONS, **kwargs)

    def add(
        self,
        url: URL | str | Pattern,
        method: str = hdrs.METH_GET,
        status: int = 200,
        body: str | bytes = "",
        exception: Exception | None = None,
        content_type: str = "application/json",
        payload: dict | None = None,
        headers: CIMultiDict | dict | None = None,
        response_class: type[ClientResponse] | None = None,
        repeat: bool | int = False,
        timeout: bool = False,
        reason: str | None = None,
        callback: Callable | None = None,
    ) -> None:
        self._matches[str(uuid4())] = RequestMatch(
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
            callback=callback,
        )

    def _format_call_signature(self, *args: Any, **kwargs: Any) -> str:
        message = f"{self.__class__.__name__}(%s)" or "mock"
        formatted_args = ""
        args_string = ", ".join([repr(arg) for arg in args])
        kwargs_string = ", ".join([f"{key}={value!r}" for key, value in kwargs.items()])
        if args_string:
            formatted_args = args_string
        if kwargs_string:
            if formatted_args:
                formatted_args += ", "
            formatted_args += kwargs_string
        return message % formatted_args

    def assert_not_called(self) -> None:
        """Assert that the mock was never called."""
        if len(self.requests) != 0:
            msg = f"Expected '{self.__class__.__name__}' to not have been called. Called {len(self._responses)} times."
            raise AssertionError(msg)

    def assert_called(self) -> None:
        """Assert that the mock was called at least once."""
        if len(self.requests) == 0:
            msg = f"Expected '{self.__class__.__name__}' to have been called."
            raise AssertionError(msg)

    def assert_called_once(self) -> None:
        """Assert that the mock was called only once."""
        call_count = len(self.requests)
        if call_count == 1:
            call_count = len(list(self.requests.values())[0])
        if not call_count == 1:
            msg = f"Expected '{self.__class__.__name__}' to have been called once. Called {call_count} times."
            raise AssertionError(msg)

    def assert_called_with(
        self,
        url: URL | str | Pattern,
        method: str = hdrs.METH_GET,
        args_to_match: Sequence[str] | None = None,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        """Assert that the last call was made with the specified arguments."""
        url = normalize_url(merge_params(url, kwargs.get("params")))
        method = method.upper()
        key = (method, url)

        if not self.requests.get(key):
            raise AssertionError(f"{self._format_call_signature(url, *args, **kwargs, method=method)} call not found")

        actual = self.requests[key][-1]
        expected = self._build_request_call(method, *args, **kwargs)

        if args_to_match is not None:
            raise_error = any(
                arg not in actual.kwargs or actual.kwargs[arg] != expected.kwargs[arg] for arg in args_to_match
            )
        else:
            raise_error = actual != expected

        if raise_error:
            raise AssertionError(f"{self._format_call_signature(actual)} != {self._format_call_signature(expected)}")

    def assert_any_call(
        self,
        url: URL | str | Pattern,
        method: str = hdrs.METH_GET,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        """Assert the mock has been called with the specified arguments at least once."""
        url = normalize_url(merge_params(url, kwargs.get("params")))
        method = method.upper()
        key = (method, url)

        try:
            self.requests[key]
        except KeyError as exc:
            expected_string = self._format_call_signature(
                url,
                *args,
                **kwargs,
                method=method,
            )
            raise AssertionError(f"{expected_string} call not found") from exc

    def assert_called_once_with(self, *args: Any, **kwargs: Any) -> None:
        """Assert that the mock was called exactly once with the specified arguments."""
        self.assert_called_once()
        self.assert_called_with(*args, **kwargs)

    @staticmethod
    def is_exception(resp_or_exc: ClientResponse | Exception) -> bool:
        if inspect.isclass(resp_or_exc):
            parent_classes = set(inspect.getmro(resp_or_exc))
            if {Exception, BaseException} & parent_classes:
                return True
        else:
            if isinstance(resp_or_exc, (Exception, BaseException)):
                return True
        return False

    async def match(
        self,
        method: str,
        url: URL,
        allow_redirects: bool = True,
        **kwargs: Any,
    ) -> ClientResponse | None:
        history = []
        while True:
            for _key, matcher in self._matches.items():
                if matcher.match(method, url):
                    response_or_exc = await matcher.build_response(url, allow_redirects=allow_redirects, **kwargs)
                    break
            else:
                return None

            if isinstance(matcher.repeat, bool):
                if not matcher.repeat:
                    del self._matches[_key]
            else:
                if matcher.repeat == 1:
                    del self._matches[_key]
                matcher.repeat -= 1

            if self.is_exception(response_or_exc):
                raise response_or_exc
            response: ClientResponse = response_or_exc  # type: ignore[assignment]
            is_redirect = response.status in (301, 302, 303, 307, 308)
            if is_redirect and allow_redirects:
                if hdrs.LOCATION not in response.headers:
                    break
                history.append(response)
                redirect_url = URL(response.headers[hdrs.LOCATION])
                if redirect_url.is_absolute():
                    url = redirect_url
                else:
                    url = url.join(redirect_url)
                method = "get"
                continue
            else:
                break

        response._history = tuple(history)
        return response

    async def _request_mock(
        self,
        orig_self: ClientSession,
        method: str,
        url: URL | str,
        *args: Any,
        **kwargs: Any,
    ) -> ClientResponse:
        """Return mocked response object or raise connection error."""
        data = kwargs.get("data", None)
        if data is not None and hasattr(data, "__aiter__"):
            chunks = []
            async for chunk in data:
                chunks.append(chunk)
            kwargs["data"] = b"".join(chunks)

        if orig_self.closed:
            raise RuntimeError("Session is closed")

        if AIOHTTP_VERSION >= Version("3.8.0"):
            url = orig_self._build_url(url)
            url_origin = str(url)
            if orig_self.headers:
                kwargs["headers"] = orig_self._prepare_headers(kwargs.get("headers"))
        else:
            url_origin = url

        url = normalize_url(merge_params(url, kwargs.get("params")))
        url_str = str(url)
        for prefix in self._passthrough:
            if url_str.startswith(prefix):
                return await self.patcher.temp_original(orig_self, method, url_origin, *args, **kwargs)

        key = (method, url)
        self.requests.setdefault(key, [])
        request_call = self._build_request_call(method, *args, **kwargs)
        self.requests[key].append(request_call)

        response = await self.match(method, url, **kwargs)

        if response is None:
            if self.passthrough_unmatched:
                return await self.patcher.temp_original(orig_self, method, url_origin, *args, **kwargs)
            raise ClientConnectionError(f"Connection refused: {method} {url}")
        self._responses.append(response)

        raise_for_status = kwargs.get("raise_for_status")
        if raise_for_status is None:
            raise_for_status = getattr(orig_self, "_raise_for_status", False)

        if callable(raise_for_status):
            await raise_for_status(response)
        elif raise_for_status:
            response.raise_for_status()

        return response

    def _build_request_call(
        self,
        method: str = hdrs.METH_GET,
        *args: Any,
        allow_redirects: bool = True,
        **kwargs: Any,
    ) -> RequestCall:
        """Return request call."""
        kwargs.setdefault("allow_redirects", allow_redirects)
        if method == "POST":
            kwargs.setdefault("data", None)

        try:
            kwargs_copy = copy.deepcopy(kwargs)
        except (TypeError, ValueError):
            kwargs_copy = kwargs
        return RequestCall(args, kwargs_copy)
