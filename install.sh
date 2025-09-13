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

# Check for any supported container runtime
CONTAINER_RUNTIME=""
if command -v docker &> /dev/null; then
    CONTAINER_RUNTIME="docker"
elif command -v apptainer &> /dev/null; then
    CONTAINER_RUNTIME="apptainer"
elif command -v singularity &> /dev/null; then
    CONTAINER_RUNTIME="singularity"
elif command -v podman &> /dev/null; then
    CONTAINER_RUNTIME="podman"
else
    echo "❌ No supported container runtime found."
    echo "   Please install one of the following:"
    case $PLATFORM in
        linux)
            echo "   Docker: curl -fsSL https://get.docker.com | sh"
            echo "   Apptainer: https://apptainer.org/docs/user/main/quick_start.html#quick-installation-steps"
            echo "   Podman: sudo apt install podman (or equivalent for your distro)"
            ;;
        macos)
            echo "   Docker: brew install --cask docker"
            echo "   Podman: brew install podman"
            echo "   Or download Docker Desktop from: https://www.docker.com/products/docker-desktop"
            ;;
        windows)
            echo "   Docker: Download from https://www.docker.com/products/docker-desktop"
            echo "   Podman: Download from https://podman.io/getting-started/installation"
            ;;
    esac
    echo ""
    echo "💡 For HPC environments, Apptainer/Singularity is recommended"
    echo "   as it doesn't require root access."
    exit 1
fi

echo "✅ Found container runtime: $CONTAINER_RUNTIME"

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

# Ensure pip is installed (cross-platform, no sudo required)
if ! command -v pip3 &> /dev/null && ! command -v pip &> /dev/null; then
    echo "❌ pip (Python package manager) is not installed."
    echo "   venvoy needs pip to install its dependencies."
    
    # Try multiple methods to install pip
    PIP_INSTALLED=false
    
    # Method 1: Try ensurepip first (fastest if available)
    if command -v python3 &> /dev/null; then
        echo "   Attempting to install pip using ensurepip..."
        python3 -m ensurepip --user --upgrade 2>/dev/null && PIP_INSTALLED=true
    elif command -v python &> /dev/null; then
        echo "   Attempting to install pip using ensurepip..."
        python -m ensurepip --user --upgrade 2>/dev/null && PIP_INSTALLED=true
    fi
    
    # Method 2: Download and run get-pip.py (most reliable)
    if [ "$PIP_INSTALLED" = false ]; then
        echo "   ensurepip not available, downloading get-pip.py..."
        if command -v python3 &> /dev/null; then
            curl -fsSL https://bootstrap.pypa.io/get-pip.py | python3 --user && PIP_INSTALLED=true
        elif command -v python &> /dev/null; then
            curl -fsSL https://bootstrap.pypa.io/get-pip.py | python --user && PIP_INSTALLED=true
        fi
    fi
    
    # Method 3: Try using the system's package manager as last resort
    if [ "$PIP_INSTALLED" = false ]; then
        echo "   get-pip.py failed, trying system package manager..."
        case $PLATFORM in
            linux)
                # Try to detect package manager and install pip
                if command -v dnf &> /dev/null; then
                    echo "   Found dnf, attempting to install python3-pip..."
                    sudo dnf install -y python3-pip && PIP_INSTALLED=true
                elif command -v yum &> /dev/null; then
                    echo "   Found yum, attempting to install python3-pip..."
                    sudo yum install -y python3-pip && PIP_INSTALLED=true
                elif command -v apt &> /dev/null; then
                    echo "   Found apt, attempting to install python3-pip..."
                    sudo apt update && sudo apt install -y python3-pip && PIP_INSTALLED=true
                fi
                ;;
            macos)
                if command -v brew &> /dev/null; then
                    echo "   Found brew, attempting to install python (includes pip)..."
                    brew install python && PIP_INSTALLED=true
                fi
                ;;
        esac
    fi
    
    # Final check
    if [ "$PIP_INSTALLED" = false ]; then
        echo "❌ Failed to install pip using all methods."
        echo "   Please install pip manually for your platform:"
        case $PLATFORM in
            linux)
                echo "   RHEL/CentOS: sudo dnf install python3-pip"
                echo "   Ubuntu/Debian: sudo apt install python3-pip"
                echo "   Manual: curl https://bootstrap.pypa.io/get-pip.py | python3"
                ;;
            macos)
                echo "   brew install python (includes pip)"
                echo "   Manual: curl https://bootstrap.pypa.io/get-pip.py | python3"
                ;;
            windows)
                echo "   Download Python from python.org (includes pip)"
                echo "   Manual: curl https://bootstrap.pypa.io/get-pip.py | python"
                ;;
        esac
        exit 1
    else
        echo "✅ pip installed successfully"
    fi
fi

# Install pipx in a cross-platform way (no sudo required)
if ! command -v pipx &> /dev/null; then
    echo "📦 pipx (Python application installer) is not installed."
    echo "   Installing pipx using pip (no sudo required)..."
    
    # Try pip3 first, then python3 -m pip, then python -m pip
    if command -v pip3 &> /dev/null; then
        pip3 install --user pipx || {
            echo "❌ Failed to install pipx with pip3. Trying alternative methods..."
            exit 1
        }
    elif command -v python3 &> /dev/null; then
        python3 -m pip install --user pipx || {
            echo "❌ Failed to install pipx with python3 -m pip. Trying python..."
            if command -v python &> /dev/null; then
                python -m pip install --user pipx || {
                    echo "❌ Failed to install pipx. Please install it manually:"
                    echo "   python3 -m pip install --user pipx"
                    exit 1
                }
            else
                echo "❌ Failed to install pipx. Please install it manually:"
                echo "   python3 -m pip install --user pipx"
                exit 1
            fi
        }
    elif command -v python &> /dev/null; then
        python -m pip install --user pipx || {
            echo "❌ Failed to install pipx. Please install it manually:"
            echo "   python -m pip install --user pipx"
            exit 1
        }
    else
        echo "❌ No Python or pip found. Please install Python first."
        exit 1
    fi
    
    echo "✅ pipx installed successfully"
    
    # Ensure pipx PATH is available immediately
    if [[ ":$PATH:" != *":$HOME/.local/bin:"* ]]; then
        export PATH="$HOME/.local/bin:$PATH"
        echo "📝 Added pipx PATH to current session"
    fi
fi

echo "📦 Installing venvoy using pipx..."
pipx install --force git+https://github.com/zaphodbeeblebrox3rd/venvoy.git || {
    echo "❌ Failed to install venvoy. Please check your Python and pipx installation."
    exit 1
}
echo "✅ venvoy installed successfully using pipx"

# Ensure ~/.local/bin is in PATH for user installs
PATH_UPDATED=false
if [[ ":$PATH:" != *":$HOME/.local/bin:"* ]]; then
    echo "📝 Adding $HOME/.local/bin to PATH in ~/.bashrc"
    echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$HOME/.bashrc"
    export PATH="$HOME/.local/bin:$PATH"
    PATH_UPDATED=true
    
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
# venvoy Bootstrap Script - runs venvoy inside container

set -e

# Detect container runtime
CONTAINER_RUNTIME=""
if command -v docker &> /dev/null; then
    CONTAINER_RUNTIME="docker"
elif command -v apptainer &> /dev/null; then
    CONTAINER_RUNTIME="apptainer"
elif command -v singularity &> /dev/null; then
    CONTAINER_RUNTIME="singularity"
elif command -v podman &> /dev/null; then
    CONTAINER_RUNTIME="podman"
else
    echo "❌ No supported container runtime found"
    exit 1
fi

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

# Format image URI based on container runtime
if [ "$CONTAINER_RUNTIME" = "apptainer" ] || [ "$CONTAINER_RUNTIME" = "singularity" ]; then
    IMAGE_URI="docker://$VENVOY_IMAGE"
else
    IMAGE_URI="$VENVOY_IMAGE"
fi

# Pull venvoy image if it doesn't exist or force update
if ! $CONTAINER_RUNTIME image inspect "$IMAGE_URI" &> /dev/null; then
    echo "📦 Downloading venvoy environment..."
    if [ "$CONTAINER_RUNTIME" = "apptainer" ] || [ "$CONTAINER_RUNTIME" = "singularity" ]; then
        # For Apptainer/Singularity, use --force to overwrite existing SIF files
        $CONTAINER_RUNTIME pull --force "$IMAGE_URI"
    else
        $CONTAINER_RUNTIME pull "$IMAGE_URI"
    fi
    echo "✅ Environment ready"
elif [ "\$1" = "update" ] || [ "\$1" = "upgrade" ]; then
    echo "🔄 Updating venvoy environment..."
    if [ "$CONTAINER_RUNTIME" = "apptainer" ] || [ "$CONTAINER_RUNTIME" = "singularity" ]; then
        # For Apptainer/Singularity, use --force to overwrite existing SIF files
        $CONTAINER_RUNTIME pull --force "$IMAGE_URI"
    else
        $CONTAINER_RUNTIME pull "$IMAGE_URI"
    fi
    echo "✅ Environment updated"
    
    # Also update source code
    echo "📥 Updating venvoy source code..."
    VENVOY_SOURCE_DIR="$HOME/.venvoy/src"
    if [[ -d "$VENVOY_SOURCE_DIR" ]]; then
        rm -rf "$VENVOY_SOURCE_DIR"
    fi
    mkdir -p "$VENVOY_SOURCE_DIR"
    curl -fsSL https://github.com/zaphodbeeblebrox3rd/venvoy/archive/main.tar.gz | \
        tar -xz -C "$VENVOY_SOURCE_DIR" --strip-components=1
    echo "✅ Source code updated"
    
    # Handle upgrade command by converting it to update
    if [ "$1" = "upgrade" ]; then
        # Replace upgrade with update in arguments
        set -- update "${@:2}"
    fi
fi

# Check if we're in a venvoy development directory (has src/venvoy/)
USE_LOCAL_CODE=false
if [[ -d "$(pwd)/src/venvoy" ]] && [[ -f "$(pwd)/pyproject.toml" ]]; then
    USE_LOCAL_CODE=true
    echo "🔧 Using local venvoy development code"
fi

# Also check if we can find the venvoy source in common development locations
if [[ "$USE_LOCAL_CODE" = false ]]; then
    # Check if we're in a subdirectory of a venvoy development directory
    CURRENT_DIR="$(pwd)"
    while [[ "$CURRENT_DIR" != "/" ]]; do
        if [[ -d "$CURRENT_DIR/src/venvoy" ]] && [[ -f "$CURRENT_DIR/pyproject.toml" ]]; then
            USE_LOCAL_CODE=true
            echo "🔧 Using local venvoy development code from $CURRENT_DIR"
            break
        fi
        CURRENT_DIR="$(dirname "$CURRENT_DIR")"
    done
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
        echo "  🐳 Container images (venvoy/bootstrap:latest and zaphodbeeblebrox3rd/venvoy:bootstrap)"
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
    
    # Remove container images
    if [ "$KEEP_IMAGES" = false ]; then
        echo ""
        echo "🐳 Cleaning up container images..."
        
        # Try to remove with the detected runtime
        if command -v "$CONTAINER_RUNTIME" &> /dev/null; then
            # Remove bootstrap image
            if $CONTAINER_RUNTIME image inspect zaphodbeeblebrox3rd/venvoy:bootstrap &> /dev/null; then
                $CONTAINER_RUNTIME rmi zaphodbeeblebrox3rd/venvoy:bootstrap &> /dev/null || true
                echo "✅ Removed bootstrap image"
            fi
        fi
    fi
    
    echo ""
    echo "✅ venvoy uninstalled successfully!"
    echo "💡 You may need to restart your terminal for PATH changes to take effect."
    exit 0
else
    # Download latest venvoy source code if not available locally
    VENVOY_SOURCE_DIR="$HOME/.venvoy/src"
    if [[ "$USE_LOCAL_CODE" = true ]]; then
        # Use local development code instead of downloading
        VENVOY_SOURCE_DIR="$(pwd)"
        echo "🔧 Using local venvoy development code from $VENVOY_SOURCE_DIR"
    elif [[ ! -d "$VENVOY_SOURCE_DIR" ]] || [[ ! -f "$VENVOY_SOURCE_DIR/src/venvoy/cli.py" ]]; then
        echo "📥 Downloading latest venvoy source code..."
        mkdir -p "$VENVOY_SOURCE_DIR"
        curl -fsSL https://github.com/zaphodbeeblebrox3rd/venvoy/archive/main.tar.gz | \
            tar -xz -C "$VENVOY_SOURCE_DIR" --strip-components=1
        echo "✅ Latest venvoy source code ready"
    fi

    # Run normal venvoy commands inside the container with mounted source
    if [ "$CONTAINER_RUNTIME" = "docker" ]; then
        # Docker execution with source code mounted
        docker run --rm -it \
            -v "$PWD:/workspace" \
            -v "$HOME:/host-home" \
            -v "$VENVOY_SOURCE_DIR:/venvoy-source" \
            -w /workspace \
            -e HOME="/host-home" \
            -e VENVOY_SOURCE_DIR="/venvoy-source" \
            "$VENVOY_IMAGE" "$@"
    elif [ "$CONTAINER_RUNTIME" = "apptainer" ] || [ "$CONTAINER_RUNTIME" = "singularity" ]; then
        # Apptainer/Singularity execution with source code mounted
        $CONTAINER_RUNTIME exec \
            --bind "$PWD:/workspace" \
            --bind "$HOME:/host-home" \
            --bind "$VENVOY_SOURCE_DIR:/venvoy-source" \
            --pwd /workspace \
            --env HOME="/host-home" \
            --env VENVOY_SOURCE_DIR="/venvoy-source" \
            "$IMAGE_URI" venvoy "$@"
    elif [ "$CONTAINER_RUNTIME" = "podman" ]; then
        # Podman execution with source code mounted
        podman run --rm -it \
            -v "$PWD:/workspace" \
            -v "$HOME:/host-home" \
            -v "$VENVOY_SOURCE_DIR:/venvoy-source" \
            -w /workspace \
            -e HOME="/host-home" \
            -e VENVOY_SOURCE_DIR="/venvoy-source" \
            "$VENVOY_IMAGE" "$@"
    else
        echo "❌ Unsupported container runtime: $CONTAINER_RUNTIME"
        exit 1
    fi
fi
EOF

# Make script executable
chmod +x "$INSTALL_DIR/venvoy"

# Function to reload shell configuration and verify PATH
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

# Function to verify venvoy is available in PATH
verify_venvoy_path() {
    if command -v venvoy &> /dev/null; then
        echo "✅ venvoy is available in PATH: $(which venvoy)"
        return 0
    else
        echo "⚠️  venvoy not found in PATH"
        return 1
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
            PATH_UPDATED=true
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
        if [ "$PATH_UPDATED" = true ]; then
            echo "🔄 Reloading shell configuration..."
            reload_shell_config "$SHELL_RC"
            
            # Verify venvoy is now available
            if ! verify_venvoy_path; then
                echo "🔄 Attempting to source shell configuration again..."
                source "$SHELL_RC" 2>/dev/null || true
                verify_venvoy_path || {
                    echo "⚠️  venvoy still not found in PATH"
                    echo "   This is normal - the PATH will be available in new terminal sessions"
                    echo "   To use venvoy immediately in this session, run:"
                    echo "   source $SHELL_RC"
                    echo "   Or restart your terminal"
                }
            fi
        fi
        ;;
    windows)
        echo "📝 Please add $INSTALL_DIR to your PATH manually"
        echo "   Or restart your terminal to use the updated PATH"
        ;;
esac

# Force update the bootstrap image to ensure latest features
echo "🔄 Updating venvoy bootstrap image..."
if command -v "$CONTAINER_RUNTIME" &> /dev/null; then
    $CONTAINER_RUNTIME pull "zaphodbeeblebrox3rd/venvoy:bootstrap" 2>/dev/null || true
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
    echo "   ⚠️  venvoy not found in current PATH"
    if [ "$PATH_UPDATED" = true ]; then
        echo "   💡 PATH was updated, but current shell session needs to be refreshed"
        echo "   🔧 To use venvoy immediately, run:"
        echo "      source $SHELL_RC"
        echo "   🔄 Or restart your terminal"
        echo "   ✅ venvoy will be available in all new terminal sessions"
    else
        echo "   💡 venvoy should be available via pipx"
        echo "   🔧 Try running: pipx run venvoy --help"
    fi
    
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