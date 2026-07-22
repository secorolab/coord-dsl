# SPDX-License-Identifier: MPL-2.0
# Configuration file for the Sphinx documentation builder.

project = "coord-dsl"
copyright = "2026, SECORO"
author = "SECORO"

extensions = [
    "sphinx.ext.duration",
    "sphinx.ext.githubpages",
]

templates_path = ["_templates"]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

# -- HTML output (Furo) ------------------------------------------------------
html_theme = "furo"
html_title = "coord-dsl"
html_static_path = ["_static"]

html_theme_options = {
    "source_repository": "https://github.com/secorolab/coord-dsl/",
    "source_branch": "main",
    "source_directory": "docs/",
}

# Highlight the DSL blocks as YAML-ish / C++-ish where it reads best.
highlight_language = "text"
pygments_style = "friendly"
pygments_dark_style = "monokai"
