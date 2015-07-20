# -*- coding: utf-8 -*-

from setuptools import setup, find_packages, Extension

cledadamap = Extension('cledadamap', sources=['cledadamap.c'])

setup(
    name = "ledadamap",
    version = "0.2.2",
    #packages = find_packages(),
    scripts = [],
    ext_modules = [cledadamap],
    py_modules = ['ledadagen', 'ledadamap'],

    install_requires = [],

    package_data = {
    },

    author = "Branislav Gajdos",
    author_email = "branislav.gajdos@modrykonik.com",
    description = "Shared memory hash map",
    license = "MIT license",
    keywords = "",
    url = "",
)
