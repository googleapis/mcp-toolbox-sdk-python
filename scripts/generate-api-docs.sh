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

export PATH="$PATH:$(go env GOPATH)/bin"

PACKAGE="${1:?package required (core|tbadk|tbgenkit)}"
VERSION="${2:?version required (e.g. v1.0.0 or dev)}"
BASE_URL="${3:-/}"

case "$PACKAGE" in
  core)     TITLE="Core" ;;
  tbadk)    TITLE="Tbadk" ;;
  tbgenkit) TITLE="Tbgenkit" ;;
  *)        echo "Unknown package: $PACKAGE" >&2; exit 1 ;;
esac

go install github.com/princjef/gomarkdoc/cmd/gomarkdoc@latest

# Per-build content tree in a temp dir, kept out of the checked-in
# docs-site/content so concurrent package builds never trample each other.
# The package's API reference is the home page, so /<pkg>/<version>/ lands
# directly on the docs (the repo README lives only at the site root).
CONTENT_DIR="$(mktemp -d)"
trap 'rm -rf "$CONTENT_DIR"' EXIT

cat > "$CONTENT_DIR/_index.md" <<EOF
---
title: "MCP Toolbox Go SDK — ${TITLE} (${VERSION})"
type: docs
---

EOF
gomarkdoc "./${PACKAGE}/..." | sed '/^# /d' >> "$CONTENT_DIR/_index.md"

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
