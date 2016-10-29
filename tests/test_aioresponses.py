# -*- coding: utf-8 -*-
import asyncio
from unittest.case import TestCase
from unittest.mock import patch

from aiohttp import hdrs
from aiohttp.client import ClientSession
from aiohttp.client_reqrep import ClientResponse
from aiohttp.errors import ClientConnectionError
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
