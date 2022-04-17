# Configuration file for the Sphinx documentation builder.
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Path setup --------------------------------------------------------------

import os
import sys
sys.path.insert(0, os.path.abspath('..'))


# -- Project information -----------------------------------------------------

project = 'vsfieldkit'
copyright = '2022, Justin Turner Arthur'
author = 'Justin Turner Arthur'


# -- General configuration ---------------------------------------------------

extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.intersphinx'
]
templates_path = ['_templates']
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']
intersphinx_mapping = {
    'python': ('https://docs.python.org/3', None),
    'vapoursynth': ('http://www.vapoursynth.com/doc', None)
}
autodoc_mock_imports = ['vapoursynth']
autodoc_typehints = 'both'

# -- Options for HTML output -------------------------------------------------

html_theme = 'alabaster'
html_theme_options = {
    # 'page_width': 'auto',
    # 'body_max_width': 1280
}
html_static_path = ['_static']
mathjax3_config = {
    'options': {
        'enableMenu': False
    }
}