import os
import sys
sys.path.insert(0, os.path.abspath('../packages/toolbox-adk/src'))
sys.path.insert(0, os.path.abspath('../packages/toolbox-core/src'))
sys.path.insert(0, os.path.abspath('../packages/toolbox-langchain/src'))
sys.path.insert(0, os.path.abspath('../packages/toolbox-llamaindex/src'))

extensions = ['sphinx.ext.autodoc', 'sphinx.ext.napoleon', 'sphinx.ext.viewcode']
html_theme = 'sphinx_rtd_theme'
project = 'MCP Toolbox Python SDK'

html_static_path = ['_static']
html_js_files = ['js/versions.js']