from unittest import TestCase

from ddt import ddt, data
from aioresponses.compat import (
    _vanilla_merge_url_params, _yarl_merge_url_params, yarl_available
)


@ddt
class CompatTestCase(TestCase):
    use_default_loop = False

    def setUp(self):
        self.url_with_parameters = 'http://example.com/api?foo=bar#fragment'
        self.url_without_parameters = 'http://example.com/api?#fragment'

    def _get_merge_functions(self):
        if yarl_available:
            return {
                _vanilla_merge_url_params,
                _yarl_merge_url_params
            }
        return {
            _vanilla_merge_url_params,
        }

    @data(
        _vanilla_merge_url_params,
        _yarl_merge_url_params
    )
    def test_no_params_returns_same_url(self, func):
        if func in self._get_merge_functions():
            self.assertEqual(
                func(self.url_with_parameters, None),
                self.url_with_parameters
            )

    @data(
        _vanilla_merge_url_params,
        _yarl_merge_url_params
    )
    def test_empty_params_returns_same_url(self, func):
        if func in self._get_merge_functions():
            self.assertEqual(
                func(self.url_with_parameters, {}),
                self.url_with_parameters
            )

    @data(
        _vanilla_merge_url_params,
        _yarl_merge_url_params
    )
    def test_both_with_params_returns_corrected_url(self, func):
        if func in self._get_merge_functions():
            expected_url = 'http://example.com/api?foo=bar&x=42#fragment'
            self.assertEqual(
                func(self.url_with_parameters, {'x': 42}),
                expected_url
            )

    @data(
        _vanilla_merge_url_params,
        _yarl_merge_url_params
    )
    def test_base_without_params_returns_corrected_url(self, func):
        if func in self._get_merge_functions():
            expected_url = 'http://example.com/api?x=42#fragment'
            self.assertEqual(
                func(self.url_without_parameters, {'x': 42}),
                expected_url
            )
