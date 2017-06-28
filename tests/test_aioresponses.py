# -*- coding: utf-8 -*-
import asyncio
from unittest.case import TestCase
from unittest.mock import patch

from aiohttp import hdrs
from aiohttp.client import ClientSession
from aiohttp.client_reqrep import ClientResponse

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
    def setUp(self):
        self.url = 'http://example.com/api'
        self.loop = asyncio.get_event_loop()
        self.session = ClientSession()

    def tearDown(self):
        self.session.close()

    @data(
        hdrs.METH_GET,
        hdrs.METH_POST,
        hdrs.METH_PUT,
        hdrs.METH_PATCH,
        hdrs.METH_DELETE,
        hdrs.METH_OPTIONS,
    )
    @patch('aioresponses.aioresponses.add')
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
    def test_returned_response_headers(self, m):
        m.get(self.url,
              content_type='text/html',
              headers={'Connection': 'keep-alive'})
        response = self.loop.run_until_complete(self.session.get(self.url))

        self.assertEqual(response.headers['Connection'], 'keep-alive')
        self.assertEqual(response.headers[hdrs.CONTENT_TYPE], 'text/html')

    @aioresponses()
    def test_method_dont_match(self, m):
        m.get(self.url)
        with self.assertRaises(ClientConnectionError):
            self.loop.run_until_complete(self.session.post(self.url))

    @aioresponses()
    def test_streaming(self, m):
        m.get(self.url, body='Test')
        resp = self.loop.run_until_complete(self.session.get(self.url))
        content = self.loop.run_until_complete(resp.content.read())
        self.assertEqual(content, b'Test')

    @aioresponses()
    def test_streaming_up_to(self, m):
        m.get(self.url, body='Test')
        resp = self.loop.run_until_complete(self.session.get(self.url))
        content = self.loop.run_until_complete(resp.content.read(2))
        self.assertEqual(content, b'Te')
        content = self.loop.run_until_complete(resp.content.read(2))
        self.assertEqual(content, b'st')

    def test_mocking_as_context_manager(self):
        with aioresponses() as aiomock:
            aiomock.add(self.url, payload={'foo': 'bar'})
            resp = self.loop.run_until_complete(self.session.get(self.url))
            self.assertEqual(resp.status, 200)
            payload = self.loop.run_until_complete(resp.json())
            self.assertDictEqual(payload, {'foo': 'bar'})

    def test_mocking_as_decorator(self):
        @aioresponses()
        def foo(m):
            m.add(self.url, payload={'foo': 'bar'})

            resp = self.loop.run_until_complete(self.session.get(self.url))
            self.assertEqual(resp.status, 200)
            payload = self.loop.run_until_complete(resp.json())
            self.assertDictEqual(payload, {'foo': 'bar'})

        foo()

    def test_passing_argument(self):
        @aioresponses(param='mocked')
        def foo(mocked):
            mocked.add(self.url, payload={'foo': 'bar'})
            resp = self.loop.run_until_complete(self.session.get(self.url))
            self.assertEqual(resp.status, 200)

        foo()

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

    def test_unknown_request(self):
        with aioresponses() as aiomock:
            aiomock.add(self.url, payload={'foo': 'bar'})
            with self.assertRaises(ClientConnectionError):
                self.loop.run_until_complete(
                    self.session.get('http://example.com/foo')
                )

    def test_raising_custom_error(self):
        with aioresponses() as aiomock:
            aiomock.get(self.url, exception=HttpProcessingError(message='foo'))
            with self.assertRaises(HttpProcessingError):
                self.loop.run_until_complete(
                    self.session.get(self.url)
                )

    def test_multiple_requests(self):
        with aioresponses() as m:
            m.get(self.url, status=200)
            m.get(self.url, status=201)
            m.get(self.url, status=202)
            resp = self.loop.run_until_complete(self.session.get(self.url))
            self.assertEqual(resp.status, 200)
            resp = self.loop.run_until_complete(self.session.get(self.url))
            self.assertEqual(resp.status, 201)
            resp = self.loop.run_until_complete(self.session.get(self.url))
            self.assertEqual(resp.status, 202)

            key = ('GET', self.url)
            self.assertIn(key, m.requests)
            self.assertEqual(len(m.requests[key]), 3)
            self.assertEqual(m.requests[key][0].args, tuple())
            self.assertEqual(m.requests[key][0].kwargs,
                             {'allow_redirects': True})

    def test_address_as_instance_of_url_combined_with_pass_through(self):
        external_api = 'http://google.com'

        @asyncio.coroutine
        def doit():
            api_resp = yield from self.session.get(self.url)
            # we have to hit actual url,
            # otherwise we do not test pass through option properly
            ext_rep = yield from self.session.get(URL(external_api))
            return api_resp, ext_rep

        with aioresponses(passthrough=[external_api]) as m:
            m.get(self.url, status=200)
            api, ext = self.loop.run_until_complete(doit())

            self.assertEqual(api.status, 200)
            self.assertEqual(ext.status, 200)
