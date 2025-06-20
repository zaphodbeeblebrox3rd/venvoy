#!/bin/bash
# Build and push the venvoy bootstrap image

set -e

echo "🔨 Building venvoy bootstrap image..."

# Build the bootstrap image
docker build -f docker/Dockerfile.bootstrap -t zaphodbeeblebrox3rd/venvoy:bootstrap .

echo "✅ Bootstrap image built successfully"

# Push to Docker Hub
echo "📤 Pushing to Docker Hub..."
docker push zaphodbeeblebrox3rd/venvoy:bootstrap

echo "🎉 Bootstrap image pushed successfully!"
echo "   Image: zaphodbeeblebrox3rd/venvoy:bootstrap"
echo "   Users can now run: curl -fsSL https://raw.githubusercontent.com/zaphodbeeblebrox3rd/venvoy/main/install.sh | bash" 