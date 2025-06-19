#!/bin/bash
# venvoy Self-Bootstrapping Installer
# Works without requiring Python on the host system

set -e

echo "🚀 venvoy Self-Bootstrapping Installer"
echo "======================================"

# Detect platform
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    PLATFORM="linux"
elif [[ "$OSTYPE" == "darwin"* ]]; then
    PLATFORM="macos"
elif [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "cygwin" ]]; then
    PLATFORM="windows"
else
    echo "❌ Unsupported platform: $OSTYPE"
    exit 1
fi

echo "🔍 Detected platform: $PLATFORM"

# Check for Docker
if ! command -v docker &> /dev/null; then
    echo "❌ Docker not found. Please install Docker first:"
    case $PLATFORM in
        linux)
            echo "   curl -fsSL https://get.docker.com | sh"
            ;;
        macos)
            echo "   brew install --cask docker"
            echo "   Or download from: https://www.docker.com/products/docker-desktop"
            ;;
        windows)
            echo "   Download from: https://www.docker.com/products/docker-desktop"
            ;;
    esac
    exit 1
fi

echo "✅ Docker found"

# Create installation directory
INSTALL_DIR="$HOME/.venvoy/bin"
mkdir -p "$INSTALL_DIR"

# Download or create venvoy bootstrap script
cat > "$INSTALL_DIR/venvoy" << 'EOF'
#!/bin/bash
# venvoy Bootstrap Script - runs venvoy inside Docker

set -e

VENVOY_IMAGE="venvoy/bootstrap:latest"
VENVOY_DIR="$HOME/.venvoy"

# Ensure venvoy directory exists
mkdir -p "$VENVOY_DIR"

# Build bootstrap image if it doesn't exist
if ! docker image inspect "$VENVOY_IMAGE" &> /dev/null; then
    echo "🔨 Building venvoy bootstrap image..."
    
    # Create temporary Dockerfile
    TEMP_DIR=$(mktemp -d)
    cat > "$TEMP_DIR/Dockerfile" << 'DOCKERFILE'
FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install venvoy from git
RUN pip install git+https://github.com/zaphodbeeblebrox3rd/venvoy.git

# Set up entrypoint
WORKDIR /workspace
ENTRYPOINT ["venvoy"]
DOCKERFILE

    # Build the image
    docker build -t "$VENVOY_IMAGE" "$TEMP_DIR"
    rm -rf "$TEMP_DIR"
    
    echo "✅ Bootstrap image built successfully"
fi

# Run venvoy inside Docker container
docker run --rm -it \
    -v /var/run/docker.sock:/var/run/docker.sock \
    -v "$HOME:$HOME" \
    -v "$(pwd):/workspace" \
    -w /workspace \
    -e HOME="$HOME" \
    "$VENVOY_IMAGE" "$@"
EOF

# Make script executable
chmod +x "$INSTALL_DIR/venvoy"

# Add to PATH
case $PLATFORM in
    linux|macos)
        SHELL_RC="$HOME/.bashrc"
        if [[ "$SHELL" == *"zsh"* ]]; then
            SHELL_RC="$HOME/.zshrc"
        fi
        
        if ! grep -q "$INSTALL_DIR" "$SHELL_RC" 2>/dev/null; then
            echo "export PATH=\"$INSTALL_DIR:\$PATH\"" >> "$SHELL_RC"
            echo "📝 Added venvoy to PATH in $SHELL_RC"
        fi
        ;;
    windows)
        echo "📝 Please add $INSTALL_DIR to your PATH manually"
        ;;
esac

echo ""
echo "🎉 venvoy installed successfully!"
echo ""
echo "📋 Next steps:"
echo "   1. Restart your terminal (or run: source $SHELL_RC)"
echo "   2. Run: venvoy init"
echo "   3. Start coding with AI-powered environments!"
echo ""
echo "💡 The first run will download the venvoy bootstrap image"
echo "   All subsequent operations will be containerized" 