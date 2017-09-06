#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fenc=utf-8

from setuptools import setup

setup(
        name="structure_detection",
        version="0.1",
        description="This software is capable to detect the intern" \
                " structure detection by mean of a paraver trace" \
                " post-mortem analysis.",
        url="tools.bsc.es",
        author="Juan Francisco Martinez Vera",
        author_email="juan.martinez@bsc.es",
        license="MIT",
        packages=["structure_detection"],
        install_requires=[
            "numpy",
            "argcomplete",
            "sympy",
            "scikit-learn",
            "matplotlib",
            "scipy",
            ],
        zip_safe=False)
