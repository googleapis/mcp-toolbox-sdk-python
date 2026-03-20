#!/bin/bash
set -e
OUTPUT_DIR="deploy-root"
PACKAGES=("core" "adk" "langchain" "llmgraph")

# 1. Build "Latest" for all packages
for PKG in "${PACKAGES[@]}"; do
    sphinx-build -b html "packages/toolbox-$PKG/docs" "$OUTPUT_DIR/latest/$PKG"
done

# 2. Build for specific Tags
for TAG in $(git tag); do
    echo "Processing tag: $TAG"
    # Create a unique temporary directory for the worktree
    WORKTREE_DIR=$(mktemp -d)
    
    # Create a worktree for the specific tag to isolate the build environment
    if git worktree add "$WORKTREE_DIR" "$TAG" > /dev/null 2>&1; then
        for PKG in "${PACKAGES[@]}"; do
            DOC_SRC="$WORKTREE_DIR/packages/toolbox-$PKG/docs"
            # Check if docs exist for this package in this tag
            if [ -d "$DOC_SRC" ]; then
                echo "  Building docs for $PKG ($TAG)..."
                # Build documentation into versioned subdirectory
                sphinx-build -b html "$DOC_SRC" "$OUTPUT_DIR/$TAG/$PKG"
            else
                echo "  Skipping $PKG (docs not found in $TAG)"
            fi
        done
        # Clean up the worktree
        git worktree remove --force "$WORKTREE_DIR"
    fi
    # Ensure directory is removed
    rm -rf "$WORKTREE_DIR"
done 


# 3. Copy the Portal UI and .nojekyll
cp docs/templates/index.html "$OUTPUT_DIR/index.html"
touch "$OUTPUT_DIR/.nojekyll"