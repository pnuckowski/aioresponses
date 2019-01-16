# -*- coding: utf-8 -*-
import asyncio
import re
from typing import Coroutine, Generator, Union
from unittest.mock import patch

from aiohttp import hdrs
from aiohttp import http
from aiohttp.client import ClientSession
from aiohttp.client_reqrep import ClientResponse
from asynctest import fail_on
from asynctest.case import TestCase
from ddt import ddt, data

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

from aioresponses.compat import URL
from aioresponses import aioresponses


@ddt
class AIOResponsesTestCase(TestCase):
    use_default_loop = False

    @asyncio.coroutine
    def setUp(self):
        self.url = 'http://example.com/api?foo=bar#fragment'
        self.session = ClientSession()
        super().setUp()

    @asyncio.coroutine
    def tearDown(self):
        close_result = self.session.close()
        if close_result is not None:
            yield from close_result
        super().tearDown()

    def run_async(self, coroutine: Union[Coroutine, Generator]):
        return self.loop.run_until_complete(coroutine)

    @asyncio.coroutine
    def request(self, url: str):
        return (yield from self.session.get(url))

    @data(
        hdrs.METH_HEAD,
        hdrs.METH_GET,
        hdrs.METH_POST,
        hdrs.METH_PUT,
        hdrs.METH_PATCH,
        hdrs.METH_DELETE,
        hdrs.METH_OPTIONS,
    )
    @patch('aioresponses.aioresponses.add')
    @fail_on(unused_loop=False)
    def test_shortcut_method(self, http_method, mocked):
        with aioresponses() as m:
            getattr(m, http_method.lower())(self.url)
            mocked.assert_called_once_with(self.url, method=http_method)

    @aioresponses()
    def test_returned_instance(self, m):
        m.get(self.url)
        response = self.run_async(self.session.get(self.url))
        self.assertIsInstance(response, ClientResponse)

    @aioresponses()
    @asyncio.coroutine
    def test_returned_instance_and_status_code(self, m):
        m.get(self.url, status=204)
        response = yield from self.session.get(self.url)
        self.assertIsInstance(response, ClientResponse)
        self.assertEqual(response.status, 204)

    @aioresponses()
    @asyncio.coroutine
    def test_returned_response_headers(self, m):
        m.get(self.url,
              content_type='text/html',
              headers={'Connection': 'keep-alive'})
        response = yield from self.session.get(self.url)

        self.assertEqual(response.headers['Connection'], 'keep-alive')
        self.assertEqual(response.headers[hdrs.CONTENT_TYPE], 'text/html')

    @aioresponses()
    @asyncio.coroutine
    def test_returned_response_raw_headers(self, m):
        m.get(self.url,
              content_type='text/html',
              headers={'Connection': 'keep-alive'})
        response = yield from self.session.get(self.url)
        expected_raw_headers = (
            (b'Content-Type', b'text/html'),
            (b'Connection', b'keep-alive')
        )

        self.assertEqual(response.raw_headers, expected_raw_headers)

    @aioresponses()
    @asyncio.coroutine
    def test_raise_for_status(self, m):
        m.get(self.url, status=400)
        with self.assertRaises(ClientResponseError) as cm:
            response = yield from self.session.get(self.url)
            response.raise_for_status()
        self.assertEqual(cm.exception.message, http.RESPONSES[400][0])

    @aioresponses()
    @asyncio.coroutine
    def test_returned_instance_and_params_handling(self, m):
        expected_url = 'http://example.com/api?foo=bar&x=42#fragment'
        m.get(expected_url)
        response = yield from self.session.get(self.url, params={'x': 42})
        self.assertIsInstance(response, ClientResponse)
        self.assertEqual(response.status, 200)

        expected_url = 'http://example.com/api?x=42#fragment'
        m.get(expected_url)
        response = yield from self.session.get(
            'http://example.com/api#fragment',
            params={'x': 42}
        )
        self.assertIsInstance(response, ClientResponse)
        self.assertEqual(response.status, 200)

    @aioresponses()
    def test_method_dont_match(self, m):
        m.get(self.url)
        with self.assertRaises(ClientConnectionError):
            self.run_async(self.session.post(self.url))

    @aioresponses()
    @asyncio.coroutine
    def test_streaming(self, m):
        m.get(self.url, body='Test')
        resp = yield from self.session.get(self.url)
        content = yield from resp.content.read()
        self.assertEqual(content, b'Test')

    @aioresponses()
    @asyncio.coroutine
    def test_streaming_up_to(self, m):
        m.get(self.url, body='Test')
        resp = yield from self.session.get(self.url)
        content = yield from resp.content.read(2)
        self.assertEqual(content, b'Te')
        content = yield from resp.content.read(2)
        self.assertEqual(content, b'st')

    @asyncio.coroutine
    def test_mocking_as_context_manager(self):
        with aioresponses() as aiomock:
            aiomock.add(self.url, payload={'foo': 'bar'})
            resp = yield from self.session.get(self.url)
            self.assertEqual(resp.status, 200)
            payload = yield from resp.json()
            self.assertDictEqual(payload, {'foo': 'bar'})

    def test_mocking_as_decorator(self):
        @aioresponses()
        def foo(loop, m):
            m.add(self.url, payload={'foo': 'bar'})

            resp = loop.run_until_complete(self.session.get(self.url))
            self.assertEqual(resp.status, 200)
            payload = loop.run_until_complete(resp.json())
            self.assertDictEqual(payload, {'foo': 'bar'})

        foo(self.loop)

    @asyncio.coroutine
    def test_passing_argument(self):
        @aioresponses(param='mocked')
        @asyncio.coroutine
        def foo(mocked):
            mocked.add(self.url, payload={'foo': 'bar'})
            resp = yield from self.session.get(self.url)
            self.assertEqual(resp.status, 200)

        yield from foo()

    @fail_on(unused_loop=False)
    def test_mocking_as_decorator_wrong_mocked_arg_name(self):
        @aioresponses(param='foo')
        def foo(bar):
            # no matter what is here it should raise an error
            pass

        with self.assertRaises(TypeError) as cm:
            foo()
        exc = cm.exception
        self.assertIn("foo() got an unexpected keyword argument 'foo'",
                      str(exc))

    @asyncio.coroutine
    def test_unknown_request(self):
        with aioresponses() as aiomock:
            aiomock.add(self.url, payload={'foo': 'bar'})
            with self.assertRaises(ClientConnectionError):
                yield from self.session.get('http://example.com/foo')

    @asyncio.coroutine
    def test_raising_custom_error(self):
        with aioresponses() as aiomock:
            aiomock.get(self.url, exception=HttpProcessingError(message='foo'))
            with self.assertRaises(HttpProcessingError):
                yield from self.session.get(self.url)

    @asyncio.coroutine
    def test_multiple_requests(self):
        with aioresponses() as m:
            m.get(self.url, status=200)
            m.get(self.url, status=201)
            m.get(self.url, status=202)
            resp = yield from self.session.get(self.url)
            self.assertEqual(resp.status, 200)
            resp = yield from self.session.get(self.url)
            self.assertEqual(resp.status, 201)
            resp = yield from self.session.get(self.url)
            self.assertEqual(resp.status, 202)

            key = ('GET', URL(self.url))
            self.assertIn(key, m.requests)
            self.assertEqual(len(m.requests[key]), 3)
            self.assertEqual(m.requests[key][0].args, tuple())
            self.assertEqual(m.requests[key][0].kwargs,
                             {'allow_redirects': True})

    @asyncio.coroutine
    def test_address_as_instance_of_url_combined_with_pass_through(self):
        external_api = 'http://httpbin.org/status/201'

        @asyncio.coroutine
        def doit():
            api_resp = yield from self.session.get(self.url)
            # we have to hit actual url,
            # otherwise we do not test pass through option properly
            ext_rep = yield from self.session.get(URL(external_api))
            return api_resp, ext_rep

        with aioresponses(passthrough=[external_api]) as m:
            m.get(self.url, status=200)
            api, ext = yield from doit()

            self.assertEqual(api.status, 200)
            self.assertEqual(ext.status, 201)

    @aioresponses()
    @asyncio.coroutine
    def test_custom_response_class(self, m):
        class CustomClientResponse(ClientResponse):
            pass

        m.get(self.url, body='Test', response_class=CustomClientResponse)
        resp = yield from self.session.get(self.url)
        self.assertTrue(isinstance(resp, CustomClientResponse))

    @aioresponses()
    def test_exceptions_in_the_middle_of_responses(self, mocked):
        mocked.get(self.url, payload={}, status=204)
        mocked.get(self.url, exception=ValueError('oops'), )
        mocked.get(self.url, payload={}, status=204)
        mocked.get(self.url, exception=ValueError('oops'), )
        mocked.get(self.url, payload={}, status=200)

        @asyncio.coroutine
        def doit():
            return (yield from self.session.get(self.url))

        self.assertEqual(self.run_async(doit()).status, 204)
        with self.assertRaises(ValueError):
            self.run_async(doit())
        self.assertEqual(self.run_async(doit()).status, 204)
        with self.assertRaises(ValueError):
            self.run_async(doit())
        self.assertEqual(self.run_async(doit()).status, 200)

    @aioresponses()
    @asyncio.coroutine
    def test_request_should_match_regexp(self, mocked):
        mocked.get(
            re.compile(r'^http://example\.com/api\?foo=.*$'),
            payload={}, status=200
        )

        response = yield from self.request(self.url)
        self.assertEqual(response.status, 200)

    @aioresponses()
    @asyncio.coroutine
    def test_request_does_not_match_regexp(self, mocked):
        mocked.get(
            re.compile(r'^http://exampleexample\.com/api\?foo=.*$'),
            payload={}, status=200
        )
        with self.assertRaises(ClientConnectionError):
            yield from self.request(self.url)

    @aioresponses()
    def test_timeout(self, mocked):
        mocked.get(self.url, timeout=True)

        with self.assertRaises(asyncio.TimeoutError):
            self.run_async(self.request(self.url))
