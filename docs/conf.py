# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

import os
import sys

# Add source path for autodoc
sys.path.insert(0, os.path.abspath('../configurator/src'))

# -- Project information -----------------------------------------------------
project = 'PMU-30'
copyright = '2024, PMU-30 Team'
author = 'PMU-30 Team'
version = '0.1.1'
release = '0.1.1'

# -- General configuration ---------------------------------------------------
extensions = [
    'myst_parser',              # Markdown support
    'sphinx.ext.autodoc',       # Auto-generate docs from docstrings
    'sphinx.ext.napoleon',      # Google/NumPy style docstrings
    'sphinx.ext.viewcode',      # Add links to source code
    'sphinx.ext.intersphinx',   # Link to other docs
    'sphinx.ext.todo',          # Support for TODO items
    'sphinx.ext.autosummary',   # Generate summary tables
]

# Templates path
templates_path = ['_templates']

# Patterns to exclude from source search
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']

# Source file suffixes
source_suffix = {
    '.rst': 'restructuredtext',
    '.md': 'markdown',
}

# Master doc
master_doc = 'index'

# -- MyST Parser configuration -----------------------------------------------
myst_enable_extensions = [
    'colon_fence',      # ::: fence directive support
    'deflist',          # Definition lists
    'tasklist',         # Checkboxes
    'html_image',       # HTML image support
    'smartquotes',      # Smart quotes
    'replacements',     # Text replacements
    'linkify',          # Auto-link URLs
    'strikethrough',    # ~~strikethrough~~
]

myst_heading_anchors = 3

# -- Options for HTML output -------------------------------------------------
html_theme = 'sphinx_rtd_theme'
html_static_path = ['_static']

# Create _static if it doesn't exist
if not os.path.exists('_static'):
    os.makedirs('_static')

html_theme_options = {
    'navigation_depth': 4,
    'collapse_navigation': False,
    'sticky_navigation': True,
    'titles_only': False,
}

# -- Options for autodoc -----------------------------------------------------
autodoc_default_options = {
    'members': True,
    'undoc-members': True,
    'show-inheritance': True,
}

autodoc_member_order = 'bysource'

# -- Options for intersphinx -------------------------------------------------
intersphinx_mapping = {
    'python': ('https://docs.python.org/3', None),
    'pyqt6': ('https://www.riverbankcomputing.com/static/Docs/PyQt6/', None),
}

# -- Options for todo extension ----------------------------------------------
todo_include_todos = True
