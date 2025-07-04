#!/bin/bash
# venvoy Self-Bootstrapping Installer & Updater
# Works without requiring Python on the host system

set -e

echo "🚀 venvoy Self-Bootstrapping Installer & Updater"
echo "================================================"

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

# Check if venvoy is already installed
EXISTING_INSTALL=false
if [ -f "$INSTALL_DIR/venvoy" ]; then
    EXISTING_INSTALL=true
    echo "📦 Found existing venvoy installation"
    echo "🔄 Updating to latest version..."
fi

# Ensure pip is installed
if ! command -v pip3 &> /dev/null; then
    echo "❌ pip3 (Python package manager) is not installed."
    echo "   venvoy needs pip3 to install its dependencies."
    echo "   We will now attempt to install pip3 using sudo (you may be prompted for your password)."
    read -p "Proceed with installing pip3 using sudo? [Y/n]: " yn
    yn=${yn:-Y}
    if [[ $yn =~ ^[Yy]$ ]]; then
        # Check for and fix broken repositories before installing pip3
        echo "🔧 Checking for broken package repositories..."
        if sudo apt update 2>&1 | grep -q "404.*kubernetes"; then
            echo "⚠️  Detected broken Kubernetes repository. Attempting to fix..."
            sudo rm -f /etc/apt/sources.list.d/kubernetes.list*
            echo "✅ Removed broken Kubernetes repository"
        fi
        
        # Try to update package lists again
        echo "📦 Updating package lists..."
        sudo apt update || {
            echo "⚠️  Package update had issues, but continuing with pip3 installation..."
        }
        
        # Install pip3
        echo "📦 Installing pip3..."
        sudo apt install -y python3-pip
        
        if ! command -v pip3 &> /dev/null; then
            echo "❌ pip3 installation failed. Please install pip3 manually:"
            echo "   sudo apt update && sudo apt install python3-pip"
            exit 1
        fi
        echo "✅ pip3 installed successfully"
    else
        echo "❌ pip3 is required. Please install it manually:"
        echo "   sudo apt update && sudo apt install python3-pip"
        exit 1
    fi
fi

# Install pipx in a cross-platform way
if ! command -v pipx &> /dev/null; then
    echo "📦 pipx (Python application installer) is not installed."
    if [[ "$PLATFORM" == "linux" ]]; then
        echo "   Attempting to install pipx using apt (Linux)..."
        sudo apt install -y pipx || {
            echo "❌ Failed to install pipx with apt. Please install it manually:"
            echo "   sudo apt install pipx"
            exit 1
        }
    elif [[ "$PLATFORM" == "macos" ]]; then
        if command -v brew &> /dev/null; then
            echo "   Attempting to install pipx using Homebrew (macOS)..."
            brew install pipx || {
                echo "❌ Failed to install pipx with Homebrew. Trying pip..."
                python3 -m pip install --user pipx || {
                    echo "❌ Failed to install pipx with pip. Please install it manually:"
                    echo "   brew install pipx   # or: python3 -m pip install --user pipx"
                    exit 1
                }
            }
        else
            echo "   Homebrew not found. Trying pip..."
            python3 -m pip install --user pipx || {
                echo "❌ Failed to install pipx with pip. Please install it manually:"
                echo "   python3 -m pip install --user pipx"
                exit 1
            }
        fi
    elif [[ "$PLATFORM" == "windows" ]]; then
        echo "   Attempting to install pipx using pip (Windows)..."
        python -m pip install --user pipx || {
            echo "❌ Failed to install pipx with pip. Please install it manually:"
            echo "   python -m pip install --user pipx"
            exit 1
        }
        echo "   Please ensure %USERPROFILE%\.local\bin is in your PATH."
    else
        echo "❌ Unsupported platform for automatic pipx installation. Please install pipx manually."
        exit 1
    fi
fi

echo "📦 Installing venvoy using pipx..."
pipx install git+https://github.com/zaphodbeeblebrox3rd/venvoy.git || {
    echo "❌ Failed to install venvoy. Please check your Python and pipx installation."
    exit 1
}
echo "✅ venvoy installed successfully using pipx"

# Ensure pipx PATH is available immediately
if [[ ":$PATH:" != *":$HOME/.local/bin:"* ]]; then
    export PATH="$HOME/.local/bin:$PATH"
    echo "📝 Added pipx PATH to current session"
fi

# Ensure ~/.local/bin is in PATH for user installs
if [[ ":$PATH:" != *":$HOME/.local/bin:"* ]]; then
    echo "📝 Adding $HOME/.local/bin to PATH in ~/.bashrc"
    echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$HOME/.bashrc"
    export PATH="$HOME/.local/bin:$PATH"
    
    # Also add to current shell's RC file if different from ~/.bashrc
    if [[ -n "$ZSH_VERSION" ]] || [[ "$SHELL" == *"zsh"* ]]; then
        if [[ "$HOME/.zshrc" != "$HOME/.bashrc" ]]; then
            echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$HOME/.zshrc"
        fi
    fi
fi

# Download or create venvoy bootstrap script
cat > "$INSTALL_DIR/venvoy" << 'EOF'
#!/bin/bash
# venvoy Bootstrap Script - runs venvoy inside Docker

set -e

# Use single multi-architecture bootstrap image
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

# Pull venvoy image if it doesn't exist or force update
if ! docker image inspect "$VENVOY_IMAGE" &> /dev/null; then
    echo "📦 Downloading venvoy environment..."
    docker pull "$VENVOY_IMAGE"
    echo "✅ Environment ready"
elif [ "$1" = "update" ] || [ "$1" = "upgrade" ]; then
    echo "🔄 Updating venvoy environment..."
    docker pull "$VENVOY_IMAGE"
    echo "✅ Environment updated"
fi

# Check if we're in a venvoy development directory (has src/venvoy/)
USE_LOCAL_CODE=false
if [[ -d "$(pwd)/src/venvoy" ]] && [[ -f "$(pwd)/pyproject.toml" ]]; then
    USE_LOCAL_CODE=true
    echo "🔧 Using local venvoy development code"
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
            if docker image inspect zaphodbeeblebrox3rd/venvoy:bootstrap &> /dev/null; then
                docker rmi zaphodbeeblebrox3rd/venvoy:bootstrap &> /dev/null || true
                echo "✅ Removed bootstrap image"
            fi
        fi
    fi
    
    echo ""
    echo "✅ venvoy uninstalled successfully!"
    echo "💡 You may need to restart your terminal for PATH changes to take effect."
    exit 0
else
    # Run normal venvoy commands
    if command -v pipx &> /dev/null && pipx list | grep -q venvoy; then
        # Use pipx installation (preferred)
        pipx run --spec . venvoy "$@"
    elif [ "$USE_LOCAL_CODE" = true ]; then
        # Use local development code (dependencies already installed)
        cd "$(pwd)"
        python3 -c "import sys; sys.path.insert(0, 'src'); from venvoy.cli import main; main()" "$@"
    else
        # Use installed package
        python3 -m venvoy "$@"
    fi
fi
EOF

# Make script executable
chmod +x "$INSTALL_DIR/venvoy"

# Function to reload shell configuration
reload_shell_config() {
    local shell_rc="$1"
    if [[ -f "$shell_rc" ]]; then
        if [[ "$shell_rc" == *"fish"* ]]; then
            echo "📝 Fish shell detected - please restart your terminal or run: source $shell_rc"
        else
            # For bash/zsh, source the file
            source "$shell_rc" 2>/dev/null || {
                echo "⚠️  Could not automatically reload shell config"
                echo "   Please run: source $shell_rc"
            }
        fi
    fi
}

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
        
        # Automatically reload shell configuration to make venvoy available immediately
        echo "🔄 Reloading shell configuration..."
        reload_shell_config "$SHELL_RC"
        ;;
    windows)
        echo "📝 Please add $INSTALL_DIR to your PATH manually"
        echo "   Or restart your terminal to use the updated PATH"
        ;;
esac

# Force update the bootstrap image to ensure latest features
echo "🔄 Updating venvoy bootstrap image..."
if command -v docker &> /dev/null; then
    docker pull "zaphodbeeblebrox3rd/venvoy:bootstrap" 2>/dev/null || true
    echo "✅ Bootstrap image updated"
fi

echo ""
if [ "$EXISTING_INSTALL" = true ]; then
    echo "🎉 venvoy updated successfully!"
    echo "✨ All new features are now active"
else
    echo "🎉 venvoy installed successfully!"
fi

echo ""
echo "📋 Next steps:"

# Test if venvoy is immediately available
echo "🔍 Verifying venvoy installation..."
if command -v venvoy &> /dev/null; then
    echo "   ✅ venvoy is ready to use!"
    echo "   📍 Location: $(which venvoy)"
    if [ "$EXISTING_INSTALL" = true ]; then
        echo "   🆕 New features available:"
        echo "      • Enhanced WSL editor detection"
        echo "      • Working uninstall command"
        echo "      • Improved platform detection"
    fi
    echo "   1. (Optional) Run: venvoy setup (to configure AI editors)"
    echo "   2. Run: venvoy init --python-version <python-version> --name <environment-name>"
    echo "   3. Start coding with AI-powered environments!"
else
    echo "   ⚠️  venvoy not found in PATH"
    echo "   💡 This might happen if the shell configuration couldn't be reloaded automatically"
    echo "   🔧 Try running: source $SHELL_RC"
    echo "   🔄 Or restart your terminal"
    echo "   🐛 If the problem persists, run the diagnostic script:"
    echo "      curl -fsSL https://raw.githubusercontent.com/zaphodbeeblebrox3rd/venvoy/main/scripts/diagnose-macos-path.sh | bash"
    if [ "$EXISTING_INSTALL" = true ]; then
        echo "   🆕 New features available:"
        echo "      • Enhanced WSL editor detection"
        echo "      • Working uninstall command"
        echo "      • Improved platform detection"
    fi
    echo "   1. (Optional) Run: venvoy setup (to configure AI editors)"
    echo "   2. Run: venvoy init"
    echo "   3. Start coding with AI-powered environments!"
fi

echo ""
echo "💡 The first run will download the venvoy bootstrap image"
echo "   All subsequent operations will be containerized"
echo ""
echo "🔧 Installed to: $INSTALL_DIR/venvoy"
echo "📝 Shell config: $SHELL_RC"
echo ""
if [ "$EXISTING_INSTALL" = true ]; then
    echo "🚀 Test new features: venvoy --help"
else
    echo "🚀 Quick test: venvoy --help"
fi 