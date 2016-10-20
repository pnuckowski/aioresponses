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

For requests module there is a lot of packages that helps us with testing (eg. httpretty, responses, requests-mock).

Examples
--------
.. code:: python

        import aiohttp
        import asyncio
        from aioresponses import aioresponses

        @aioresponses()
        def test_request(mocked):
                loop = asyncio.get_event_loop()
                mocked.get('http://example.com', status=200, body='test')
                session = aiohttp.ClientSession()
                resp = loop.run_until_complete(sessios.get('http://example.com')

                assert resp.status == 200



Features
--------
* Easy to mock out requests made by aiohttp.ClientSession

Disclaimer
----------
Due to the fact that `aiohttp.{get, post, put, delete and so on} methods are in deprecation mode they are NOT supported by this package


License
-------
* Free software: MIT license

Credits
---------

This package was created with Cookiecutter_ and the `audreyr/cookiecutter-pypackage`_ project template.

.. _Cookiecutter: https://github.com/audreyr/cookiecutter
.. _`audreyr/cookiecutter-pypackage`: https://github.com/audreyr/cookiecutter-pypackage

