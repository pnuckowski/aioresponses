===============================
aioresponses
===============================

.. image:: https://img.shields.io/pypi/v/aioresponses.svg
        :target: https://pypi.python.org/pypi/aioresponses

.. image:: https://github.com/pnuckowski/aioresponses/actions/workflows/ci.yml/badge.svg
        :target: https://github.com/pnuckowski/aioresponses/actions/workflows/ci.yml
        :alt: CI


Aioresponses is a helper to mock/fake web requests in python aiohttp package.

For *requests* module there are a lot of packages that help us with testing (eg. *httpretty*, *responses*, *requests-mock*).

When it comes to testing asynchronous HTTP requests it is a bit harder (at least at the beginning).
The purpose of this package is to provide an easy way to test asynchronous HTTP requests.

Installing
----------

.. code:: bash

    $ pip install aioresponses

Supported versions
------------------
- Python 3.10+
- aiohttp>=3.8,<4.0

Usage
--------

To mock out HTTP requests in pytest, use the built-in ``aioresponse`` fixture.
The classic decorator and context manager styles are still supported as well.

Response *status* code, *body*, *payload* (for json response) and *headers* can be mocked.

Supported HTTP methods: **GET**, **POST**, **PUT**, **PATCH**, **DELETE** and **OPTIONS**.

.. code:: python

    import aiohttp
    import pytest

    @pytest.mark.asyncio
    async def test_request(aioresponse):
        mocked = aioresponse()
        mocked.get('http://example.com', status=200, body='test')

        async with aiohttp.ClientSession() as session:
            resp = await session.get('http://example.com')

        assert resp.status == 200
        mocked.assert_called_once_with('http://example.com')


for convenience use *payload* argument to mock out json response. Example below.

**as a context manager**

.. code:: python

    import aiohttp
    import pytest
    from aioresponses import aioresponses

    @pytest.mark.asyncio
    async def test_ctx():
        with aioresponses() as m:
            m.get('http://test.example.com', payload=dict(foo='bar'))

            async with aiohttp.ClientSession() as session:
                resp = await session.get('http://test.example.com')
                data = await resp.json()

            assert dict(foo='bar') == data
            m.assert_called_once_with('http://test.example.com')

**aioresponses allows to mock out any HTTP headers**

.. code:: python

    import aiohttp
    import pytest

    @pytest.mark.asyncio
    async def test_http_headers(aioresponse):
        mocked = aioresponse()
        mocked.post(
            'http://example.com',
            payload=dict(),
            headers=dict(connection='keep-alive'),
        )

        async with aiohttp.ClientSession() as session:
            resp = await session.post('http://example.com')

        # note that we pass 'connection' but get 'Connection' (capitalized)
        # under the neath `multidict` is used to work with HTTP headers
        assert resp.headers['Connection'] == 'keep-alive'
        mocked.assert_called_once_with('http://example.com', method='POST')

**allows to register different responses for the same url**

.. code:: python

    import aiohttp
    import pytest

    @pytest.mark.asyncio
    async def test_multiple_responses(aioresponse):
        mocked = aioresponse()
        mocked.get('http://example.com', status=500)
        mocked.get('http://example.com', status=200)

        async with aiohttp.ClientSession() as session:
            resp1 = await session.get('http://example.com')
            resp2 = await session.get('http://example.com')

        assert resp1.status == 500
        assert resp2.status == 200


**Repeat response for the same url**  

E.g. for cases where you want to test retrying mechanisms.

- By default, ``repeat=False`` means the response is not repeated (``repeat=1`` does the same).
- Use ``repeat=n`` to repeat a response n times.
- Use ``repeat=True`` to repeat a response indefinitely.

.. code:: python

    import aiohttp
    import pytest

    @pytest.mark.asyncio
    async def test_multiple_responses(aioresponse):
        mocked = aioresponse()
        mocked.get('http://example.com', status=500, repeat=2)
        mocked.get('http://example.com', status=200)  # will take effect after two preceding calls

        async with aiohttp.ClientSession() as session:
            resp1 = await session.get('http://example.com')
            resp2 = await session.get('http://example.com')
            resp3 = await session.get('http://example.com')

        assert resp1.status == 500
        assert resp2.status == 500
        assert resp3.status == 200


**match URLs with regular expressions**

.. code:: python

    import aiohttp
    import re
    import pytest

    @pytest.mark.asyncio
    async def test_regexp_example(aioresponse):
        mocked = aioresponse()
        pattern = re.compile(r'^http://example\.com/api\?foo=.*$')
        mocked.get(pattern, status=200)

        async with aiohttp.ClientSession() as session:
            resp = await session.get('http://example.com/api?foo=bar')

        assert resp.status == 200

**allows to make redirects responses**

.. code:: python

    import aiohttp
    import pytest

    @pytest.mark.asyncio
    async def test_redirect_example(aioresponse):
        mocked = aioresponse()

        # absolute urls are supported
        mocked.get(
            'http://example.com/',
            headers={'Location': 'http://another.com/'},
            status=307
        )
        mocked.get('http://another.com/', status=200)

        async with aiohttp.ClientSession() as session:
            resp = await session.get('http://example.com/', allow_redirects=True)
        assert resp.url == 'http://another.com/'

        # and also relative
        mocked.get(
            'http://example.com/',
            headers={'Location': '/test'},
            status=307
        )
        mocked.get('http://example.com/test', status=200)

        async with aiohttp.ClientSession() as session:
            resp = await session.get('http://example.com/', allow_redirects=True)
        assert resp.url == 'http://example.com/test'

**allows to passthrough to a specified list of servers**

.. code:: python

    import aiohttp
    import pytest

    @pytest.mark.asyncio
    async def test_passthrough(aioresponse):
        mocked = aioresponse(passthrough=['http://backend'])
        mocked.get('http://example.com/api', status=200)

        async with aiohttp.ClientSession() as session:
            mocked_resp = await session.get('http://example.com/api')
        # this will actually perform a request
            resp = await session.get('http://backend/api')

        assert mocked_resp.status == 200

**also you can passthrough all requests except specified by mocking object**

.. code:: python

    import aiohttp
    import pytest

    @pytest.mark.asyncio
    async def test_passthrough_unmatched(aioresponse):
        url = 'https://httpbin.org/get'
        mocked = aioresponse(passthrough_unmatched=True)
        mocked.get(url, status=200)
        # this will actually perform a request
        async with aiohttp.ClientSession() as session:
            resp = await session.get('http://backend/api')
        # this will not perform a request and resp2.status will return 200
            resp2 = await session.get(url)

        assert resp.status == 200
        assert resp2.status == 200

**aioresponses allows to throw an exception**

.. code:: python

    import pytest
    from aiohttp import ClientSession
    from aiohttp.http_exceptions import HttpProcessingError

    @pytest.mark.asyncio
    async def test_how_to_throw_an_exception(aioresponse):
        mocked = aioresponse()
        mocked.get('http://example.com/api', exception=HttpProcessingError('test'))

        async with ClientSession() as session:
            with pytest.raises(HttpProcessingError):
                await session.get('http://example.com/api')


**aioresponses allows to use callbacks to provide dynamic responses**

.. code:: python

    import aiohttp
    import pytest
    from aioresponses import CallbackResult

    def callback(url, **kwargs):
        return CallbackResult(status=418)

    @pytest.mark.asyncio
    async def test_callback(aioresponse):
        mocked = aioresponse()
        mocked.get('http://example.com', callback=callback)

        async with aiohttp.ClientSession() as session:
            resp = await session.get('http://example.com')

        assert resp.status == 418


**aioresponses can be used with pytest**

aioresponses ships with a built-in pytest plugin. After installing the package,
the ``aioresponse`` fixture is available **automatically** — no extra
configuration needed. To run ``async def`` tests, install ``pytest-asyncio`` as well.

The fixture is a factory: call it to get a configured mock instance.

.. code:: python

    import aiohttp
    import pytest

    @pytest.mark.asyncio
    async def test_get(aioresponse):
        m = aioresponse()
        m.get("http://example.com", status=200)

        async with aiohttp.ClientSession() as session:
            resp = await session.get("http://example.com")

        assert resp.status == 200

Pass keyword arguments to configure the mock behaviour:

.. code:: python

    import pytest

    @pytest.mark.asyncio
    async def test_passthrough_unmatched(aioresponse):
        m = aioresponse(passthrough_unmatched=True)
        m.get("http://example.com/mocked", status=200)
        # unmatched requests are forwarded to the real server

    @pytest.mark.asyncio
    async def test_passthrough_list(aioresponse):
        m = aioresponse(passthrough=["http://real-backend"])
        m.get("http://example.com/mocked", status=200)

You can also define your own fixture when you need custom defaults:

.. code:: python

    import pytest
    from aioresponses import aioresponses

    @pytest.fixture
    def mock_aioresponse():
        with aioresponses() as m:
            yield m


**aioresponses can be used with unittest**

.. code:: python

    import asyncio
    import unittest
    from aiohttp import ClientSession
    from aioresponses import aioresponses

    class MyTestCase(unittest.TestCase):
        @aioresponses()
        def test_request(self, mocked):
            mocked.get('http://example.com', status=200)

            loop = asyncio.get_event_loop()
            async def run():
                async with ClientSession() as session:
                    response = await session.get('http://example.com')
                    self.assertEqual(response.status, 200)

            loop.run_until_complete(run())


Features
--------
* Easy to mock out HTTP requests made by *aiohttp.ClientSession*


License
-------
* Free software: MIT license

Credits
-------

This package was created with Cookiecutter_ and the `audreyr/cookiecutter-pypackage`_ project template.

.. _Cookiecutter: https://github.com/audreyr/cookiecutter
.. _`audreyr/cookiecutter-pypackage`: https://github.com/audreyr/cookiecutter-pypackage
