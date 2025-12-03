#!/bin/bash

# Build ARM64-only Python environment images for venvoy
# Run this on an ARM64 machine (M1/M2/M3 Mac, ARM64 Linux, etc.)
set -e

# Ensure we're in the project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT"

echo "🔨 Building ARM64-only venvoy Python images..."

# Python versions to build
PYTHON_VERSIONS=("3.9" "3.10" "3.11" "3.12" "3.13")

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

# Build Python images for each version (ARM64 only)
for PYTHON_VERSION in "${PYTHON_VERSIONS[@]}"; do
    echo ""
    echo "🐍 Building Python ${PYTHON_VERSION} environment image for ARM64..."
    
    if [ "$CONTAINER_RUNTIME" = "docker" ]; then
        # Build ARM64-only image
        docker buildx build \
            --platform linux/arm64 \
            --build-arg PYTHON_VERSION=${PYTHON_VERSION} \
            -f docker/Dockerfile.base \
            -t ${REGISTRY}/${IMAGE_NAME}:python${PYTHON_VERSION}-arm64 \
            --push \
            .
        
        echo "✅ Python ${PYTHON_VERSION} ARM64 image built and pushed"
    elif [ "$CONTAINER_RUNTIME" = "podman" ]; then
        if podman build \
            --build-arg PYTHON_VERSION=${PYTHON_VERSION} \
            -f docker/Dockerfile.base \
            -t ${REGISTRY}/${IMAGE_NAME}:python${PYTHON_VERSION}-arm64 \
            .; then
            echo "📤 Pushing ${REGISTRY}/${IMAGE_NAME}:python${PYTHON_VERSION}-arm64..."
            if podman push ${REGISTRY}/${IMAGE_NAME}:python${PYTHON_VERSION}-arm64; then
                echo "✅ Python ${PYTHON_VERSION} ARM64 image built and pushed"
            else
                echo "❌ Failed to push Python ${PYTHON_VERSION} ARM64"
                exit 1
            fi
        else
            echo "❌ Failed to build Python ${PYTHON_VERSION} ARM64"
            exit 1
        fi
    fi
done

# Create latest tag (Python 3.11) for ARM64
echo ""
echo "🏷️  Creating latest tag (Python 3.11) for ARM64..."
if [ "$CONTAINER_RUNTIME" = "docker" ]; then
    docker buildx build \
        --platform linux/arm64 \
        --build-arg PYTHON_VERSION=3.11 \
        -f docker/Dockerfile.base \
        -t ${REGISTRY}/${IMAGE_NAME}:latest-arm64 \
        --push \
        .
    echo "✅ Published: ${REGISTRY}/${IMAGE_NAME}:latest-arm64"
elif [ "$CONTAINER_RUNTIME" = "podman" ]; then
    if podman build \
        --build-arg PYTHON_VERSION=3.11 \
        -f docker/Dockerfile.base \
        -t ${REGISTRY}/${IMAGE_NAME}:latest-arm64 \
        .; then
        echo "📤 Pushing ${REGISTRY}/${IMAGE_NAME}:latest-arm64..."
        if podman push ${REGISTRY}/${IMAGE_NAME}:latest-arm64; then
            echo "✅ Published: ${REGISTRY}/${IMAGE_NAME}:latest-arm64"
        else
            echo "❌ Failed to push latest-arm64 tag"
            exit 1
        fi
    else
        echo "❌ Failed to build latest-arm64 tag"
        exit 1
    fi
fi

echo ""
echo "🎉 All ARM64 Python environment images built successfully!"
echo ""
echo "🐍 Available ARM64 Python images:"
for PYTHON_VERSION in "${PYTHON_VERSIONS[@]}"; do
    echo "   - ${REGISTRY}/${IMAGE_NAME}:python${PYTHON_VERSION}-arm64"
done
echo "   - ${REGISTRY}/${IMAGE_NAME}:latest-arm64"
echo ""
echo "🚀 Usage:"
echo "   venvoy init --python-version 3.11 --name my-python-project"
echo "   venvoy run --name my-python-project"

