#!/bin/bash
# Build and push venvoy container images
# This is the main orchestrator script that builds all images by default
# Supports both Docker and Podman
#
# Usage:
#   ./scripts/build-and-push.sh              # Build all images (default)
#   ./scripts/build-and-push.sh --python     # Build only Python images
#   ./scripts/build-and-push.sh --r          # Build only R images
#   ./scripts/build-and-push.sh --bootstrap  # Build only bootstrap image
#   ./scripts/build-and-push.sh --python --r # Build Python and R (no bootstrap)

set -e

# Ensure we're in the project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT"

echo "📁 Working directory: $(pwd)"

# Default: build everything
BUILD_PYTHON=true
BUILD_R=true
BUILD_BOOTSTRAP=true

# Parse command-line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --python)
            BUILD_PYTHON=true
            BUILD_R=false
            BUILD_BOOTSTRAP=false
            shift
            ;;
        --r)
            BUILD_PYTHON=false
            BUILD_R=true
            BUILD_BOOTSTRAP=false
            shift
            ;;
        --bootstrap)
            BUILD_PYTHON=false
            BUILD_R=false
            BUILD_BOOTSTRAP=true
            shift
            ;;
        --all)
            BUILD_PYTHON=true
            BUILD_R=true
            BUILD_BOOTSTRAP=true
            shift
            ;;
        --help|-h)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Build and push venvoy container images"
            echo ""
            echo "Options:"
            echo "  --python     Build only Python images"
            echo "  --r          Build only R images"
            echo "  --bootstrap  Build only bootstrap image"
            echo "  --all        Build all images (default)"
            echo "  --help, -h   Show this help message"
            echo ""
            echo "Examples:"
            echo "  $0                    # Build all images (default)"
            echo "  $0 --python           # Build only Python images"
            echo "  $0 --r                # Build only R images"
            echo "  $0 --python --r       # Build Python and R (no bootstrap)"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# If multiple specific options are provided, combine them
if [[ "$*" == *"--python"* ]] && [[ "$*" == *"--r"* ]]; then
    BUILD_PYTHON=true
    BUILD_R=true
    BUILD_BOOTSTRAP=false
elif [[ "$*" == *"--python"* ]] && [[ "$*" == *"--bootstrap"* ]]; then
    BUILD_PYTHON=true
    BUILD_R=false
    BUILD_BOOTSTRAP=true
elif [[ "$*" == *"--r"* ]] && [[ "$*" == *"--bootstrap"* ]]; then
    BUILD_PYTHON=false
    BUILD_R=true
    BUILD_BOOTSTRAP=true
fi

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
echo ""
echo "📋 Build plan:"
if [ "$BUILD_PYTHON" = true ]; then
    echo "   ✓ Python images (${PYTHON_VERSIONS[*]})"
fi
if [ "$BUILD_R" = true ]; then
    echo "   ✓ R images (4.2, 4.3, 4.4, 4.5)"
fi
if [ "$BUILD_BOOTSTRAP" = true ]; then
    echo "   ✓ Bootstrap image"
fi
echo ""

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

# Function to build Python images
build_python_images() {
    echo ""
    echo "🐍 Building Python images..."
    echo "============================"
    
    # Call the dedicated Python build script
    "$SCRIPT_DIR/build-python.sh"
}

# Function to build R images
build_r_images() {
    echo ""
    echo "📊 Building R images..."
    echo "======================"
    
    # Call the dedicated R build script
    "$SCRIPT_DIR/build-r.sh"
}

# Function to build bootstrap image
build_bootstrap_image() {
    echo ""
    echo "📦 Building bootstrap image..."
    echo "============================="
    
    # Call the dedicated bootstrap build script
    "$SCRIPT_DIR/build-bootstrap.sh"
}

# Execute builds based on flags
BUILD_FAILED=false

if [ "$BUILD_PYTHON" = true ]; then
    if ! build_python_images; then
        BUILD_FAILED=true
    fi
fi

if [ "$BUILD_R" = true ]; then
    if ! build_r_images; then
        BUILD_FAILED=true
    fi
fi

if [ "$BUILD_BOOTSTRAP" = true ]; then
    if ! build_bootstrap_image; then
        BUILD_FAILED=true
    fi
fi

if [ "$BUILD_FAILED" = true ]; then
    echo ""
    echo "❌ Some builds failed. Please check the output above."
    exit 1
fi

# Summary
echo ""
echo "🎉 All requested images published successfully!"
echo ""
echo "📦 Available images:"
if [ "$BUILD_PYTHON" = true ]; then
    for version in "${PYTHON_VERSIONS[@]}"; do
        echo "   $CONTAINER_RUNTIME pull $REGISTRY/$IMAGE_NAME:python$version"
    done
    echo "   $CONTAINER_RUNTIME pull $REGISTRY/$IMAGE_NAME:latest"
fi
if [ "$BUILD_R" = true ]; then
    for R_VERSION in "4.2" "4.3" "4.4" "4.5"; do
        echo "   $CONTAINER_RUNTIME pull $REGISTRY/$IMAGE_NAME:r${R_VERSION}"
    done
fi
if [ "$BUILD_BOOTSTRAP" = true ]; then
    echo "   $CONTAINER_RUNTIME pull $REGISTRY/$IMAGE_NAME:bootstrap"
fi
echo ""
echo "🔗 Docker Hub: https://hub.docker.com/r/$IMAGE_NAME"
echo ""
