#!/bin/bash

# Build multi-architecture R environment images for venvoy
set -e

echo "🔨 Building multi-architecture venvoy R images..."

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

# Build R images for each version
for R_VERSION in "${R_VERSIONS[@]}"; do
    echo "📊 Building R ${R_VERSION} environment image for all architectures..."
    
    # Build multi-architecture image
    docker buildx build \
        --platform linux/amd64,linux/arm64 \
        --build-arg R_VERSION=${R_VERSION} \
        -f docker/Dockerfile.r \
        -t zaphodbeeblebrox3rd/venvoy:r${R_VERSION} \
        --push \
        .
    
    echo "✅ R ${R_VERSION} image built and pushed"
done

echo "🎉 All R environment images built successfully!"
echo ""
echo "📊 Available R images:"
for R_VERSION in "${R_VERSIONS[@]}"; do
    echo "   - zaphodbeeblebrox3rd/venvoy:r${R_VERSION}"
done
echo ""
echo "🚀 Usage:"
echo "   venvoy init --runtime r --version 4.4 --name my-r-project"
echo "   venvoy run --name my-r-project" 