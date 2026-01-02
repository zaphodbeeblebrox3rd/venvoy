#!/bin/bash

# Build multi-architecture bootstrap image for venvoy
# The bootstrap image contains the venvoy CLI and is used by the installer
# and the 'venvoy update' command
set -e

# Ensure we're in the project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT"

echo "🔨 Building multi-architecture venvoy bootstrap image..."

REGISTRY="docker.io"
IMAGE_NAME="zaphodbeeblebrox3rd/venvoy"

# Detect container runtime (Docker or Podman)
# Check if docker is actually Docker (has buildx) or a Podman wrapper
CONTAINER_RUNTIME=""
if command -v docker &> /dev/null && docker info &> /dev/null; then
    # Check if docker buildx actually works and is Docker (not Podman wrapper)
    # Podman's buildx wrapper returns "buildah" in version, Docker returns "github.com/docker/buildx"
    BUILDX_VERSION=$(docker buildx version 2>&1)
    if echo "$BUILDX_VERSION" | grep -q "github.com/docker/buildx\|buildx v"; then
        CONTAINER_RUNTIME="docker"
    elif command -v podman &> /dev/null; then
        # docker exists but buildx output suggests Podman wrapper
        CONTAINER_RUNTIME="podman"
    else
        CONTAINER_RUNTIME="docker"
    fi
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

# Build bootstrap image (single multi-arch image)
echo "📦 Building bootstrap image for all architectures..."
echo "   This includes the entrypoint that supports mounted source code"
echo "   and uses ContainerManager instead of DockerManager"

if [ "$CONTAINER_RUNTIME" = "docker" ]; then
    docker buildx build \
        --platform linux/amd64,linux/arm64 \
        --build-arg PYTHON_VERSION=3.11 \
        -f docker/Dockerfile.bootstrap \
        -t ${REGISTRY}/${IMAGE_NAME}:bootstrap \
        --push \
        .
    
    echo "✅ Bootstrap image built and pushed successfully!"
elif [ "$CONTAINER_RUNTIME" = "podman" ]; then
    echo "🔨 Building multi-architecture bootstrap image with Podman..."
    # Build for amd64
    echo "   Building for linux/amd64..."
    AMD64_TAG="${REGISTRY}/${IMAGE_NAME}:bootstrap-amd64"
    if ! podman build \
        --platform linux/amd64 \
        --build-arg PYTHON_VERSION=3.11 \
        -f docker/Dockerfile.bootstrap \
        -t ${AMD64_TAG} \
        .; then
        echo "❌ Failed to build amd64 bootstrap image"
        exit 1
    fi
    
    # Build for arm64
    echo "   Building for linux/arm64..."
    ARM64_TAG="${REGISTRY}/${IMAGE_NAME}:bootstrap-arm64"
    if ! podman build \
        --platform linux/arm64 \
        --build-arg PYTHON_VERSION=3.11 \
        -f docker/Dockerfile.bootstrap \
        -t ${ARM64_TAG} \
        .; then
        echo "❌ Failed to build arm64 bootstrap image"
        exit 1
    fi
    
    # Push both architecture-specific images
    echo "📤 Pushing architecture-specific images..."
    if ! podman push ${AMD64_TAG}; then
        echo "❌ Failed to push amd64 bootstrap image"
        exit 1
    fi
    if ! podman push ${ARM64_TAG}; then
        echo "❌ Failed to push arm64 bootstrap image"
        exit 1
    fi
    
    # Create and push manifest list for multi-arch
    echo "🔗 Creating multi-architecture manifest..."
    FINAL_TAG="${REGISTRY}/${IMAGE_NAME}:bootstrap"
    # Remove existing manifest and image if they exist (required for Podman)
    # Note: Podman automatically tags images with both architecture-specific and final tags
    # When building amd64, it tags as both "bootstrap-amd64" AND "bootstrap"
    # We need to remove the final tag (whether it's a manifest or image) before creating a new manifest
    # This causes brief unavailability, but new manifest is created immediately
    podman manifest rm ${FINAL_TAG} 2>/dev/null || true
    podman rmi ${FINAL_TAG} 2>/dev/null || true
    # Create new manifest
    if ! podman manifest create ${FINAL_TAG} ${AMD64_TAG} ${ARM64_TAG}; then
        echo "❌ Failed to create manifest for ${FINAL_TAG}"
        exit 1
    fi
    
    if ! podman manifest push ${FINAL_TAG} docker://${FINAL_TAG}; then
        echo "❌ Failed to push multi-architecture manifest"
        exit 1
    fi
    
    echo "✅ Bootstrap image built and pushed successfully!"
    echo "   Tag: ${FINAL_TAG} (amd64 + arm64)"
fi

echo ""
echo "🎯 Bootstrap image features:"
echo "   • Contains venvoy CLI installed from git"
echo "   • Smart entrypoint that supports mounted source code"
echo "   • Uses ContainerManager instead of DockerManager"
echo "   • Works with Apptainer, Singularity, Docker, and Podman"
echo ""
echo "🚀 Users will get the updated bootstrap image when they run:"
echo "   • venvoy update"
echo "   • Fresh installs via install.sh"
echo ""
echo "💡 Update this image when:"
echo "   • venvoy code changes (installs from git)"
echo "   • Entrypoint script (docker/venvoy-entrypoint.sh) changes"
echo "   • System dependencies need updating"
echo "   • Python version needs updating"

