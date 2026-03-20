#!/bin/bash
set -e
OUTPUT_DIR="deploy-root"
PACKAGES=("adk" "core" "langchain" "llamaindex")

# Function to setup build environment (not called by default)
setup_build_env() {
    echo "Setting up build environment..."
    # Loop through all packages and install dependencies
    for pkg_dir in packages/*; do
        if [ -d "$pkg_dir" ]; then
            echo "Processing $pkg_dir..."
            
            # Install dependencies if requirements.txt exists
            if [ -f "$pkg_dir/requirements.txt" ]; then
                echo "  Installing requirements from $pkg_dir/requirements.txt..."
                pip install -r "$pkg_dir/requirements.txt"
            fi
            
            # Install the package itself in editable mode
            echo "  Installing $pkg_dir in editable mode..."
            pip install -e "$pkg_dir"
        fi
    done
    echo "Environment setup complete!"
}


build_latest() {
    echo "Building 'latest' documentation..."
    for PKG in "${PACKAGES[@]}"; do
        echo "Processing $PKG..."
        
        # Define directories
        PKG_SRC="packages/toolbox-$PKG/src"
        TEMP_DOC_DIR="build/docs/$PKG"
        
        # Create temporary doc source directory
        mkdir -p "$TEMP_DOC_DIR"
        
        # Generate RST files from source code
        # -f: force overwrite
        # -o: output directory
        echo "  Generating API docs for $PKG..."
        sphinx-apidoc -f -o "$TEMP_DOC_DIR" "$PKG_SRC"
        
        # Create index.rst if it doesn't exist (sphinx-apidoc doesn't create it by default without -F)
        cat > "$TEMP_DOC_DIR/index.rst" <<EOF
Toolbox $PKG
============

.. toctree::
   :maxdepth: 2
   :caption: Contents:

   modules
EOF

        # Build the HTML documentation
        # -c docs: use config from docs/ directory
        # -D: override config values
        echo "  Building HTML for $PKG..."
        sphinx-build -b html \
          -D project="Toolbox $PKG" \
          -D release="latest" \
          -c docs \
          "$TEMP_DOC_DIR" \
          "$OUTPUT_DIR/latest/$PKG"
    done
}

build_tags() {
    echo "Building documentation for tags..."
    for TAG in $(git tag); do
        echo "Processing tag: $TAG"
        # Create a unique temporary directory for the worktree
        WORKTREE_DIR=$(mktemp -d)
        
        # Create a worktree for the specific tag to isolate the build environment
        if git worktree add "$WORKTREE_DIR" "$TAG" > /dev/null 2>&1; then
            for PKG in "${PACKAGES[@]}"; do
                PKG_SRC="$WORKTREE_DIR/packages/toolbox-$PKG/src"
                TEMP_DOC_DIR="build/docs/$TAG/$PKG"
                
                # Create temporary doc source directory
                mkdir -p "$TEMP_DOC_DIR"

                # Check if source exists for this package in this tag
                if [ -d "$PKG_SRC" ]; then
                    echo "  Building docs for $PKG ($TAG)..."
                    
                    # Generate RST files from source code
                    sphinx-apidoc -f -o "$TEMP_DOC_DIR" "$PKG_SRC" >/dev/null 2>&1 || true
                    
                    # Create index.rst
                    cat > "$TEMP_DOC_DIR/index.rst" <<EOF
Toolbox $PKG ($TAG)
===================

.. toctree::
   :maxdepth: 2
   :caption: Contents:

   modules
EOF

                    # Build documentation into versioned subdirectory
                    # We need to tell python where to find the modules in this worktree
                    # Using PYTHONPATH environment variable for sphinx-build
                    export PYTHONPATH="$PKG_SRC"
                    
                    sphinx-build -b html \
                      -D project="Toolbox $PKG ($TAG)" \
                      -D release="$TAG" \
                      -c docs \
                      "$TEMP_DOC_DIR" \
                      "$OUTPUT_DIR/$TAG/$PKG" >/dev/null 2>&1
                else
                    echo "  Skipping $PKG (source not found in $TAG)"
                fi
            done
            # Clean up the worktree
            git worktree remove --force "$WORKTREE_DIR"
        fi
        # Ensure directory is removed
        rm -rf "$WORKTREE_DIR"
    done 
}

generate_registry() {
    # Generate versions.json
    echo "Generating versions.json..."
    python3 -c "import json, subprocess; tags = subprocess.check_output(['git', 'tag']).decode().split(); print(json.dumps(['latest'] + tags))" > "$OUTPUT_DIR/versions.json"
}

copy_assets() {
    # Copy the Portal UI and .nojekyll
    cp docs/templates/index.html "$OUTPUT_DIR/index.html"
    touch "$OUTPUT_DIR/.nojekyll"
}

# --- Main Execution ---

# Optional: setup_build_env

build_latest
build_tags
generate_registry
copy_assets