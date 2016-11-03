===============================
aioresponses
===============================

.. image:: https://img.shields.io/travis/pnuckowski/aioresponses.svg
        :target: https://travis-ci.org/pnuckowski/aioresponses

.. image:: https://coveralls.io/repos/github/pnuckowski/aioresponses/badge.svg?branch=master
        :target: https://coveralls.io/github/pnuckowski/aioresponses?branch=master

.. image:: https://landscape.io/github/pnuckowski/aioresponses/master/landscape.svg?style=flat
        :target: https://landscape.io/github/pnuckowski/aioresponses/master
        :alt: Code Health

.. image:: https://pyup.io/repos/github/pnuckowski/aioresponses/shield.svg
        :target: https://pyup.io/repos/github/pnuckowski/aioresponses/
        :alt: Updates

.. image:: https://img.shields.io/pypi/v/aioresponses.svg
        :target: https://pypi.python.org/pypi/aioresponses

.. image:: https://readthedocs.org/projects/aioresponses/badge/?version=latest
        :target: https://aioresponses.readthedocs.io/en/latest/?badge=latest
        :alt: Documentation Status


Aioresponses is a helper for mock/fake web requests in python aiohttp package.

For *requests* module there is a lot of packages that helps us with testing (eg. *httpretty*, *responses*, *requests-mock*).

When it comes to testing asynchronous http requests it is a bit harder (at least at the beginning).
The purpose of this package is to provide an easy way to test asynchronous http requests.

Installing
----------

.. code:: bash

    $ pip install aioresponses

Usage
--------

To mock out http request use *aioresponses* as method decorator or as context manager.

Response *status* code, *body*, *payload* (for json response) and *headers* can be mocked.

Supported http methods: **get**, **post**, **put**, **patch**, **delete** and **options**.

.. code:: python

    import aiohttp
    import asyncio
    from aioresponses import aioresponses

    @aioresponses()
    def test_request(mocked):
        loop = asyncio.get_event_loop()
        mocked.get('http://example.com', status=200, body='test')
        session = aiohttp.ClientSession()
        resp = loop.run_until_complete(session.get('http://example.com'))

        assert resp.status == 200


for convenience use *payload* argument to mock out json response. Example below.

**as context manager**

.. code:: python

    import asyncio
    import aiohttp
    from aioresponses import aioresponses

    def test_ctx():
        loop = asyncio.get_event_loop()
        session = aiohttp.ClientSession()
        with aioresponses() as m:
            m.get('http://test.example.com', payload=dict(foo='bar'))

            resp = loop.run_until_complete(session.get('http://test.example.com'))
            data = loop.run_until_complete(resp.json())

            assert dict(foo='bar') == data

**aioresponses allow to mock out any HTTP headers**

.. code:: python

    import asyncio
    import aiohttp
    from aioresponses import aioresponses

    @aioresponses()
    def test_http_headers(m):
        loop = asyncio.get_event_loop()
        session = aiohttp.ClientSession()
        m.post(
            'http://example.com',
            payload=dict(),
            headers=dict(connection='keep-alive'),
        )

        resp = loop.run_until_complete(session.post('http://example.com'))

        # note that we pass 'connection' but get 'Connection' (capitalized)
        # under the neath `multidict` is used to work with HTTP headers
        assert resp.headers['Connection'] == 'keep-alive'

**allow to register different response for the same url**

.. code:: python

    import asyncio
    import aiohttp
    from aioresponses import aioresponses

    @aioresponses()
    def test_multiple_respnses(m):
        loop = asyncio.get_event_loop()
        session = aiohttp.ClientSession()
        m.get('http://example.com', status=500)
        m.get('http://example.com', status=200)

        resp1 = loop.run_until_complete(session.get('http://example.com'))
        resp2 = loop.run_until_complete(session.get('http://example.com'))

        assert resp1.status == 500
        assert resp2.status == 200


Features
--------
* Easy to mock out http requests made by *aiohttp.ClientSession*

Disclaimer
----------
Due to the fact that *get*, *post*, *put*, *delete* methods from *aiohttp* are in deprecation mode and they are NOT supported by this package.


License
-------
* Free software: MIT license

Credits
---------

This package was created with Cookiecutter_ and the `audreyr/cookiecutter-pypackage`_ project template.

.. _Cookiecutter: https://github.com/audreyr/cookiecutter
.. _`audreyr/cookiecutter-pypackage`: https://github.com/audreyr/cookiecutter-pypackage

