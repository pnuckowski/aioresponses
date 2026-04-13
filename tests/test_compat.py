# -*- coding: utf-8 -*-
from typing import Union

import pytest
from yarl import URL

from aioresponses.compat import merge_params

URL_WITH_PARAMS = 'http://example.com/api?foo=bar#fragment'
URL_WITHOUT_PARAMS = 'http://example.com/api?#fragment'


def get_url(url: str, as_str: bool) -> Union[URL, str]:
    return url if as_str else URL(url)


@pytest.mark.parametrize("as_str", [True, False])
def test_no_params_returns_same_url(as_str):
    url = get_url(URL_WITH_PARAMS, as_str)
    assert merge_params(url, None) == URL(URL_WITH_PARAMS)


@pytest.mark.parametrize("as_str", [True, False])
def test_empty_params_returns_same_url(as_str):
    url = get_url(URL_WITH_PARAMS, as_str)
    assert merge_params(url, {}) == URL(URL_WITH_PARAMS)


@pytest.mark.parametrize("as_str", [True, False])
def test_both_with_params_returns_corrected_url(as_str):
    url = get_url(URL_WITH_PARAMS, as_str)
    assert merge_params(url, {'x': 42}) == URL('http://example.com/api?foo=bar&x=42#fragment')


@pytest.mark.parametrize("as_str", [True, False])
def test_base_without_params_returns_corrected_url(as_str):
    url = get_url(URL_WITHOUT_PARAMS, as_str)
    assert merge_params(url, {'x': 42}) == URL('http://example.com/api?x=42#fragment')
