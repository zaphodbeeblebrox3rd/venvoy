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

VENVOY_IMAGE="zaphodbeeblebrox3rd/venvoy:bootstrap"
VENVOY_DIR="$HOME/.venvoy"

# Ensure venvoy directory exists
mkdir -p "$VENVOY_DIR"

# Clear Python bytecode cache to ensure latest code is used
if [[ -d "/workspace" ]]; then
    echo "🧹 Clearing Python bytecode cache..."
    find /workspace -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
    find /workspace -name "*.pyc" -delete 2>/dev/null || true
fi

# Pull venvoy image if it doesn't exist
if ! docker image inspect "$VENVOY_IMAGE" &> /dev/null; then
    echo "📦 Downloading venvoy environment..."
    docker pull "$VENVOY_IMAGE"
    echo "✅ Environment ready"
fi

# Handle uninstall command specially
if [ "$1" = "uninstall" ]; then
    # Run uninstall directly on host, not in container
    echo "🗑️  venvoy Uninstaller"
    echo "===================="
    
    # Parse arguments
    FORCE=false
    KEEP_PROJECTS=false
    KEEP_IMAGES=false
    
    shift  # Remove 'uninstall' from arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --force)
                FORCE=true
                shift
                ;;
            --keep-projects)
                KEEP_PROJECTS=true
                shift
                ;;
            --keep-images)
                KEEP_IMAGES=true
                shift
                ;;
            *)
                echo "Unknown option: $1"
                exit 1
                ;;
        esac
    done
    
    # Show what will be removed
    echo ""
    echo "This will remove:"
    echo "  📁 Installation directory: $INSTALL_DIR"
    echo "  📁 Configuration directory: $HOME/.venvoy"
    if [ "$KEEP_PROJECTS" = false ]; then
        echo "  📁 Projects directory: $HOME/venvoy-projects"
    fi
    echo "  🔗 PATH entries from shell configuration files"
    if [ "$KEEP_IMAGES" = false ]; then
        echo "  🐳 Docker images (venvoy/bootstrap:latest and zaphodbeeblebrox3rd/venvoy:bootstrap)"
    fi
    echo ""
    
    if [ "$FORCE" = false ]; then
        read -p "Are you sure you want to uninstall venvoy? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            echo "❌ Uninstallation cancelled"
            exit 0
        fi
    fi
    
    echo ""
    echo "🗑️  Removing venvoy..."
    
    # Remove installation directory
    if [ -d "$INSTALL_DIR" ]; then
        rm -rf "$INSTALL_DIR"
        echo "✅ Removed installation directory"
    fi
    
    # Remove configuration directory
    if [ -d "$HOME/.venvoy" ]; then
        rm -rf "$HOME/.venvoy"
        echo "✅ Removed configuration directory"
    fi
    
    # Handle projects directory
    if [ -d "$HOME/venvoy-projects" ]; then
        if [ "$KEEP_PROJECTS" = true ]; then
            echo "📁 Kept projects directory: $HOME/venvoy-projects"
        else
            if [ "$FORCE" = false ]; then
                read -p "Remove projects directory with environment exports? (y/N): " -n 1 -r
                echo
                if [[ $REPLY =~ ^[Yy]$ ]]; then
                    rm -rf "$HOME/venvoy-projects"
                    echo "✅ Removed projects directory"
                else
                    echo "📁 Kept projects directory: $HOME/venvoy-projects"
                fi
            else
                rm -rf "$HOME/venvoy-projects"
                echo "✅ Removed projects directory"
            fi
        fi
    fi
    
    # Remove PATH entries from shell configuration files
    if [[ "$OSTYPE" == "linux-gnu"* ]] || [[ "$OSTYPE" == "darwin"* ]]; then
        # Linux and macOS
        SHELL_FILES=(
            "$HOME/.bashrc"
            "$HOME/.zshrc"
            "$HOME/.config/fish/config.fish"
            "$HOME/.profile"
            "$HOME/.bash_profile"
        )
        
        for shell_file in "${SHELL_FILES[@]}"; do
            if [ -f "$shell_file" ]; then
                if grep -q "$INSTALL_DIR" "$shell_file" 2>/dev/null; then
                    # Create backup
                    cp "$shell_file" "$shell_file.venvoy-backup"
                    
                    # Remove venvoy-related lines
                    sed -i.bak '/# Added by venvoy installer/,+2d' "$shell_file"
                    sed -i.bak "s|$INSTALL_DIR:||g" "$shell_file"
                    sed -i.bak "s|:$INSTALL_DIR||g" "$shell_file"
                    
                    echo "✅ Cleaned PATH from $(basename "$shell_file")"
                    echo "   📋 Backup saved as: $(basename "$shell_file").venvoy-backup"
                fi
            fi
        done
        
        # Remove system-wide symlink if it exists
        if [ -L "/usr/local/bin/venvoy" ]; then
            rm -f "/usr/local/bin/venvoy"
            echo "✅ Removed system-wide symlink"
        fi
        
    elif [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "cygwin" ]]; then
        # Windows (Git Bash, Cygwin)
        echo "⚠️  Please manually remove $INSTALL_DIR from your Windows PATH"
        echo "   Control Panel > System > Advanced System Settings > Environment Variables"
    fi
    
    # Remove Docker images
    if [ "$KEEP_IMAGES" = false ]; then
        echo ""
        echo "🐳 Cleaning up Docker images..."
        
        if command -v docker &> /dev/null; then
            # Remove bootstrap image
            if docker image inspect venvoy/bootstrap:latest &> /dev/null; then
                docker rmi venvoy/bootstrap:latest &> /dev/null || true
                echo "✅ Removed bootstrap image"
            fi
            
            # Remove venvoy bootstrap image
            if docker image inspect zaphodbeeblebrox3rd/venvoy:bootstrap &> /dev/null; then
                docker rmi zaphodbeeblebrox3rd/venvoy:bootstrap &> /dev/null || true
                echo "✅ Removed venvoy bootstrap image"
            fi
        fi
    fi
    
    echo ""
    echo "✅ venvoy uninstalled successfully!"
    echo "💡 You may need to restart your terminal for PATH changes to take effect."
    exit 0
else
    # Run normal venvoy commands
    docker run --rm -it \
        -v /var/run/docker.sock:/var/run/docker.sock \
        -v "$HOME:$HOME" \
        -v "$(pwd):/workspace" \
        -w /workspace \
        -e HOME="$HOME" \
        "$VENVOY_IMAGE" "$@"
fi
EOF

# Make script executable
chmod +x "$INSTALL_DIR/venvoy"

# Add to PATH with better shell detection
case $PLATFORM in
    linux|macos)
        # Detect shell and appropriate RC file
        SHELL_RC=""
        if [[ -n "$ZSH_VERSION" ]] || [[ "$SHELL" == *"zsh"* ]]; then
            SHELL_RC="$HOME/.zshrc"
        elif [[ -n "$BASH_VERSION" ]] || [[ "$SHELL" == *"bash"* ]]; then
            SHELL_RC="$HOME/.bashrc"
        elif [[ "$SHELL" == *"fish"* ]]; then
            SHELL_RC="$HOME/.config/fish/config.fish"
            mkdir -p "$HOME/.config/fish"
        else
            # Default to .bashrc for unknown shells
            SHELL_RC="$HOME/.bashrc"
        fi
        
        # Create shell RC file if it doesn't exist
        touch "$SHELL_RC"
        
        # Check if PATH is already set
        PATH_ALREADY_SET=false
        if [[ -f "$SHELL_RC" ]] && grep -q "$INSTALL_DIR" "$SHELL_RC" 2>/dev/null; then
            PATH_ALREADY_SET=true
        fi
        
        if [[ "$PATH_ALREADY_SET" == false ]]; then
            echo "" >> "$SHELL_RC"
            echo "# Added by venvoy installer" >> "$SHELL_RC"
            
            if [[ "$SHELL_RC" == *"fish"* ]]; then
                echo "set -gx PATH \"$INSTALL_DIR\" \$PATH" >> "$SHELL_RC"
            else
                echo "export PATH=\"$INSTALL_DIR:\$PATH\"" >> "$SHELL_RC"
            fi
            
            echo "📝 Added venvoy to PATH in $SHELL_RC"
        else
            echo "📝 venvoy already in PATH"
        fi
        
        # Also try to add to current session PATH
        export PATH="$INSTALL_DIR:$PATH"
        
        # Create symlink in /usr/local/bin if writable (for system-wide access)
        if [[ -w "/usr/local/bin" ]]; then
            ln -sf "$INSTALL_DIR/venvoy" "/usr/local/bin/venvoy" 2>/dev/null || true
            echo "📝 Created system-wide symlink in /usr/local/bin"
        fi
        ;;
    windows)
        echo "📝 Please add $INSTALL_DIR to your PATH manually"
        echo "   Or restart your terminal to use the updated PATH"
        ;;
esac

echo ""
echo "🎉 venvoy installed successfully!"
echo ""
echo "📋 Next steps:"

# Test if venvoy is immediately available
if command -v venvoy &> /dev/null; then
    echo "   ✅ venvoy is ready to use!"
    echo "   1. (Optional) Run: venvoy setup (to configure AI editors)"
    echo "   2. Run: venvoy init --python-version <python-version> --name <environment-name>"
    echo "   3. Start coding with AI-powered environments!"
else
    echo "   1. Restart your terminal (or run: source $SHELL_RC)"
    echo "   2. (Optional) Run: venvoy setup (to configure AI editors)"
    echo "   3. Run: venvoy init"
    echo "   4. Start coding with AI-powered environments!"
fi

echo ""
echo "💡 The first run will download the venvoy bootstrap image"
echo "   All subsequent operations will be containerized"
echo ""
echo "🔧 Installed to: $INSTALL_DIR/venvoy"
echo "📝 Shell config: $SHELL_RC"
echo ""
echo "🚀 Quick test: venvoy --help" 