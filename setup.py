# -*- coding: utf-8 -*-
# Copyright (c) 2016 - 2020 Sqreen. All rights reserved.
# Please refer to our terms for more information:
#
#     https://www.sqreen.io/terms.html
#
import os.path

# setuptools must be imported before distutils
from setuptools import find_packages, setup

from distutils.command.build_ext import build_ext
from distutils.core import Extension
from distutils.errors import (
    CCompilerError,
    DistutilsExecError,
    DistutilsPlatformError,
)

root_dir = os.path.abspath(os.path.dirname(__file__))
metadata = {}

about_file = os.path.join(root_dir, "sqreen", "__about__.py")
with open(about_file, "rb") as f:
    exec(f.read(), metadata)

readme_file = os.path.join(root_dir, "README.md")
with open(readme_file, "rb") as f:
    long_description = f.read().decode("utf-8")

base_setup = dict(
    name="sqreen",
    version=metadata["__version__"],
    description="Sqreen agent to protect Python applications.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author=metadata["__author__"],
    author_email=metadata["__email__"],
    url="https://www.sqreen.com/",
    packages=find_packages(
        exclude=[
            "benchmarks.*", "benchmarks",
            "tests.*", "tests",
        ]
    ),
    package_dir={"sqreen": "sqreen"},
    include_package_data=True,
    install_requires=["py-mini-racer>=0.4.0,<1.0.0", "sq-native>=1.0.5,<2.0.0"],
    license=metadata["__license__"],
    zip_safe=False,
    keywords="sqreen",
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "License :: Other/Proprietary License",
        "Programming Language :: Python",
        "Programming Language :: Python :: 2",
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.4",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Topic :: Internet :: WWW/HTTP",
        "Topic :: Security",
    ],
    test_suite="tests",
    tests_require=[],
    entry_points={
        "console_scripts": ["sqreen-start = sqreen.bin.protect:protect"]
    },
)


class BuildExtFailed(Exception):
    pass


class optional_build_ext(build_ext):
    def run(self):
        try:
            build_ext.run(self)
        except DistutilsPlatformError:
            raise BuildExtFailed

    def build_extension(self, ext):
        try:
            build_ext.build_extension(self, ext)
        except (CCompilerError, DistutilsExecError, DistutilsPlatformError):
            raise BuildExtFailed


def run_setup(install_extensions=True):
    setup_options = {}
    if install_extensions:
        setup_options["cmdclass"] = {"build_ext": optional_build_ext}
        setup_options["ext_modules"] = [
            Extension("sqreen._vendors.wrapt._wrappers", ["sqreen/_vendors/wrapt/_wrappers.c"])
        ]
    setup_options.update(base_setup)
    setup(**setup_options)


SQREEN_INSTALL_EXTENSIONS = os.getenv("SQREEN_INSTALL_EXTENSIONS")
if SQREEN_INSTALL_EXTENSIONS is not None:
    # Build with or without extensions according to the environment variable.
    run_setup(install_extensions=SQREEN_INSTALL_EXTENSIONS.lower() in ("true", "1", "yes", "y"))
else:
    # By default, try to build the extensions and fallback to a pure-Python installation.
    try:
        run_setup(install_extensions=True)
    except BuildExtFailed:
        print("Install sqreen without extensions because they could not be compiled.")
        run_setup(install_extensions=False)
