import sys

from os.path import dirname, join

from setuptools import setup

from cjwmodule import __version__

# We use the README as the long_description
readme = open(join(dirname(__file__), "README.md")).read()

needs_pytest = {"pytest", "test", "ptr"}.intersection(sys.argv)

setup(
    name="cjwmodule",
    version=__version__,
    url="http://github.com/CJWorkbench/cjwmodule/",
    author="Adam Hooper",
    author_email="adam@adamhooper.com",
    description="Utilities to help build Workbench modules",
    long_description=readme,
    long_description_content_type="text/markdown",
    license="MIT",
    zip_safe=True,
    packages=["cjwmodule"],
    install_requires=["pandas==0.25.3", "pyarrow==0.15.1"],
    setup_requires=["pytest-runner~=5.2"] if needs_pytest else [],
    tests_require=["pytest~=5.3.0"],
)
