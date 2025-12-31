#!/bin/bash

# Build multi-architecture combined Python+R environment images for venvoy
set -e

# Ensure we're in the project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT"

echo "🔨 Building multi-architecture venvoy combined Python+R images..."

# Define version pairs: (PYTHON_VERSION, R_VERSION)
declare -a VERSION_PAIRS=(
    "3.13:4.5"
    "3.12:4.4"
    "3.11:4.3"
    "3.11:4.2"
    "3.10:4.2"
)

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

# Build combined images for each version pair
for PAIR in "${VERSION_PAIRS[@]}"; do
    IFS=':' read -r PYTHON_VERSION R_VERSION <<< "$PAIR"
    # Validate that both versions were extracted
    if [ -z "$PYTHON_VERSION" ] || [ -z "$R_VERSION" ]; then
        echo "❌ Failed to parse version pair: $PAIR"
        exit 1
    fi
    IMAGE_TAG="python${PYTHON_VERSION}-r${R_VERSION}"
    
    echo ""
    echo "🐍📊 Building Python ${PYTHON_VERSION} / R ${R_VERSION} combined image for all architectures..."
    
    if [ "$CONTAINER_RUNTIME" = "docker" ]; then
        # Build multi-architecture image
        docker buildx build \
            --platform linux/amd64,linux/arm64 \
            --build-arg PYTHON_VERSION=${PYTHON_VERSION} \
            --build-arg R_VERSION=${R_VERSION} \
            -f docker/Dockerfile.combined \
            -t ${REGISTRY}/${IMAGE_NAME}:${IMAGE_TAG} \
            --push \
            .
        
        # Verify the image was actually built and pushed
        if docker buildx imagetools inspect ${REGISTRY}/${IMAGE_NAME}:${IMAGE_TAG} > /dev/null 2>&1; then
            echo "✅ Python ${PYTHON_VERSION} / R ${R_VERSION} image built and pushed"
            echo "   Verified: ${REGISTRY}/${IMAGE_NAME}:${IMAGE_TAG}"
        else
            echo "⚠️  Warning: Image ${REGISTRY}/${IMAGE_NAME}:${IMAGE_TAG} may not be accessible yet"
            echo "   (This can happen immediately after push - image may need a moment to propagate)"
        fi
    elif [ "$CONTAINER_RUNTIME" = "podman" ]; then
        echo "⚠️  Podman multi-arch builds require manual manifest creation"
        echo "   Building for current architecture only..."
        if podman build \
            --build-arg PYTHON_VERSION=${PYTHON_VERSION} \
            --build-arg R_VERSION=${R_VERSION} \
            -f docker/Dockerfile.combined \
            -t ${REGISTRY}/${IMAGE_NAME}:${IMAGE_TAG} \
            .; then
            echo "📤 Pushing ${REGISTRY}/${IMAGE_NAME}:${IMAGE_TAG}..."
            if podman push ${REGISTRY}/${IMAGE_NAME}:${IMAGE_TAG}; then
                echo "✅ Python ${PYTHON_VERSION} / R ${R_VERSION} image built and pushed"
                echo "   Tag: ${REGISTRY}/${IMAGE_NAME}:${IMAGE_TAG}"
            else
                echo "❌ Failed to push Python ${PYTHON_VERSION} / R ${R_VERSION}"
                exit 1
            fi
        else
            echo "❌ Failed to build Python ${PYTHON_VERSION} / R ${R_VERSION}"
            exit 1
        fi
    fi
done

# Create latest tag (Python 3.11 / R 4.3)
echo ""
echo "🏷️  Creating latest tag (Python 3.11 / R 4.3)..."
if [ "$CONTAINER_RUNTIME" = "docker" ]; then
    docker buildx build \
        --platform linux/amd64,linux/arm64 \
        --build-arg PYTHON_VERSION=3.11 \
        --build-arg R_VERSION=4.3 \
        -f docker/Dockerfile.combined \
        -t ${REGISTRY}/${IMAGE_NAME}:latest \
        --push \
        .
    # Verify the latest tag
    if docker buildx imagetools inspect ${REGISTRY}/${IMAGE_NAME}:latest > /dev/null 2>&1; then
        echo "✅ Published: ${REGISTRY}/${IMAGE_NAME}:latest"
        echo "   Verified: ${REGISTRY}/${IMAGE_NAME}:latest (Python 3.11 / R 4.3)"
    else
        echo "⚠️  Warning: latest tag may not be accessible yet"
    fi
elif [ "$CONTAINER_RUNTIME" = "podman" ]; then
    if podman build \
        --build-arg PYTHON_VERSION=3.11 \
        --build-arg R_VERSION=4.3 \
        -f docker/Dockerfile.combined \
        -t ${REGISTRY}/${IMAGE_NAME}:latest \
        .; then
        echo "📤 Pushing ${REGISTRY}/${IMAGE_NAME}:latest..."
        if podman push ${REGISTRY}/${IMAGE_NAME}:latest; then
            echo "✅ Published: ${REGISTRY}/${IMAGE_NAME}:latest"
            echo "   Tag: ${REGISTRY}/${IMAGE_NAME}:latest (Python 3.11 / R 4.3)"
        else
            echo "❌ Failed to push latest tag"
            exit 1
        fi
    else
        echo "❌ Failed to build latest tag"
        exit 1
    fi
fi

echo ""
echo "🎉 All combined Python+R environment images built successfully!"
echo ""
echo "🐍📊 Available combined images:"
for PAIR in "${VERSION_PAIRS[@]}"; do
    IFS=':' read -r PYTHON_VERSION R_VERSION <<< "$PAIR"
    if [ -z "$PYTHON_VERSION" ] || [ -z "$R_VERSION" ]; then
        continue
    fi
    echo "   - ${REGISTRY}/${IMAGE_NAME}:python${PYTHON_VERSION}-r${R_VERSION}"
done
echo "   - ${REGISTRY}/${IMAGE_NAME}:latest"
echo ""
echo "🚀 Usage:"
echo "   venvoy init --python-version 3.11 --r-version 4.3 --name my-project"
echo "   venvoy run --name my-project"

