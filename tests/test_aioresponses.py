# -*- coding: utf-8 -*-
import asyncio
import re
from asyncio import CancelledError, TimeoutError
from random import uniform
from unittest.mock import patch

import pytest
from aiohttp import hdrs, http
from aiohttp.client import ClientSession
from aiohttp.client_reqrep import ClientResponse
from multidict import CIMultiDict
from packaging.version import Version

try:
    from aiohttp.errors import (
        ClientConnectionError,
        ClientResponseError,
        HttpProcessingError,
    )
except ImportError:
    from aiohttp.client_exceptions import (
        ClientConnectionError,
        ClientResponseError,
    )
    from aiohttp.http_exceptions import HttpProcessingError

from aioresponses.compat import AIOHTTP_VERSION, URL
from aioresponses import CallbackResult, aioresponses

URL_EXAMPLE = 'http://example.com/api?foo=bar#fragment'
URL_REDIRECT = "http://10.1.1.1:8080/redirect"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
async def session():
    s = ClientSession()
    yield s
    result = s.close()
    if result is not None:
        await result


@pytest.fixture
async def session_raise_for_status():
    s = ClientSession(raise_for_status=True)
    yield s
    result = s.close()
    if result is not None:
        await result


# ---------------------------------------------------------------------------
# Shortcut methods
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("http_method", [
    hdrs.METH_HEAD,
    hdrs.METH_GET,
    hdrs.METH_POST,
    hdrs.METH_PUT,
    hdrs.METH_PATCH,
    hdrs.METH_DELETE,
    hdrs.METH_OPTIONS,
])
@patch('aioresponses.aioresponses.add')
def test_shortcut_method(mocked_add, http_method):
    with aioresponses() as m:
        getattr(m, http_method.lower())(URL_EXAMPLE)
        mocked_add.assert_called_once_with(URL_EXAMPLE, method=http_method)


# ---------------------------------------------------------------------------
# Basic response tests
# ---------------------------------------------------------------------------

async def test_returned_instance(session):
    with aioresponses() as m:
        m.get(URL_EXAMPLE)
        response = await session.get(URL_EXAMPLE)
    assert isinstance(response, ClientResponse)


async def test_returned_instance_and_status_code(session):
    with aioresponses() as m:
        m.get(URL_EXAMPLE, status=204)
        response = await session.get(URL_EXAMPLE)
    assert isinstance(response, ClientResponse)
    assert response.status == 204


@pytest.mark.parametrize("base_url,relative_url", [
    ("http://example.com", "/api?foo=bar#fragment"),
    ("http://example.com/", "/api?foo=bar#fragment"),
])
async def test_base_url(base_url, relative_url):
    with aioresponses() as m:
        m.get(URL_EXAMPLE, status=200)
        async with ClientSession(base_url=base_url) as s:
            response = await s.get(relative_url)
    assert response.status == 200


async def test_session_headers():
    with aioresponses() as m:
        m.get(URL_EXAMPLE)
        async with ClientSession(headers={"Authorization": "Bearer foobar"}) as s:
            response = await s.get(URL_EXAMPLE)

    assert response.status == 200
    key = ('GET', URL(URL_EXAMPLE))
    request = m.requests[key][0]
    assert request.kwargs["headers"]["Authorization"] == 'Bearer foobar'


async def test_returned_response_headers(session):
    with aioresponses() as m:
        m.get(URL_EXAMPLE, content_type='text/html', headers={'Connection': 'keep-alive'})
        response = await session.get(URL_EXAMPLE)
    assert response.headers['Connection'] == 'keep-alive'
    assert response.headers[hdrs.CONTENT_TYPE] == 'text/html'


async def test_returned_response_multidict_headers(session):
    header_name = 'x-custom-header'
    header_values = ['foo', 'bar']
    with aioresponses() as m:
        m.get(
            URL_EXAMPLE,
            content_type='text/html',
            headers=CIMultiDict([(header_name, v) for v in header_values]),
        )
        response = await session.get(URL_EXAMPLE)
    assert response.headers.getall(header_name) == header_values


async def test_returned_response_cookies(session):
    with aioresponses() as m:
        m.get(URL_EXAMPLE, headers={'Set-Cookie': 'cookie=value'})
        response = await session.get(URL_EXAMPLE)
    assert response.cookies['cookie'].value == 'value'


async def test_returned_response_raw_headers(session):
    with aioresponses() as m:
        m.get(URL_EXAMPLE, content_type='text/html', headers={'Connection': 'keep-alive'})
        response = await session.get(URL_EXAMPLE)
    expected = (
        (hdrs.CONTENT_TYPE.encode(), b'text/html'),
        (b'Connection', b'keep-alive'),
    )
    assert response.raw_headers == expected


async def test_raise_for_status(session):
    with aioresponses() as m:
        m.get(URL_EXAMPLE, status=400)
        response = await session.get(URL_EXAMPLE)
    with pytest.raises(ClientResponseError) as exc_info:
        response.raise_for_status()
    assert exc_info.value.message == http.RESPONSES[400][0]


async def test_request_raise_for_status(session):
    with aioresponses() as m:
        m.get(URL_EXAMPLE, status=400)
        with pytest.raises(ClientResponseError) as exc_info:
            await session.get(URL_EXAMPLE, raise_for_status=True)
    assert exc_info.value.message == http.RESPONSES[400][0]


async def test_returned_instance_and_params_handling(session):
    with aioresponses() as m:
        m.get('http://example.com/api?foo=bar&x=42#fragment')
        response = await session.get(URL_EXAMPLE, params={'x': 42})
        assert isinstance(response, ClientResponse)
        assert response.status == 200

        m.get('http://example.com/api?x=42#fragment')
        response = await session.get('http://example.com/api#fragment', params={'x': 42})
        assert isinstance(response, ClientResponse)
        assert response.status == 200
        assert len(m.requests) == 2

        with pytest.raises(AssertionError):
            m.assert_called_once()


async def test_method_dont_match(session):
    with aioresponses() as m:
        m.get(URL_EXAMPLE)
        with pytest.raises(ClientConnectionError):
            await session.post(URL_EXAMPLE)


async def test_post_with_data(session):
    body = {'foo': 'bar'}
    payload = {'spam': 'eggs'}
    user_agent = {'User-Agent': 'aioresponses'}

    with aioresponses() as m:
        m.post(URL_EXAMPLE, payload=payload, headers=dict(connection='keep-alive'), body=body)
        response = await session.post(URL_EXAMPLE, data=payload, headers=user_agent)
        assert isinstance(response, ClientResponse)
        assert response.status == 200
        assert await response.json() == payload

    m.assert_called_once_with(URL_EXAMPLE, method='POST', data=payload, headers=user_agent)

    with pytest.raises(AssertionError):
        m.assert_called_once_with(URL_EXAMPLE, method='POST', data=body, headers=user_agent)
    with pytest.raises(AssertionError):
        m.assert_called_once_with('http://httpbin.org/', method='POST', data=payload, headers=user_agent)
    with pytest.raises(AssertionError):
        m.assert_called_once_with(URL_EXAMPLE, method='POST', data=payload, headers={'User-Agent': 'aiorequest'})


async def test_post_with_data_selected_field_to_compare(session):
    body = {'foo': 'bar'}
    payload = {'spam': 'eggs'}
    user_agent = {'User-Agent': 'aioresponses'}

    with aioresponses() as m:
        m.post(URL_EXAMPLE, payload=payload, headers=dict(connection='keep-alive'), body=body)
        await session.post(URL_EXAMPLE, data=payload, headers=user_agent)

    m.assert_called_once_with(URL_EXAMPLE, method='POST', args_to_match=['data', 'headers'],
                              data=payload, headers=user_agent)
    m.assert_called_once_with(URL_EXAMPLE, method='POST', args_to_match=['data'], data=payload)
    m.assert_called_once_with(URL_EXAMPLE, method='POST', args_to_match=['headers'], headers=user_agent)
    m.assert_called_once_with(URL_EXAMPLE, method='POST', args_to_match=[])

    with pytest.raises(AssertionError):
        m.assert_called_once_with(URL_EXAMPLE, method='POST', args_to_match=['data', 'headers', 'body'],
                                  data=body, headers=user_agent)


# ---------------------------------------------------------------------------
# Streaming
# ---------------------------------------------------------------------------

async def test_streaming(session):
    with aioresponses() as m:
        m.get(URL_EXAMPLE, body='Test')
        resp = await session.get(URL_EXAMPLE)
        content = await resp.content.read()
    assert content == b'Test'


async def test_streaming_up_to(session):
    with aioresponses() as m:
        m.get(URL_EXAMPLE, body='Test')
        resp = await session.get(URL_EXAMPLE)
        part1 = await resp.content.read(2)
        part2 = await resp.content.read(2)
    assert part1 == b'Te'
    assert part2 == b'st'


async def test_binary_body(session):
    body = b'Invalid utf-8: \x95\x00\x85'
    with aioresponses() as m:
        m.get(URL_EXAMPLE, body=body)
        resp = await session.get(URL_EXAMPLE)
        content = await resp.read()
    assert content == body


async def test_binary_body_via_callback(session):
    body = b'\x00\x01\x02\x80\x81\x82\x83\x84\x85'

    def callback(url, **kwargs):
        return CallbackResult(body=body)

    with aioresponses() as m:
        m.get(URL_EXAMPLE, callback=callback)
        resp = await session.get(URL_EXAMPLE)
        content = await resp.read()
    assert content == body


# ---------------------------------------------------------------------------
# Context manager / decorator usage
# ---------------------------------------------------------------------------

async def test_mocking_as_context_manager(session):
    with aioresponses() as m:
        m.add(URL_EXAMPLE, payload={'foo': 'bar'})
        resp = await session.get(URL_EXAMPLE)
        assert resp.status == 200
        assert await resp.json() == {'foo': 'bar'}


def test_mocking_as_decorator():
    loop = asyncio.new_event_loop()

    @aioresponses()
    def foo(loop, m):
        m.add(URL_EXAMPLE, payload={'foo': 'bar'})

        async def run():
            async with ClientSession() as s:
                resp = await s.get(URL_EXAMPLE)
                assert resp.status == 200
                assert await resp.json() == {'foo': 'bar'}

        loop.run_until_complete(run())

    try:
        foo(loop)
    finally:
        loop.close()


async def test_passing_argument():
    @aioresponses(param='mocked')
    async def foo(mocked):
        mocked.add(URL_EXAMPLE, payload={'foo': 'bar'})
        resp = await ClientSession().get(URL_EXAMPLE)
        assert resp.status == 200

    await foo()


def test_mocking_as_decorator_wrong_mocked_arg_name():
    @aioresponses(param='foo')
    def foo(bar):
        pass

    with pytest.raises(TypeError, match="foo\\(\\) got an unexpected keyword argument 'foo'"):
        foo()


# ---------------------------------------------------------------------------
# Exception handling
# ---------------------------------------------------------------------------

async def test_unknown_request(session):
    with aioresponses() as m:
        m.add(URL_EXAMPLE, payload={'foo': 'bar'})
        with pytest.raises(ClientConnectionError):
            await session.get('http://example.com/foo')


async def test_raising_exception(session):
    cases = [
        ('http://example.com/Exception', Exception, Exception),
        ('http://example.com/Exception_obj', Exception(), Exception),
        ('http://example.com/BaseException', BaseException, BaseException),
        ('http://example.com/BaseException_obj', BaseException(), BaseException),
        ('http://example.com/CancelError', CancelledError, CancelledError),
        ('http://example.com/TimeoutError', TimeoutError, TimeoutError),
        ('http://example.com/HttpProcessingError',
         HttpProcessingError(message='foo'), HttpProcessingError),
    ]
    with aioresponses() as m:
        for url, exc, _ in cases:
            m.get(url, exception=exc)

        for url, _, exc_type in cases:
            with pytest.raises(exc_type):
                await session.get(url)

        callback_called = asyncio.Event()
        m.get('http://example.com/HttpProcessingError2',
              exception=HttpProcessingError(message='foo'),
              callback=lambda *_, **__: callback_called.set())
        with pytest.raises(HttpProcessingError):
            await session.get('http://example.com/HttpProcessingError2')
        await callback_called.wait()


# ---------------------------------------------------------------------------
# Request tracking
# ---------------------------------------------------------------------------

async def test_multiple_requests(session):
    with aioresponses() as m:
        m.get(URL_EXAMPLE, status=200)
        m.get(URL_EXAMPLE, status=201)
        m.get(URL_EXAMPLE, status=202)

        json_ref = [1]
        assert (await session.get(URL_EXAMPLE, json=json_ref)).status == 200
        json_ref[:] = [2]
        assert (await session.get(URL_EXAMPLE, json=json_ref)).status == 201
        json_ref[:] = [3]
        assert (await session.get(URL_EXAMPLE, json=json_ref)).status == 202

        key = ('GET', URL(URL_EXAMPLE))
        assert key in m.requests
        assert len(m.requests[key]) == 3
        assert m.requests[key][0].kwargs == {'allow_redirects': True, 'json': [1]}
        assert m.requests[key][1].kwargs == {'allow_redirects': True, 'json': [2]}
        assert m.requests[key][2].kwargs == {'allow_redirects': True, 'json': [3]}


async def test_request_with_non_deepcopyable_parameter(session):
    def non_deep_copyable():
        for line in ["header1,header2", "v1,v2", "v10,v20"]:
            yield line

    generator_value = non_deep_copyable()
    with aioresponses() as m:
        m.get(URL_EXAMPLE, status=200)
        resp = await session.get(URL_EXAMPLE, data=generator_value)
    assert resp.status == 200
    key = ('GET', URL(URL_EXAMPLE))
    assert m.requests[key][0].kwargs == {'allow_redirects': True, 'data': generator_value}


async def test_request_retrieval_in_case_no_response(session):
    with aioresponses() as m:
        with pytest.raises(ClientConnectionError):
            await session.get(URL_EXAMPLE)
    key = ('GET', URL(URL_EXAMPLE))
    assert key in m.requests
    assert m.requests[key][0].kwargs == {'allow_redirects': True}


async def test_request_failure_in_case_session_is_closed(session):
    async def do_request(s):
        return await s.get(URL_EXAMPLE)

    with aioresponses():
        coro = do_request(session)
        await session.close()
        with pytest.raises(RuntimeError, match="Session is closed"):
            await coro


async def test_exception_requests_are_tracked(session):
    kwargs = {"json": [42], "allow_redirects": True}
    with aioresponses() as m:
        m.get(URL_EXAMPLE, exception=ValueError('oops'))
        with pytest.raises(ValueError):
            await session.get(URL_EXAMPLE, **kwargs)
    key = ('GET', URL(URL_EXAMPLE))
    assert m.requests[key][0].kwargs == kwargs


# ---------------------------------------------------------------------------
# Passthrough
# ---------------------------------------------------------------------------

async def test_address_as_instance_of_url_combined_with_pass_through(session):
    external_api = 'http://httpbin.org/status/201'
    with aioresponses(passthrough=[external_api]) as m:
        m.get(URL_EXAMPLE, status=200)
        api_resp = await session.get(URL_EXAMPLE)
        ext_resp = await session.get(URL(external_api))
    assert api_resp.status == 200
    assert ext_resp.status == 201


async def test_pass_through_with_origin_params(session):
    external_api = 'http://httpbin.org/get'
    with aioresponses(passthrough=[external_api]):
        ext = await session.get(URL(external_api), params={'foo': 'bar'})
    assert ext.status == 200
    assert str(ext.url) == 'http://httpbin.org/get?foo=bar'


# ---------------------------------------------------------------------------
# Custom response class
# ---------------------------------------------------------------------------

async def test_custom_response_class(session):
    class CustomClientResponse(ClientResponse):
        pass

    with aioresponses() as m:
        m.get(URL_EXAMPLE, body='Test', response_class=CustomClientResponse)
        resp = await session.get(URL_EXAMPLE)
    assert isinstance(resp, CustomClientResponse)


# ---------------------------------------------------------------------------
# Exception sequencing
# ---------------------------------------------------------------------------

async def test_exceptions_in_the_middle_of_responses(session):
    with aioresponses() as m:
        m.get(URL_EXAMPLE, payload={}, status=204)
        m.get(URL_EXAMPLE, exception=ValueError('oops'))
        m.get(URL_EXAMPLE, payload={}, status=204)
        m.get(URL_EXAMPLE, exception=ValueError('oops'))
        m.get(URL_EXAMPLE, payload={}, status=200)

        assert (await session.get(URL_EXAMPLE)).status == 204
        with pytest.raises(ValueError):
            await session.get(URL_EXAMPLE)
        assert (await session.get(URL_EXAMPLE)).status == 204
        with pytest.raises(ValueError):
            await session.get(URL_EXAMPLE)
        assert (await session.get(URL_EXAMPLE)).status == 200


# ---------------------------------------------------------------------------
# Regexp matching
# ---------------------------------------------------------------------------

async def test_request_should_match_regexp(session):
    with aioresponses() as m:
        m.get(re.compile(r'^http://example\.com/api\?foo=.*$'), payload={}, status=200)
        response = await session.get(URL_EXAMPLE)
    assert response.status == 200


async def test_request_does_not_match_regexp(session):
    with aioresponses() as m:
        m.get(re.compile(r'^http://exampleexample\.com/api\?foo=.*$'), payload={}, status=200)
        with pytest.raises(ClientConnectionError):
            await session.get(URL_EXAMPLE)


# ---------------------------------------------------------------------------
# Timeout
# ---------------------------------------------------------------------------

async def test_timeout(session):
    with aioresponses() as m:
        m.get(URL_EXAMPLE, timeout=True)
        with pytest.raises(asyncio.TimeoutError):
            await session.get(URL_EXAMPLE)


# ---------------------------------------------------------------------------
# Callbacks
# ---------------------------------------------------------------------------

async def test_callback(session):
    body = b'New body'

    def callback(url, **kwargs):
        assert str(url) == URL_EXAMPLE
        assert kwargs == {'allow_redirects': True}
        return CallbackResult(body=body)

    with aioresponses() as m:
        m.get(URL_EXAMPLE, callback=callback)
        response = await session.get(URL_EXAMPLE)
        data = await response.read()
    assert data == body


async def test_callback_coroutine(session):
    body = b'New body'
    event = asyncio.Event()

    async def callback(url, **kwargs):
        await event.wait()
        return CallbackResult(body=body)

    with aioresponses() as m:
        m.get(URL_EXAMPLE, callback=callback)
        future = asyncio.ensure_future(session.get(URL_EXAMPLE))
        await asyncio.wait([future], timeout=0)
        assert not future.done()
        event.set()
        await asyncio.wait([future], timeout=0)
        assert future.done()
        data = await (await future).read()
    assert data == body


# ---------------------------------------------------------------------------
# Assert helpers
# ---------------------------------------------------------------------------

async def test_assert_not_called(session):
    with aioresponses() as m:
        m.get(URL_EXAMPLE)
        m.assert_not_called()
        await session.get(URL_EXAMPLE)
        with pytest.raises(AssertionError):
            m.assert_not_called()


async def test_assert_called(session):
    with aioresponses() as m:
        m.get(URL_EXAMPLE)
        with pytest.raises(AssertionError):
            m.assert_called()
        await session.get(URL_EXAMPLE)

        m.assert_called_once()
        m.assert_called_once_with(URL_EXAMPLE)
        m.assert_called_with(URL_EXAMPLE)
        with pytest.raises(AssertionError):
            m.assert_not_called()
        with pytest.raises(AssertionError):
            m.assert_called_with("http://foo.bar")


async def test_assert_called_twice(session):
    with aioresponses() as m:
        m.get(URL_EXAMPLE, repeat=True)
        m.assert_not_called()
        await session.get(URL_EXAMPLE)
        await session.get(URL_EXAMPLE)
        with pytest.raises(AssertionError):
            m.assert_called_once()


async def test_integer_repeat_once(session):
    with aioresponses() as m:
        m.get(URL_EXAMPLE, repeat=1)
        await session.get(URL_EXAMPLE)
        with pytest.raises(ClientConnectionError):
            await session.get(URL_EXAMPLE)


async def test_integer_repeat_twice(session):
    with aioresponses() as m:
        m.get(URL_EXAMPLE, repeat=2)
        await session.get(URL_EXAMPLE)
        await session.get(URL_EXAMPLE)
        with pytest.raises(ClientConnectionError):
            await session.get(URL_EXAMPLE)


async def test_assert_any_call(session):
    http_bin_url = "http://httpbin.org"
    with aioresponses() as m:
        m.get(URL_EXAMPLE)
        m.get(http_bin_url)
        await session.get(URL_EXAMPLE)
        response = await session.get(http_bin_url)
    assert response.status == 200
    m.assert_any_call(URL_EXAMPLE)
    m.assert_any_call(http_bin_url)


async def test_assert_any_call_not_called(session):
    http_bin_url = "http://httpbin.org"
    with aioresponses() as m:
        m.get(URL_EXAMPLE)
        response = await session.get(URL_EXAMPLE)
    assert response.status == 200
    m.assert_any_call(URL_EXAMPLE)
    with pytest.raises(AssertionError):
        m.assert_any_call(http_bin_url)


# ---------------------------------------------------------------------------
# Race condition
# ---------------------------------------------------------------------------

async def test_possible_race_condition(session):
    async def random_sleep_cb(url, **kwargs):
        await asyncio.sleep(uniform(0.1, 1))
        return CallbackResult(body='test')

    with aioresponses() as m:
        for i in range(20):
            m.get(f'http://example.org/id-{i}', callback=random_sleep_cb)
        await asyncio.gather(*[session.get(f'http://example.org/id-{i}') for i in range(20)])


# ---------------------------------------------------------------------------
# raise_for_status session
# ---------------------------------------------------------------------------

async def test_session_raise_for_status(session_raise_for_status):
    with aioresponses() as m:
        m.get(URL_EXAMPLE, status=400)
        with pytest.raises(ClientResponseError) as exc_info:
            await session_raise_for_status.get(URL_EXAMPLE)
    assert exc_info.value.message == http.RESPONSES[400][0]


async def test_session_do_not_raise_for_status(session_raise_for_status):
    with aioresponses() as m:
        m.get(URL_EXAMPLE, status=400)
        response = await session_raise_for_status.get(URL_EXAMPLE, raise_for_status=False)
    assert response.status == 400


@pytest.mark.skipif(
    AIOHTTP_VERSION < Version('3.9.0'),
    reason='aiohttp<3.9.0 does not support callable raise_for_status',
)
async def test_session_callable_raise_for_status(session_raise_for_status):
    async def raise_for_status(response: ClientResponse):
        if response.status >= 400:
            raise Exception("callable raise_for_status")

    with aioresponses() as m:
        m.get(URL_EXAMPLE, status=400)
        with pytest.raises(Exception, match="callable raise_for_status"):
            await session_raise_for_status.get(URL_EXAMPLE, raise_for_status=raise_for_status)


# ---------------------------------------------------------------------------
# Redirect tests
# ---------------------------------------------------------------------------

async def test_redirect_followed():
    with aioresponses() as m:
        m.get(URL_REDIRECT, status=307, headers={"Location": "https://httpbin.org"})
        m.get("https://httpbin.org")
        async with ClientSession() as s:
            response = await s.get(URL_REDIRECT, allow_redirects=True)
    assert response.status == 200
    assert str(response.url) == "https://httpbin.org"
    assert len(response.history) == 1
    assert str(response.history[0].url) == URL_REDIRECT


async def test_post_redirect_followed():
    with aioresponses() as m:
        m.post(URL_REDIRECT, status=307, headers={"Location": "https://httpbin.org"})
        m.get("https://httpbin.org")
        async with ClientSession() as s:
            response = await s.post(URL_REDIRECT, allow_redirects=True)
    assert response.status == 200
    assert str(response.url) == "https://httpbin.org"
    assert response.method == "get"
    assert len(response.history) == 1


async def test_redirect_missing_mocked_match():
    with aioresponses() as m:
        m.get(URL_REDIRECT, status=307, headers={"Location": "https://httpbin.org"})
        async with ClientSession() as s:
            with pytest.raises(ClientConnectionError, match=f'Connection refused: GET {URL_REDIRECT}'):
                await s.get(URL_REDIRECT, allow_redirects=True)


async def test_redirect_missing_location_header():
    with aioresponses() as m:
        m.get(URL_REDIRECT, status=307)
        async with ClientSession() as s:
            response = await s.get(URL_REDIRECT, allow_redirects=True)
    assert str(response.url) == URL_REDIRECT


async def test_request_info():
    with aioresponses() as m:
        m.get(URL_REDIRECT, status=200)
        async with ClientSession() as s:
            response = await s.get(URL_REDIRECT)
    assert str(response.request_info.url) == URL_REDIRECT
    assert response.request_info.headers == {}


async def test_request_info_with_original_request_headers():
    headers = {"Authorization": "Bearer access-token"}
    with aioresponses() as m:
        m.get(URL_REDIRECT, status=200)
        async with ClientSession() as s:
            response = await s.get(URL_REDIRECT, headers=headers)
    assert str(response.request_info.url) == URL_REDIRECT
    assert response.request_info.headers == headers


async def test_relative_url_redirect_followed():
    base_url = "https://httpbin.org"
    url = f"{base_url}/foo/bar"
    with aioresponses() as m:
        m.get(url, status=307, headers={"Location": "../baz"})
        m.get(f"{base_url}/baz")
        async with ClientSession() as s:
            response = await s.get(url, allow_redirects=True)
    assert response.status == 200
    assert str(response.url) == f"{base_url}/baz"
    assert len(response.history) == 1
    assert str(response.history[0].url) == url


async def test_pass_through_unmatched_requests():
    matched_url = "https://matched_example.org"
    unmatched_url = "https://httpbin.org/get"
    async with ClientSession() as s:
        with aioresponses(passthrough_unmatched=True) as m:
            m.post(URL(matched_url), status=200)
            mocked_resp = await s.post(URL(matched_url))
            response = await s.get(URL(unmatched_url), params={'foo': 'bar'})
    assert response.status == 200
    assert str(response.url) == 'https://httpbin.org/get?foo=bar'
    assert mocked_resp.status == 200

