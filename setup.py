# -*- coding: utf-8 -*-

from setuptools import setup, find_packages, Extension

cledadamap = Extension('cledadamap', sources=['cledadamap.c'])

setup(
    name = "ledadamap",
    version = "0.1",
    packages = find_packages(),
    scripts = [],
    ext_modules = [cledadamap],

    install_requires = [],

    package_data = {
    },

    author = "Branislav Gajdos",
    author_email = "branislav.gajdos@asmira.com",
    description = "Shared memory hash map",
    license = "Asmira license",
    keywords = "",
    url = "",
)
