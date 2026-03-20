#!/bin/bash
set -e
OUTPUT_DIR="build/api-docs"
PACKAGES=("adk" "core" "langchain" "llamaindex")

# Function to setup build environment (not called by default)
setup_build_env() {
    echo "Setting up build environment..."
    for pkg_dir in packages/*; do
        if [ -d "$pkg_dir" ]; then
            echo "Processing $pkg_dir..."
            # Use pushd/popd to ensure relative paths in requirements.txt (like -e ../toolbox-core) resolve correctly
            pushd "$pkg_dir" >/dev/null
            if [ -f "requirements.txt" ]; then
                echo "  Installing requirements from $pkg_dir/requirements.txt..."
                pip install -r "requirements.txt"
            fi
            echo "  Installing $pkg_dir in editable mode..."
            pip install -e .
            popd >/dev/null
        fi
    done
    echo "Environment setup complete!"
}

# Generic function to build documentation for a package
generate_package_docs() {
    local PKG_NAME=$1
    local VERSION_TAG=$2
    local SOURCE_DIR=$3

    local TEMP_DOC_DIR="build/docs/$VERSION_TAG/$PKG_NAME"
    local OUTPUT_SUBDIR="$OUTPUT_DIR/$VERSION_TAG/$PKG_NAME"
    
    echo "  Generating docs for $PKG_NAME ($VERSION_TAG)..."
    
    # Ensure directories exist
    mkdir -p "$TEMP_DOC_DIR"
    mkdir -p "$OUTPUT_SUBDIR"

    # Generate ReStructuredText files from source code
    # Using '|| true' to suppress warnings from apidoc but continue
    sphinx-apidoc -f -o "$TEMP_DOC_DIR" "$SOURCE_DIR" >/dev/null 2>&1 || true

    # Create index.rst
    cat > "$TEMP_DOC_DIR/index.rst" <<DOC_EOF
Toolbox $PKG_NAME
=================

.. toctree::
   :maxdepth: 2
   :caption: Contents:

   modules
DOC_EOF

    # Build HTML documentation
    # Passing SOURCE_DIR in PYTHONPATH to ensure modules are importable
    local STATUS=0
    PYTHONPATH="$SOURCE_DIR" sphinx-build -b html \
        -D project="Toolbox $PKG_NAME ($VERSION_TAG)" \
        -D release="$VERSION_TAG" \
        -c docs \
        "$TEMP_DOC_DIR" \
        "$OUTPUT_SUBDIR" >/dev/null 2>&1 || STATUS=$?

    if [ $STATUS -ne 0 ]; then
        echo "    Warning: Sphinx build failed for $PKG_NAME ($VERSION_TAG)"
    fi
}

build_latest() {
    echo "Building 'latest' documentation..."
    for PKG in "${PACKAGES[@]}"; do
        local PKG_SRC="packages/toolbox-$PKG/src"
        if [ -d "$PKG_SRC" ]; then
            generate_package_docs "$PKG" "latest" "$PKG_SRC"
        else
            echo "  Skipping $PKG (source not found)"
        fi
    done
}

build_tags() {
    echo "Building documentation for tags..."
    local TAGS
    TAGS=$(git tag --sort=-v:refname)
    
    for TAG in $TAGS; do
        echo "Processing tag: $TAG"
        local WORKTREE_DIR
        WORKTREE_DIR=$(mktemp -d)
        
        # Create a clean worktree for the tag
        if git worktree add "$WORKTREE_DIR" "$TAG" > /dev/null 2>&1; then
            for PKG in "${PACKAGES[@]}"; do
                local PKG_SRC="$WORKTREE_DIR/packages/toolbox-$PKG/src"
                # Check if package existed in that tag
                if [ -d "$PKG_SRC" ]; then
                    generate_package_docs "$PKG" "$TAG" "$PKG_SRC"
                else
                    echo "  Skipping $PKG (source not found in $TAG)"
                fi
            done
            # Clean up worktree
            git worktree remove --force "$WORKTREE_DIR" >/dev/null 2>&1
        fi
        # Ensure temporary directory is removed
        rm -rf "$WORKTREE_DIR"
    done
}

generate_registry() {
    echo "Generating versions.json..."

    python3 <<EOF > "$OUTPUT_DIR/versions.json"
import json
import subprocess

try:
    tags = subprocess.check_output(
        ['git', 'tag', '--sort=-v:refname']
    ).decode().split()
except:
    tags = []

print(json.dumps(['latest'] + tags))
EOF

    echo "Generated versions.json:"
    cat "$OUTPUT_DIR/versions.json"
}

copy_assets() {
    echo "Copying static assets..."
    cp docs/templates/index.html "$OUTPUT_DIR/index.html"
    touch "$OUTPUT_DIR/.nojekyll"
}

# --- Main Execution ---

mkdir -p "$OUTPUT_DIR"

setup_build_env
build_latest
build_tags
generate_registry
copy_assets