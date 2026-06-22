#!/bin/bash
# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

set -euo pipefail

PACKAGE="${1:?package required (core|adk|langchain|llamaindex)}"
VERSION="${2:?version required (e.g. v1.0.0 or dev)}"
BASE_URL="${3:-/}"

# Absolute repo root: the pydoc-markdown config's search_path is resolved
# relative to the config file's directory (a temp dir), not the CWD, so it must
# be absolute. Captured before the later `cd docs-site`.
ROOT="$(pwd)"

# Map the URL slug to its package title and the curated list of public modules
# to document. The list is explicit (not whole-package recursion) so internal
# surface -- utils, itransport, the mcp_transport.v* protocol impls, and every
# package's version module -- stays out of the page, matching the Go/JS docs.
case "$PACKAGE" in
  core)
    TITLE="Core"
    MODULES=(client sync_client tool sync_tool auth_methods protocol) ;;
  adk)
    TITLE="ADK"
    MODULES=(client tool toolset credentials) ;;
  langchain)
    TITLE="LangChain"
    MODULES=(client tools async_client async_tools) ;;
  llamaindex)
    TITLE="LlamaIndex"
    MODULES=(client tools async_client async_tools) ;;
  *) echo "Unknown package: $PACKAGE" >&2; exit 1 ;;
esac

DIR="packages/toolbox-${PACKAGE}"
MODULE="toolbox_${PACKAGE}"

# Per-build content tree in a temp dir, kept out of the checked-in
# docs-site/content so concurrent package builds never trample each other.
# The package's API reference is the home page, so /<pkg>/<version>/ lands
# directly on the docs (the repo README lives only at the site root).
CONTENT_DIR="$(mktemp -d)"
CFG="$(mktemp)"
# return 0 so a leftover non-zero never becomes the script's exit code, since an
# EXIT trap's last status replaces it.
cleanup() { rm -rf "$CONTENT_DIR"; rm -f "$CFG"; return 0; }
trap cleanup EXIT

# Build the YAML module block ("      - toolbox_<pkg>.<mod>" per line).
MODULE_YAML=""
for m in "${MODULES[@]}"; do
  MODULE_YAML+="      - ${MODULE}.${m}"$'\n'
done

# Generate the package's API reference as a single markdown page.
# pydoc-markdown parses the source statically (AST via docspec-python); it never
# imports the package, so the wrappers (adk/langchain/llamaindex) document their
# toolbox_core references as plain names without core being installed or built --
# no dependency build step is needed for any package.
#   filter (exclude_private, skip_empty_modules): drop _-prefixed internals and
#     empty modules; dunders like __init__/__call__ are kept (public surface).
#   google: parse Google-style Args:/Returns:/Raises: blocks.
#   crossref: resolve {@link X}-style refs to in-page #anchors (no stray .md).
#   renderer markdown -> a single _index.md, the Hugo section index for
#     /<pkg>/<version>/. Parameters render as lists (Go-SDK style); the Raises
#     section is kept as pydoc-markdown emits it.
cat > "$CFG" <<YAML
loaders:
  - type: python
    search_path: ["${ROOT}/${DIR}/src"]
    modules:
${MODULE_YAML}processors:
  - type: filter
    exclude_private: true
    skip_empty_modules: true
  - type: google
  - type: crossref
renderer:
  type: markdown
  filename: "${CONTENT_DIR}/_index.md"
  render_toc: false
YAML
pydoc-markdown "$CFG"

# Prepend Docsy frontmatter (type: docs + the friendly "<Title> (<version>)"
# heading) to the generated page so Docsy renders the section index correctly.
tmp="$(mktemp)"
{ printf -- '---\ntitle: "%s"\ntype: docs\n---\n\n' "${TITLE} (${VERSION})"; cat "${CONTENT_DIR}/_index.md"; } > "$tmp"
mv "$tmp" "${CONTENT_DIR}/_index.md"

cd docs-site
HUGO_PARAMS_VERSION="${VERSION}" HUGO_PARAMS_PACKAGE="${PACKAGE}" hugo \
  --minify \
  --contentDir "${CONTENT_DIR}" \
  --baseURL "${BASE_URL}${PACKAGE}/${VERSION}/" \
  --destination "public/${PACKAGE}/${VERSION}"

# Hoist the home-scoped outputs from this version's dir up to the package root,
# where the navbar version selector fetches them. They list every version of the
# package, so they must live once per package (not per version) and are shared
# across all of this package's version pages. keep_files on deploy preserves them.
mv "public/${PACKAGE}/${VERSION}/releases.releases" "public/${PACKAGE}/releases.releases"
mkdir -p "public/${PACKAGE}/latest"
mv "public/${PACKAGE}/${VERSION}/latest.html" "public/${PACKAGE}/latest/index.html"
