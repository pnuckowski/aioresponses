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

Examples
--------
The package may used in many ways.
The most common and easier way is to use a decorator.

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



Testing by using context manager.

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

