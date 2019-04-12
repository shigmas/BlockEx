#!/usr/bin/env python3

from setuptools import setup, find_packages

# If we setup as a PyPi package.
setup(
    name = 'BlockEx',
    version = '0.1.2',
    author = 'Masa Jow',
    author_email = 'wyan.github@futomen.net',
    url = "https://www.futomen.net",
    packages = find_packages(),
    classifiers = [
        'Programming Language :: Python :: 3.6'
    ],
    description = 'An overly complicated regular expression engine',
)
