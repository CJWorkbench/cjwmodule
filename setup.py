#!/usr/bin/env python3

import sys
from distutils.command.sdist import sdist
from os.path import dirname, join

from setuptools import find_packages, setup

from cjwmodule import __version__

# We use the README as the long_description
readme = open(join(dirname(__file__), "README.md")).read()

needs_pytest = {"pytest", "test", "ptr"}.intersection(sys.argv)


class _sdist(sdist):
    def run(self):
        from maintenance import i18n

        i18n.check()
        super().run()


setup(
    name="cjwmodule",
    version=__version__,
    url="http://github.com/CJWorkbench/cjwmodule/",
    author="Adam Hooper",
    author_email="adam@adamhooper.com",
    description="Utilities to help build Workbench modules",
    include_package_data=True,
    long_description=readme,
    long_description_content_type="text/markdown",
    license="MIT",
    zip_safe=True,
    packages=find_packages(
        exclude=["tests", "tests.*", "maintenance", "maintenance.*"]
    ),
    install_requires=["httpx~=0.11.0"],
    setup_requires=["pytest-runner~=5.2"] if needs_pytest else [],
    extras_require={
        "tests": ["pytest~=5.3.0", "pytest-asyncio~=0.10.0"],
        "maintenance": ["babel~=2.8.0"],
    },
    cmdclass={"sdist": _sdist},
)
