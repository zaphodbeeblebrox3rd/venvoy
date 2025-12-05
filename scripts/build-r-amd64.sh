#!/bin/bash

# Build AMD64-only R environment images for venvoy
set -e

# Ensure we're in the project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT"

echo "🔨 Building AMD64-only venvoy R images..."

# R versions to build
R_VERSIONS=("4.2" "4.3" "4.4" "4.5")

# Create or use existing multi-architecture builder
if ! docker buildx ls | grep -q "venvoy-multiarch"; then
    echo "🔧 Creating multi-architecture builder..."
    docker buildx create --name venvoy-multiarch --use --bootstrap
else
    echo "🔧 Using existing multi-architecture builder..."
    docker buildx use venvoy-multiarch
fi

# Build R images for each version (AMD64 only)
for R_VERSION in "${R_VERSIONS[@]}"; do
    echo "📊 Building R ${R_VERSION} environment image for AMD64..."
    
    # Build AMD64-only image
    docker buildx build \
        --platform linux/amd64 \
        --build-arg R_VERSION=${R_VERSION} \
        -f docker/Dockerfile.r \
        -t zaphodbeeblebrox3rd/venvoy:r${R_VERSION}-amd64 \
        --push \
        .
    
    echo "✅ R ${R_VERSION} AMD64 image built and pushed"
done

echo "🎉 All AMD64 R environment images built successfully!"
echo ""
echo "📊 Available AMD64 R images:"
for R_VERSION in "${R_VERSIONS[@]}"; do
    echo "   - zaphodbeeblebrox3rd/venvoy:r${R_VERSION}-amd64"
done
echo ""
echo "🚀 Usage:"
echo "   venvoy init --runtime r --r-version 4.4 --name my-r-project"
echo "   venvoy run --name my-r-project" 