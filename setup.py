#!/usr/bin/env python3

import distutils.cmd
from os.path import dirname, join

from setuptools import find_packages, setup

from cjwmodule import __version__

# We use the README as the long_description
readme = open(join(dirname(__file__), "README.md")).read()


class ExtractMessagesCommand(distutils.cmd.Command):
    """A custom command to run i18n-related stuff."""

    description = "extract i18n messages or check if they need extraction"
    user_options = [
        # The format is (long option, short option, description).
        (
            "check",
            None,
            "Check if all messages have been extracted without modifying catalogs",
        ),
    ]

    def initialize_options(self):
        """Set default values for options."""
        # Each user option must be listed here with their default value.
        self.check = False

    def finalize_options(self):
        """Post-process options."""

    def run(self):
        from maintenance.i18n import check, extract

        """Run command."""
        if self.check:
            check()
        else:
            extract()


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
    # google-re2==0.0.5 is the last version to support Debian Buster's libre2-5
    # When we upgrade Debian (or google-re2 gets wheels), remove the constraint.
    install_requires=["google-re2==0.0.5", "httpx~=0.17", "pyarrow~=2.0"],
    extras_require={"maintenance": ["babel~=2.9.0"]},
    cmdclass={"extract_messages": ExtractMessagesCommand},
)
