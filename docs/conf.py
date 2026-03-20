import os
import sys
sys.path.insert(0, os.path.abspath('../packages/toolbox-adk'))
sys.path.insert(0, os.path.abspath('../packages/toolbox-core'))
sys.path.insert(0, os.path.abspath('../packages/toolbox-langchain'))
sys.path.insert(0, os.path.abspath('../packages/toolbox-llamaindex'))

extensions = ['sphinx.ext.autodoc', 'sphinx.ext.napoleon', 'sphinx.ext.viewcode']
html_theme = 'sphinx_rtd_theme'
project = 'MCP Toolbox Python SDK'