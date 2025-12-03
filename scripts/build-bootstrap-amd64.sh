#!/bin/bash

# Build AMD64-only bootstrap image for venvoy
# The bootstrap image contains the venvoy CLI and is used by the installer
# and the 'venvoy update' command
set -e

# Ensure we're in the project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT"

echo "🔨 Building AMD64-only venvoy bootstrap image..."

REGISTRY="docker.io"
IMAGE_NAME="zaphodbeeblebrox3rd/venvoy"

# Detect container runtime (Docker or Podman)
CONTAINER_RUNTIME=""
if command -v docker &> /dev/null && docker info &> /dev/null; then
    CONTAINER_RUNTIME="docker"
elif command -v podman &> /dev/null; then
    CONTAINER_RUNTIME="podman"
else
    echo "❌ No container runtime found. Please install Docker or Podman."
    exit 1
fi

# Create or use existing multi-architecture builder
if [ "$CONTAINER_RUNTIME" = "docker" ]; then
    if ! docker buildx version &> /dev/null; then
        echo "❌ Docker BuildX not available. Please install Docker BuildX."
        echo "   Docker Desktop includes BuildX by default."
        echo "   For Linux: docker buildx install"
        exit 1
    fi
    
    if ! docker buildx ls | grep -q "venvoy-multiarch"; then
        echo "🔧 Creating multi-architecture builder..."
        docker buildx create --name venvoy-multiarch --use --bootstrap
    else
        echo "🔧 Using existing multi-architecture builder..."
        docker buildx use venvoy-multiarch
    fi
fi

# Build bootstrap image (AMD64 only)
echo "📦 Building bootstrap image for AMD64..."
echo "   This includes the entrypoint that supports mounted source code"
echo "   and uses ContainerManager instead of DockerManager"

if [ "$CONTAINER_RUNTIME" = "docker" ]; then
    docker buildx build \
        --platform linux/amd64 \
        --build-arg PYTHON_VERSION=3.11 \
        -f docker/Dockerfile.bootstrap \
        -t ${REGISTRY}/${IMAGE_NAME}:bootstrap-amd64 \
        --push \
        .
    
    echo "✅ Bootstrap image (AMD64) built and pushed successfully!"
elif [ "$CONTAINER_RUNTIME" = "podman" ]; then
    if podman build \
        --build-arg PYTHON_VERSION=3.11 \
        -f docker/Dockerfile.bootstrap \
        -t ${REGISTRY}/${IMAGE_NAME}:bootstrap-amd64 \
        .; then
        echo "📤 Pushing ${REGISTRY}/${IMAGE_NAME}:bootstrap-amd64..."
        if podman push ${REGISTRY}/${IMAGE_NAME}:bootstrap-amd64; then
            echo "✅ Bootstrap image (AMD64) built and pushed successfully!"
        else
            echo "❌ Failed to push bootstrap image"
            exit 1
        fi
    else
        echo "❌ Failed to build bootstrap image"
        exit 1
    fi
fi

echo ""
echo "🎯 Bootstrap image features:"
echo "   • Contains venvoy CLI installed from git"
echo "   • Smart entrypoint that supports mounted source code"
echo "   • Uses ContainerManager instead of DockerManager"
echo "   • Works with Apptainer, Singularity, Docker, and Podman"

