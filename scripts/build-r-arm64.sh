#!/bin/bash

# Build ARM64-only R environment images for venvoy
# Run this on an ARM64 machine (M1/M2/M3 Mac, ARM64 Linux, etc.)
set -e

# Ensure we're in the project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT"

echo "🔨 Building ARM64-only venvoy R images..."

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

# Build R images for each version (ARM64 only)
for R_VERSION in "${R_VERSIONS[@]}"; do
    echo "📊 Building R ${R_VERSION} environment image for ARM64..."
    
    # Build ARM64-only image
    docker buildx build \
        --platform linux/arm64 \
        --build-arg R_VERSION=${R_VERSION} \
        -f docker/Dockerfile.r \
        -t zaphodbeeblebrox3rd/venvoy:r${R_VERSION}-arm64 \
        --push \
        .
    
    echo "✅ R ${R_VERSION} ARM64 image built and pushed"
done

echo "🎉 All ARM64 R environment images built successfully!"
echo ""
echo "📊 Available ARM64 R images:"
for R_VERSION in "${R_VERSIONS[@]}"; do
    echo "   - zaphodbeeblebrox3rd/venvoy:r${R_VERSION}-arm64"
done
echo ""
echo "🚀 Usage:"
echo "   venvoy init --runtime r --r-version 4.4 --name my-r-project"
echo "   venvoy run --name my-r-project" 