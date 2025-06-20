#!/bin/bash
# Build and push venvoy Docker images
# This script builds multi-architecture images for all Python versions

set -e

# Ensure we're in the project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT"

echo "📁 Working directory: $(pwd)"

REGISTRY="docker.io"
IMAGE_NAME="zaphodbeeblebrox3rd/venvoy"
PYTHON_VERSIONS=("3.9" "3.10" "3.11" "3.12" "3.13")

echo "🚀 Building and pushing venvoy Docker images"
echo "=============================================="

# Check if logged into Docker Hub
if ! docker system info 2>/dev/null | grep -q "Username\|Registry"; then
    # Try alternative check
    if ! docker info 2>/dev/null | grep -i "registry\|username" >/dev/null; then
        echo "⚠️  Cannot verify Docker Hub login status"
        echo "📝 If build fails, please run: docker login"
        echo ""
    fi
fi

echo "✅ Proceeding with Docker Hub operations..."

# Set up buildx if not already done
if ! docker buildx ls | grep -q "venvoy-builder"; then
    echo "🔧 Setting up Docker Buildx..."
    docker buildx create --name venvoy-builder --use
    docker buildx inspect --bootstrap
fi

echo "✅ Docker Buildx ready"

# Build and push each Python version
for version in "${PYTHON_VERSIONS[@]}"; do
    echo ""
    echo "🐍 Building Python $version..."
    
    # Build and push the image
    if docker buildx build \
        --platform linux/amd64,linux/arm64,linux/arm/v7 \
        --build-arg PYTHON_VERSION=$version \
        --tag $REGISTRY/$IMAGE_NAME:python$version \
        --file ./docker/Dockerfile.base \
        --push \
        .; then
        echo "✅ Published: $REGISTRY/$IMAGE_NAME:python$version"
    else
        echo "❌ Failed to build Python $version"
        exit 1
    fi
done

# Create latest tag (Python 3.11)
echo ""
echo "🏷️  Creating latest tag (Python 3.11)..."
docker buildx build \
    --platform linux/amd64,linux/arm64,linux/arm/v7 \
    --build-arg PYTHON_VERSION=3.11 \
    --tag $REGISTRY/$IMAGE_NAME:latest \
    --file ./docker/Dockerfile.base \
    --push \
    .

echo "✅ Published: $REGISTRY/$IMAGE_NAME:latest"

echo ""
echo "🎉 All images published successfully!"
echo ""
echo "📦 Available images:"
for version in "${PYTHON_VERSIONS[@]}"; do
    echo "   docker pull $REGISTRY/$IMAGE_NAME:python$version"
done
echo "   docker pull $REGISTRY/$IMAGE_NAME:latest"
echo ""
echo "🔗 Docker Hub: https://hub.docker.com/r/$IMAGE_NAME" 