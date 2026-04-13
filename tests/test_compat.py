# -*- coding: utf-8 -*-
from itertools import product
from typing import Union

from ddt import ddt, data, unpack
from yarl import URL

from aioresponses.compat import merge_params, normalize_url


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


@pytest.mark.parametrize(
    "original_url, expected_url, as_str",
    [
        (
            "http://example.com/api?var2=baz&var1=foo",
            "http://example.com/api?var1=foo&var2=baz",
            as_str,
        )
        for as_str in [True, False]
    ]
    + [
        (
            "https://example.com/api?var3=gaz%3Bdar&var1=foo:bar&var1=bar/baz&var2=baz%26gaz",
            "https://example.com/api?var1=bar%252Fbaz&var1=foo%253Abar&var2=baz%2526gaz&var3=gaz%253Bdar",
            as_str,
        )
        for as_str in [True, False]
    ]
    + [
        (
            "https://example.com/api?var3=gaz%3Bdar&var1=foo%3Abar&var1=bar%2Fbaz&var2=baz%26gaz",
            "https://example.com/api?var1=bar%252Fbaz&var1=foo%253Abar&var2=baz%2526gaz&var3=gaz%253Bdar",
            as_str,
        )
        for as_str in [True, False]
    ]
    + [
        (
            "https://example.com/api?var=\u043f\u0443\u0442\u044c",
            "https://example.com/api?var=%25D0%25BF%25D1%2583%25D1%2582%25D1%258C",
            as_str,
        )
        for as_str in [True, False]
    ]
    + [
        (
            "https://example.com/api?var=%D0%BF%D1%83%D1%82%D1%8C",
            "https://example.com/api?var=%25D0%25BF%25D1%2583%25D1%2582%25D1%258C",
            as_str,
        )
        for as_str in [True, False]
    ],
)
def test_normalize_url(original_url, expected_url, as_str):
    original_url = get_url(original_url, as_str)
    received_url = normalize_url(original_url)
    assert isinstance(received_url, URL)
    assert expected_url == str(received_url)
