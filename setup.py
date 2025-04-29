# flake8: noqa
import codecs
import os

from setuptools import find_packages, setup

PACKAGE_NAME = "coord_dsl"
VERSION = "0.1.0"
AUTHOR = ""
AUTHOR_EMAIL = ""
DESCRIPTION = "coord_dsl"
KEYWORDS = ""
LICENSE = "MIT"
URL = ""

setup(
    name=PACKAGE_NAME,
    version=VERSION,
    description=DESCRIPTION,
    url=URL,
    author=AUTHOR,
    author_email=AUTHOR_EMAIL,
    keywords=KEYWORDS,
    license=LICENSE,
    package_dir={"": "src"},
    include_package_data=True,
    packages=find_packages(where="src"),
    package_data={"coord_dsl": ["*.tx"]},
    install_requires=["textx_ls_core"],
    entry_points={
        "textx_languages": ["fsm = coord_dsl:fsm_meta"],
        "textx_generators": [
            "fsm_json = coord_dsl.generators.fsm_gen:fsm_json_gen",
            "fsm_cpp = coord_dsl.generators.fsm_gen:fsm_cpp_gen",
            "fsm_console = coord_dsl.generators.fsm_gen:fsm_console_gen",
        ],
    },
)
