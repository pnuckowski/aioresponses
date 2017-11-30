# -*- coding: utf-8 -*-
import asyncio
from unittest.mock import patch

from aiohttp import hdrs
from aiohttp.client import ClientSession
from aiohttp.client_reqrep import ClientResponse
from asynctest import fail_on
from asynctest.case import TestCase

from aioresponses.compat import URL

try:
    from aiohttp.errors import ClientConnectionError, HttpProcessingError
except ImportError:
    from aiohttp.client_exceptions import ClientConnectionError
    from aiohttp.http_exceptions import HttpProcessingError
from ddt import ddt, data

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
        response = self.loop.run_until_complete(self.session.get(self.url))
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
            self.loop.run_until_complete(self.session.post(self.url))

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

            key = ('GET', self.url)
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
