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
For requests module there is a lot of packages that helps us with testing (eg. httpretty, responses).


* Free software: MIT license


Features
--------

* Easy to mock out requests made by aiohttp.ClientSession

Disclaimer
----------
Due to the fact that `aiohttp.{get, post, put, delete and so on} methods are in deprecation mode they are NOT supported by this package

Credits
---------

This package was created with Cookiecutter_ and the `audreyr/cookiecutter-pypackage`_ project template.

.. _Cookiecutter: https://github.com/audreyr/cookiecutter
.. _`audreyr/cookiecutter-pypackage`: https://github.com/audreyr/cookiecutter-pypackage

