#!/bin/bash
# Build and push venvoy container images
# This script builds multi-architecture images for all Python versions
# Supports both Docker and Podman

set -e

# Ensure we're in the project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT"

echo "📁 Working directory: $(pwd)"

REGISTRY="docker.io"
IMAGE_NAME="zaphodbeeblebrox3rd/venvoy"
PYTHON_VERSIONS=("3.9" "3.10" "3.11" "3.12" "3.13")

# Detect container runtime (Docker or Podman)
CONTAINER_RUNTIME=""
if command -v docker &> /dev/null; then
    # Check if Docker is accessible
    if docker info &> /dev/null; then
        CONTAINER_RUNTIME="docker"
    else
        # Docker is installed but not accessible - check if it's a permission issue
        if docker info 2>&1 | grep -q "permission denied"; then
            echo "❌ Docker permission denied"
            echo ""
            echo "💡 Your user is in the docker group, but this shell session doesn't have it active."
            echo "   Try one of these solutions:"
            echo ""
            echo "   1. Run with docker group: sg docker -c \"$0\""
            echo "   2. Start new shell: newgrp docker"
            echo "   3. Log out and log back in"
            echo ""
            if command -v podman &> /dev/null; then
                echo "   Or use Podman instead: CONTAINER_RUNTIME=podman $0"
            fi
            exit 1
        elif command -v podman &> /dev/null; then
            CONTAINER_RUNTIME="podman"
            echo "⚠️  Docker found but not accessible, using Podman instead"
        else
            CONTAINER_RUNTIME="docker"
        fi
    fi
elif command -v podman &> /dev/null; then
    CONTAINER_RUNTIME="podman"
else
    echo "❌ No container runtime found. Please install Docker or Podman."
    exit 1
fi

echo "🚀 Building and pushing venvoy container images"
echo "=============================================="
echo "🔧 Using container runtime: $CONTAINER_RUNTIME"

# Check if logged into registry
if [ "$CONTAINER_RUNTIME" = "docker" ]; then
    if ! docker system info 2>/dev/null | grep -q "Username\|Registry"; then
        if ! docker info 2>/dev/null | grep -i "registry\|username" >/dev/null; then
            echo "⚠️  Cannot verify Docker Hub login status"
            echo "📝 If build fails, please run: docker login"
            echo ""
        fi
    fi
    echo "✅ Proceeding with Docker Hub operations..."
    
    # Set up buildx if not already done
    if ! docker buildx ls 2>/dev/null | grep -q "venvoy-builder"; then
        echo "🔧 Setting up Docker Buildx..."
        docker buildx create --name venvoy-builder --use 2>/dev/null || {
            echo "⚠️  Failed to create buildx builder, trying to use default..."
        }
        docker buildx inspect --bootstrap 2>/dev/null || true
    fi
    echo "✅ Docker Buildx ready"
elif [ "$CONTAINER_RUNTIME" = "podman" ]; then
    echo "✅ Using Podman for builds"
    # Podman doesn't require buildx, uses podman build directly
fi

# Build and push each Python version
for version in "${PYTHON_VERSIONS[@]}"; do
    echo ""
    echo "🐍 Building Python $version..."
    
    # Build and push the image
    if [ "$CONTAINER_RUNTIME" = "docker" ]; then
        if docker buildx build \
            --platform linux/amd64,linux/arm64 \
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
    elif [ "$CONTAINER_RUNTIME" = "podman" ]; then
        # Podman build (single architecture for now - multi-arch requires manifest creation)
        # Note: Podman can build multi-arch but requires separate builds and manifest creation
        if podman build \
            --build-arg PYTHON_VERSION=$version \
            --tag $REGISTRY/$IMAGE_NAME:python$version \
            --file ./docker/Dockerfile.base \
            .; then
            echo "📤 Pushing $REGISTRY/$IMAGE_NAME:python$version..."
            if podman push $REGISTRY/$IMAGE_NAME:python$version; then
                echo "✅ Published: $REGISTRY/$IMAGE_NAME:python$version"
            else
                echo "❌ Failed to push Python $version"
                exit 1
            fi
        else
            echo "❌ Failed to build Python $version"
            exit 1
        fi
    fi
done

# Create latest tag (Python 3.11)
echo ""
echo "🏷️  Creating latest tag (Python 3.11)..."
if [ "$CONTAINER_RUNTIME" = "docker" ]; then
    docker buildx build \
        --platform linux/amd64,linux/arm64 \
        --build-arg PYTHON_VERSION=3.11 \
        --tag $REGISTRY/$IMAGE_NAME:latest \
        --file ./docker/Dockerfile.base \
        --push \
        .
elif [ "$CONTAINER_RUNTIME" = "podman" ]; then
    podman build \
        --build-arg PYTHON_VERSION=3.11 \
        --tag $REGISTRY/$IMAGE_NAME:latest \
        --file ./docker/Dockerfile.base \
        .
    echo "📤 Pushing $REGISTRY/$IMAGE_NAME:latest..."
    podman push $REGISTRY/$IMAGE_NAME:latest
fi

echo "✅ Published: $REGISTRY/$IMAGE_NAME:latest"

echo ""
echo "🎉 All images published successfully!"
echo ""
echo "📦 Available images:"
for version in "${PYTHON_VERSIONS[@]}"; do
    echo "   $CONTAINER_RUNTIME pull $REGISTRY/$IMAGE_NAME:python$version"
done
echo "   $CONTAINER_RUNTIME pull $REGISTRY/$IMAGE_NAME:latest"
echo ""
echo "🔗 Docker Hub: https://hub.docker.com/r/$IMAGE_NAME" 