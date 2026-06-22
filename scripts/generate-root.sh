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

BASE_URL="${1:-/}"

# Render the repo README (from the checked-out tag) as the root landing page.
# Built only on tag pushes so the root URL tracks the latest release and stays
# stable between main-branch dev builds.
CONTENT_DIR="$(mktemp -d)"
trap 'rm -rf "$CONTENT_DIR"' EXIT

cat > "$CONTENT_DIR/_index.md" <<EOF
---
title: "MCP Toolbox Python API Reference"
type: docs
---
EOF
# Strip the README's leading H1 and its hand-maintained TOC block before
# appending: Docsy already renders the page title as an H1 and an "On this page"
# TOC, so leaving them in would duplicate both on the landing page.
awk '
  /<!-- TOC -->/ { intoc = 1 }
  intoc { if (/<!-- \/TOC -->/) intoc = 0; next }
  !h1done && /^# / { h1done = 1; next }
  { print }
' README.md >> "$CONTENT_DIR/_index.md"

cd docs-site
hugo \
  --minify \
  --contentDir "${CONTENT_DIR}" \
  --baseURL "${BASE_URL}" \
  --destination "public"
