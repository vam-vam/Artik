#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright (C) 2020 Jan Vacek

"""Setup script for "Artik the robot" package."""

from setuptools import setup, find_packages


setup(
    name="Artik",
    version="1.0.0",
    description="Control for a home-assembled hobbyist R2D2-like robot",
    author="Jan Vacek",
    include_package_data=True,
    author_email="",
    packages=find_packages(),
    python_requires=">=3.6.*",
    license='MIT',
    platforms='Raspberry Pi',
)
