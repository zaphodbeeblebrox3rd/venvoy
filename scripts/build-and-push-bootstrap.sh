#!/bin/bash
# Build and push updated bootstrap image with new entrypoint logic

set -e

echo "🔨 Building updated bootstrap image with dynamic source mounting..."

# Ensure buildx is available
if ! docker buildx version &> /dev/null; then
    echo "❌ Docker BuildX not available. Please install Docker BuildX."
    echo "   Docker Desktop includes BuildX by default."
    echo "   For Linux: docker buildx install"
    exit 1
fi

# Create and use a new builder instance for multi-arch builds
BUILDER_NAME="venvoy-multiarch"
if ! docker buildx inspect "$BUILDER_NAME" &> /dev/null; then
    echo "🔧 Creating multi-architecture builder..."
    docker buildx create --name "$BUILDER_NAME" --use
else
    echo "🔧 Using existing multi-architecture builder..."
    docker buildx use "$BUILDER_NAME"
fi

# Build bootstrap image (single multi-arch image)
echo "📦 Building updated bootstrap image for all architectures..."
echo "   This includes the new entrypoint that supports mounted source code"
echo "   and uses ContainerManager instead of DockerManager"

docker buildx build \
    --platform linux/amd64,linux/arm64 \
    --build-arg PYTHON_VERSION=3.11 \
    -f docker/Dockerfile.bootstrap \
    -t zaphodbeeblebrox3rd/venvoy:bootstrap \
    --push \
    .

echo "✅ Bootstrap image built and pushed successfully!"
echo ""
echo "🎯 What this fixes:"
echo "   • Bootstrap container now has smart entrypoint"
echo "   • Supports mounted source code via VENVOY_SOURCE_DIR"
echo "   • Uses ContainerManager instead of DockerManager"
echo "   • Works with Apptainer, Singularity, Docker, and Podman"
echo ""
echo "🚀 Users will get the updated bootstrap image when they run:"
echo "   • venvoy update"
echo "   • Fresh installs"
echo ""
echo "💡 The Python environment images (python3.11, python3.12, etc.)"
echo "   don't need to be rebuilt - they're just base Python environments."
