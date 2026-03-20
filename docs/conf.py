# Copyright 2026 Google LLC
# 
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
# 
#     https://www.apache.org/licenses/LICENSE-2.0
# 
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

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