# -*- coding: utf-8 -*-
from unittest import TestCase
from aioresponses import __version__


class TestAioresponses(TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_0000_something(self):
        self.assertEqual(__version__, '0.1.0')
