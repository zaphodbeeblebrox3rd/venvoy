#!/bin/bash
# Build and push multi-architecture venvoy bootstrap images

set -e

# Supported Python versions
PYTHON_VERSIONS=("3.9" "3.10" "3.11" "3.12" "3.13")

# Supported platforms (architectures)
PLATFORMS="linux/amd64,linux/arm64,linux/arm/v7"

echo "🔨 Building multi-architecture venvoy bootstrap images..."

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

# Build and push multi-arch images for each Python version
for version in "${PYTHON_VERSIONS[@]}"; do
    echo "📦 Building Python ${version} bootstrap image for all architectures..."
    
    docker buildx build \
        --platform "$PLATFORMS" \
        --build-arg PYTHON_VERSION=${version} \
        -f docker/Dockerfile.bootstrap \
        -t zaphodbeeblebrox3rd/venvoy:bootstrap-python${version} \
        --push \
        .
    
    echo "✅ Python ${version} multi-arch bootstrap image built and pushed"
done

# Also build the default image (Python 3.11)
echo "📦 Building default bootstrap image (Python 3.11) for all architectures..."
docker buildx build \
    --platform "$PLATFORMS" \
    --build-arg PYTHON_VERSION=3.11 \
    -f docker/Dockerfile.bootstrap \
    -t zaphodbeeblebrox3rd/venvoy:bootstrap \
    --push \
    .

echo "🎉 All multi-architecture bootstrap images built and pushed successfully!"
echo ""
echo "📋 Available multi-arch images:"
for version in "${PYTHON_VERSIONS[@]}"; do
    echo "   • zaphodbeeblebrox3rd/venvoy:bootstrap-python${version}"
done
echo "   • zaphodbeeblebrox3rd/venvoy:bootstrap (default - Python 3.11)"
echo ""
echo "🏗️  Supported architectures:"
echo "   • linux/amd64 (Intel/AMD x86_64)"
echo "   • linux/arm64 (Apple Silicon, ARM64 servers)"
echo "   • linux/arm/v7 (ARM32 devices)"
echo ""
echo "🚀 Users can now run: curl -fsSL https://raw.githubusercontent.com/zaphodbeeblebrox3rd/venvoy/main/install.sh | bash"
echo "   Docker will automatically pull the correct architecture for their system!" 