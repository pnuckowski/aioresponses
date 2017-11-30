from unittest import TestCase

from ddt import ddt, data
from aioresponses.compat import (
    _vanilla_merge_url_params, _yarl_merge_url_params
)


@ddt
class CompatTestCase(TestCase):
    use_default_loop = False

    def setUp(self):
        self.url = 'http://example.com/api?foo=bar#fragment'


    @data(
        _vanilla_merge_url_params,
        _yarl_merge_url_params
    )
    def test_no_params_returns_same_url(self, func):
        self.assertEqual(func(self.url, None), self.url)

    @data(
        _vanilla_merge_url_params,
        _yarl_merge_url_params
    )
    def test_empty_params_returns_same_url(self, func):
        self.assertEqual(func(self.url, {}), self.url)

    @data(
        _vanilla_merge_url_params,
        _yarl_merge_url_params
    )
    def test_params_returns_corrected_url(self, func):
        expected_url = 'http://example.com/api?foo=bar&x=42#fragment'
        self.assertEqual(func(self.url, {'x': 42}), expected_url)

