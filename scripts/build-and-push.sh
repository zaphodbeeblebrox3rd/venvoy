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
BUILD_BOOTSTRAP=true

# Parse command-line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --python)
            BUILD_PYTHON=true
            BUILD_BOOTSTRAP=false
            shift
            ;;
        --r)
            # --r is now an alias for --python since images are combined
            BUILD_PYTHON=true
            BUILD_BOOTSTRAP=false
            shift
            ;;
        --bootstrap)
            BUILD_PYTHON=false
            BUILD_BOOTSTRAP=true
            shift
            ;;
        --all)
            BUILD_PYTHON=true
            BUILD_BOOTSTRAP=true
            shift
            ;;
        --help|-h)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Build and push venvoy container images"
            echo ""
            echo "Options:"
            echo "  --python     Build only combined Python+R images"
            echo "  --r          Alias for --python (images now include both Python and R)"
            echo "  --bootstrap  Build only bootstrap image"
            echo "  --all        Build all images (default)"
            echo "  --help, -h   Show this help message"
            echo ""
            echo "Examples:"
            echo "  $0                    # Build all images (default)"
            echo "  $0 --python           # Build only combined Python+R images"
            echo "  $0 --bootstrap        # Build only bootstrap image"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

REGISTRY="docker.io"
IMAGE_NAME="zaphodbeeblebrox3rd/venvoy"
# Combined images: Python/R version pairs
VERSION_PAIRS=("3.13:4.5" "3.12:4.4" "3.11:4.3" "3.11:4.2" "3.10:4.2")

# Detect container runtime (Docker or Podman)
# Check if docker is actually Docker (has buildx) or a Podman wrapper
CONTAINER_RUNTIME=""
if command -v docker &> /dev/null; then
    # Check if Docker is accessible
    if docker info &> /dev/null; then
        # Check if docker buildx actually works and is Docker (not Podman wrapper)
        # Podman's buildx wrapper returns "buildah" in version, Docker returns "github.com/docker/buildx"
        BUILDX_VERSION=$(docker buildx version 2>&1)
        if echo "$BUILDX_VERSION" | grep -q "github.com/docker/buildx\|buildx v"; then
            CONTAINER_RUNTIME="docker"
        elif command -v podman &> /dev/null; then
            # docker exists but buildx output suggests Podman wrapper
            CONTAINER_RUNTIME="podman"
            echo "⚠️  'docker' command found but appears to be Podman wrapper - using Podman instead"
        else
            CONTAINER_RUNTIME="docker"
        fi
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
    echo "   ✓ Combined Python+R images (5 pairs)"
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
    # Check if logged into Docker Hub
    if ! podman login --get-login docker.io &>/dev/null; then
        echo "⚠️  Not logged into Docker Hub with Podman"
        echo "📝 If build fails, please run: podman login docker.io"
        echo "   (Podman can use Docker's credentials if Docker is logged in)"
        echo ""
    else
        echo "✅ Logged into Docker Hub"
    fi
    # Podman doesn't require buildx, uses podman build directly
fi

# Function to build combined Python+R images
build_python_images() {
    echo ""
    echo "🐍📊 Building combined Python+R images..."
    echo "=========================================="
    
    # Call the dedicated build script (builds combined Python+R images)
    "$SCRIPT_DIR/build-python-r.sh"
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

# Automatic cleanup of old tags after successful builds
if [ "$BUILD_PYTHON" = true ]; then
    echo ""
    echo "🧹 Cleaning up old separate Python/R tags..."
    echo "============================================="
    
    # Check if cleanup script exists and is executable
    CLEANUP_SCRIPT="$SCRIPT_DIR/cleanup-docker-tags.sh"
    if [ -f "$CLEANUP_SCRIPT" ] && [ -x "$CLEANUP_SCRIPT" ]; then
        # Check if docker.env exists (required for cleanup)
        if [ -f "$PROJECT_ROOT/docker.env" ]; then
            echo "📋 Running cleanup in dry-run mode first to preview deletions..."
            if "$CLEANUP_SCRIPT" --dry-run > /tmp/venvoy-cleanup-preview.txt 2>&1; then
                # Check if there are tags to delete
                if grep -q "Tags to delete:" /tmp/venvoy-cleanup-preview.txt; then
                    DELETE_COUNT=$(grep "Tags to delete:" /tmp/venvoy-cleanup-preview.txt | grep -oE '[0-9]+' | head -1)
                    if [ -n "$DELETE_COUNT" ] && [ "$DELETE_COUNT" -gt 0 ]; then
                        echo "   Found $DELETE_COUNT old tag(s) that can be deleted"
                        echo ""
                        echo "⚠️  To delete old tags, run manually:"
                        echo "   $CLEANUP_SCRIPT --execute"
                        echo ""
                        echo "   Or review the preview:"
                        echo "   cat /tmp/venvoy-cleanup-preview.txt"
                    else
                        echo "   ✅ No old tags to clean up"
                    fi
                else
                    echo "   ✅ No old tags to clean up"
                fi
                rm -f /tmp/venvoy-cleanup-preview.txt
            else
                echo "   ⚠️  Cleanup script failed (this is non-fatal)"
                echo "   You can run cleanup manually: $CLEANUP_SCRIPT --dry-run"
            fi
        else
            echo "   ⚠️  docker.env not found - skipping automatic cleanup"
            echo "   To enable cleanup, create docker.env with DOCKER_USERNAME and DOCKER_TOKEN"
            echo "   Then run manually: $CLEANUP_SCRIPT --execute"
        fi
    else
        echo "   ⚠️  Cleanup script not found or not executable"
    fi
fi

# Summary
echo ""
echo "🎉 All requested images published successfully!"
echo ""
echo "📦 Available images:"
if [ "$BUILD_PYTHON" = true ]; then
    for PAIR in "${VERSION_PAIRS[@]}"; do
        IFS=':' read -r PYTHON_VERSION R_VERSION <<< "$PAIR"
        if [ -z "$PYTHON_VERSION" ] || [ -z "$R_VERSION" ]; then
            echo "⚠️  Skipping invalid version pair: $PAIR"
            continue
        fi
        echo "   $CONTAINER_RUNTIME pull $REGISTRY/$IMAGE_NAME:python${PYTHON_VERSION}-r${R_VERSION}"
    done
    echo "   $CONTAINER_RUNTIME pull $REGISTRY/$IMAGE_NAME:latest"
fi
if [ "$BUILD_BOOTSTRAP" = true ]; then
    echo "   $CONTAINER_RUNTIME pull $REGISTRY/$IMAGE_NAME:bootstrap"
fi
echo ""
echo "🔗 Docker Hub: https://hub.docker.com/r/$IMAGE_NAME"
echo ""
