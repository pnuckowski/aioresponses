#!/usr/bin/env python
import setuptools

setuptools.setup(
    setup_requires=['pbr'],
    pbr=True,
    package_data={"aioresponses": ["py.typed"]}
)
