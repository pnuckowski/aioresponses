# -*- coding: utf-8 -*-
from typing import Union
from unittest import TestCase

from ddt import ddt, data
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
        self.url_with_unsafe_chars_and_unordered_params = 'http://example.com/api?foo=bar&type=arg@&see:=thatagain'

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

    def test_normalize_url(self):
        self.assertEqual(
            normalize_url(self.url_with_unsafe_chars_and_unordered_params),
            URL('http://example.com/api?foo=bar&see:=thatagain&type=arg@')
        )
