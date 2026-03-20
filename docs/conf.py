import os
import sys
import glob

for path in glob.glob('../packages/*/src'):
    sys.path.insert(0, os.path.abspath(path))

autodoc_default_options = {
    'members': True,
    'undoc-members': True,
    'show-inheritance': True,
}

extensions = ['sphinx.ext.autodoc', 'sphinx.ext.napoleon', 'sphinx.ext.viewcode']
html_theme = 'sphinx_rtd_theme'
project = 'MCP Toolbox Python SDK'

html_static_path = ['_static']
html_js_files = ['js/versions.js']