# -*- coding: utf-8 -*-
from itertools import product
from typing import Union
from unittest import TestCase

from ddt import ddt, data, unpack
from yarl import URL

from aioresponses.compat import merge_params, normalize_url


def get_url(url: str, as_str: bool) -> Union[URL, str]:
    return url if as_str else URL(url)


@ddt
class CompatTestCase(TestCase):
    use_default_loop = False

    def setUp(self):
        self.url_with_parameters = 'http://example.com/api?foo=bar#fragment'
        self.url_without_parameters = 'http://example.com/api?#fragment'

    @data(True, False)
    def test_no_params_returns_same_url__as_str(self, as_str):
        url = get_url(self.url_with_parameters, as_str)
        self.assertEqual(
            merge_params(url, None), URL(self.url_with_parameters)
        )

    @data(True, False)
    def test_empty_params_returns_same_url__as_str(self, as_str):
        url = get_url(self.url_with_parameters, as_str)
        self.assertEqual(merge_params(url, {}), URL(self.url_with_parameters))

    @data(True, False)
    def test_both_with_params_returns_corrected_url__as_str(self, as_str):
        url = get_url(self.url_with_parameters, as_str)
        self.assertEqual(
            merge_params(url, {'x': 42}),
            URL('http://example.com/api?foo=bar&x=42#fragment'),
        )

    @data(True, False)
    def test_base_without_params_returns_corrected_url__as_str(self, as_str):
        expected_url = URL('http://example.com/api?x=42#fragment')
        url = get_url(self.url_without_parameters, as_str)

        self.assertEqual(merge_params(url, {'x': 42}), expected_url)

    @data(
        *(
            (original_url, expected_url, as_str)
            for (original_url, expected_url), as_str
            in product(
                [
                    (
                            # Trivial example.
                            "http://example.com/api?var2=baz&var1=foo",
                            "http://example.com/api?var1=foo&var2=baz",
                    ),
                    (
                            # Multi-occurrence of keys and proper query string encoding/decoding.
                            "https://example.com/api?var3=gaz%3Bdar&var1=foo:bar&var1=bar/baz&var2=baz%26gaz",
                            "https://example.com/api?var1=bar/baz&var1=foo:bar&var2=baz%26gaz&var3=gaz%3Bdar",
                    ),
                    (
                            # Same as above, but input already encoded.
                            "https://example.com/api?var3=gaz%3Bdar&var1=foo%3Abar&var1=bar%2Fbaz&var2=baz%26gaz",
                            "https://example.com/api?var1=bar/baz&var1=foo:bar&var2=baz%26gaz&var3=gaz%3Bdar",
                    ),
                    (
                            # Testing encoding/decoding for non-ascii characters.
                            "https://example.com/api?var=путь",
                            "https://example.com/api?var=%D0%BF%D1%83%D1%82%D1%8C",
                    ),
                    (
                            # Same as above, but input already encoded.
                            "https://example.com/api?var=%D0%BF%D1%83%D1%82%D1%8C",
                            "https://example.com/api?var=%D0%BF%D1%83%D1%82%D1%8C",
                    ),
                ],
                [True, False]
            )
        )
    )
    @unpack
    def test_normalize_url(self, original_url, expected_url, as_str):
        original_url = get_url(original_url, as_str)
        received_url = normalize_url(original_url)
        assert isinstance(received_url, URL)
        assert expected_url == str(received_url)
