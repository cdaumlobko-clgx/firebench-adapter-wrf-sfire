import os
import sys

sys.path.insert(0, os.path.abspath("../src"))

project = "firebench-adapter-wrf-sfire"
author = "WIRC SJSU"
version = "0.1"
release = "0.1-dev1"
copyright = "%Y, Aurelien Costes, WIRC SJSU"

extensions = [
    "myst_parser",
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "sphinx.ext.viewcode",
    "sphinx.ext.autosummary",
]

templates_path = ["_templates"]
exclude_patterns = ["_build"]

html_theme = "sphinx_rtd_theme"

myst_enable_extensions = [
    "deflist",
    "fieldlist",
    "attrs_block",
    "colon_fence",
    "substitution",
    "tasklist",
]

autodoc_default_options = {
    "members": True,
    "undoc-members": True,
    "show-inheritance": True,
}

autosummary_generate = True
napoleon_numpy_docstring = True
