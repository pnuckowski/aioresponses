# -*- coding: utf-8 -*-

try:
    from yarl import URL
except ImportError:
    class URL(str):
        pass
