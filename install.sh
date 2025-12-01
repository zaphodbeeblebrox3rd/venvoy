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

# Clone repository to temporary directory for usage analytics (non-blocking)
if command -v git &> /dev/null; then
    TEMP_CLONE_DIR=$(mktemp -d 2>/dev/null || mktemp -d -t 'venvoy-install')
    if [ -n "$TEMP_CLONE_DIR" ]; then
        echo "📊 Tracking installation for analytics..."
        git clone --depth 1 --quiet https://github.com/zaphodbeeblebrox3rd/venvoy.git "$TEMP_CLONE_DIR" 2>/dev/null || true
        rm -rf "$TEMP_CLONE_DIR" 2>/dev/null || true
    fi
fi

# Check for any supported container runtime (prioritize HPC runtimes, then check accessibility)
CONTAINER_RUNTIME=""
if command -v apptainer &> /dev/null; then
    CONTAINER_RUNTIME="apptainer"
elif command -v singularity &> /dev/null; then
    CONTAINER_RUNTIME="singularity"
elif command -v docker &> /dev/null; then
    # Check if Docker is accessible (not just installed)
    if docker info &> /dev/null; then
        CONTAINER_RUNTIME="docker"
    elif command -v podman &> /dev/null; then
        # Docker is installed but not accessible, use Podman instead
        CONTAINER_RUNTIME="podman"
        echo "⚠️  Docker found but not accessible, using Podman instead"
    else
        # Docker is installed but not accessible, and Podman not available
        CONTAINER_RUNTIME="docker"
    fi
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

# Function to manage PATH entries in shell configuration files
manage_path_entry() {
    local shell_rc="$1"
    local path_entry="$2"
    local description="$3"
    
    if [[ ! -f "$shell_rc" ]]; then
        touch "$shell_rc"
    fi
    
    # Check if PATH entry already exists
    if grep -q "export PATH.*$path_entry" "$shell_rc" 2>/dev/null; then
        echo "📝 $description already in PATH"
        return 0
    fi
    
    # Check if there's an existing PATH export line
    if grep -q "^export PATH=" "$shell_rc" 2>/dev/null; then
        # Update existing PATH line to include new entry
        sed -i.bak "s|^export PATH=\"\(.*\)\"|export PATH=\"$path_entry:\1\"|" "$shell_rc"
        echo "📝 Added $description to existing PATH in $(basename "$shell_rc")"
    else
        # Add new PATH export line
        echo "" >> "$shell_rc"
        echo "# Added by venvoy installer" >> "$shell_rc"
        echo "export PATH=\"$path_entry:\$PATH\"" >> "$shell_rc"
        echo "📝 Added $description to PATH in $(basename "$shell_rc")"
    fi
    
    # Clean up backup file
    rm -f "$shell_rc.bak" 2>/dev/null || true
}

# Ensure ~/.local/bin is in PATH for user installs
PATH_UPDATED=false
if [[ ":$PATH:" != *":$HOME/.local/bin:"* ]]; then
    manage_path_entry "$HOME/.bashrc" "$HOME/.local/bin" "pipx directory"
    export PATH="$HOME/.local/bin:$PATH"
    PATH_UPDATED=true
    
    # Also add to current shell's RC file if different from ~/.bashrc
    if [[ -n "$ZSH_VERSION" ]] || [[ "$SHELL" == *"zsh"* ]]; then
        if [[ "$HOME/.zshrc" != "$HOME/.bashrc" ]]; then
            manage_path_entry "$HOME/.zshrc" "$HOME/.local/bin" "pipx directory"
        fi
    fi
fi

# Download or create venvoy bootstrap script
# Remove existing bootstrap script to ensure clean update
rm -f "$INSTALL_DIR/venvoy"
cat > "$INSTALL_DIR/venvoy" << 'EOF'
#!/bin/bash
# venvoy Bootstrap Script - runs venvoy inside container

set -e

# Detect container runtime (prioritize HPC runtimes, then check accessibility)
CONTAINER_RUNTIME=""
if command -v apptainer &> /dev/null; then
    CONTAINER_RUNTIME="apptainer"
elif command -v singularity &> /dev/null; then
    CONTAINER_RUNTIME="singularity"
elif command -v docker &> /dev/null; then
    # Check if Docker is accessible (not just installed)
    if docker info &> /dev/null; then
        CONTAINER_RUNTIME="docker"
    elif command -v podman &> /dev/null; then
        # Docker is installed but not accessible, use Podman instead
        CONTAINER_RUNTIME="podman"
        echo "⚠️  Docker found but not accessible, using Podman instead"
    else
        # Docker is installed but not accessible, and Podman not available
        CONTAINER_RUNTIME="docker"
    fi
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
elif [ "$CONTAINER_RUNTIME" = "podman" ]; then
    # Podman requires fully qualified image names
    IMAGE_URI="docker.io/$VENVOY_IMAGE"
else
    IMAGE_URI="$VENVOY_IMAGE"
fi

# Function to handle container runtime errors
handle_container_error() {
    local error_output="$1"
    local runtime="$2"
    
    if echo "$error_output" | grep -qi "permission denied\|docker.sock"; then
        echo ""
        echo "❌ Permission denied: Cannot access $runtime"
        echo ""
        if [ "$runtime" = "docker" ]; then
            echo "💡 Solutions:"
            echo "   1. Add your user to the docker group (recommended):"
            echo "      sudo usermod -aG docker \$USER"
            echo "      Then log out and back in, or run: newgrp docker"
            echo ""
            echo "   2. Use Podman instead (rootless, no permissions needed):"
            echo "      sudo apt install podman  # or equivalent for your distro"
            echo ""
            echo "   3. Use Apptainer/Singularity (HPC-friendly, no root needed):"
            echo "      See: https://apptainer.org/docs/user/main/quick_start.html"
            echo ""
            echo "   4. Start Docker service (if not running):"
            echo "      sudo systemctl start docker"
        fi
        exit 1
    fi
}

# Function to test container runtime access
test_container_access() {
    local runtime="$1"
    if [ "$runtime" = "docker" ]; then
        # Test docker access by trying to run a simple command
        if ! docker info &> /dev/null; then
            ERROR_OUTPUT=$(docker info 2>&1)
            handle_container_error "$ERROR_OUTPUT" "$runtime"
        fi
    fi
}

# Function to check if Cursor is available
check_cursor_available() {
    command -v cursor &> /dev/null || \
    [ -f "/Applications/Cursor.app/Contents/Resources/app/bin/cursor" ] || \
    [ -f "$HOME/Applications/Cursor.app/Contents/Resources/app/bin/cursor" ] || \
    [ -f "/usr/bin/cursor" ] || \
    [ -f "/usr/local/bin/cursor" ] || \
    [ -f "$HOME/.local/bin/cursor" ]
}

# Function to check if VSCode is available
check_vscode_available() {
    command -v code &> /dev/null || \
    [ -f "/Applications/Visual Studio Code.app/Contents/Resources/app/bin/code" ] || \
    [ -f "$HOME/Applications/Visual Studio Code.app/Contents/Resources/app/bin/code" ] || \
    [ -f "/usr/bin/code" ] || \
    [ -f "/usr/local/bin/code" ] || \
    [ -f "$HOME/.local/bin/code" ]
}

# Function to get editor command path
get_editor_command() {
    local editor="$1"
    if [ "$editor" = "cursor" ]; then
        if command -v cursor &> /dev/null; then
            echo "cursor"
        elif [ -f "/Applications/Cursor.app/Contents/Resources/app/bin/cursor" ]; then
            echo "/Applications/Cursor.app/Contents/Resources/app/bin/cursor"
        elif [ -f "$HOME/Applications/Cursor.app/Contents/Resources/app/bin/cursor" ]; then
            echo "$HOME/Applications/Cursor.app/Contents/Resources/app/bin/cursor"
        elif [ -f "/usr/bin/cursor" ]; then
            echo "/usr/bin/cursor"
        elif [ -f "/usr/local/bin/cursor" ]; then
            echo "/usr/local/bin/cursor"
        elif [ -f "$HOME/.local/bin/cursor" ]; then
            echo "$HOME/.local/bin/cursor"
        fi
    elif [ "$editor" = "vscode" ]; then
        if command -v code &> /dev/null; then
            echo "code"
        elif [ -f "/Applications/Visual Studio Code.app/Contents/Resources/app/bin/code" ]; then
            echo "/Applications/Visual Studio Code.app/Contents/Resources/app/bin/code"
        elif [ -f "$HOME/Applications/Visual Studio Code.app/Contents/Resources/app/bin/code" ]; then
            echo "$HOME/Applications/Visual Studio Code.app/Contents/Resources/app/bin/code"
        elif [ -f "/usr/bin/code" ]; then
            echo "/usr/bin/code"
        elif [ -f "/usr/local/bin/code" ]; then
            echo "/usr/local/bin/code"
        elif [ -f "$HOME/.local/bin/code" ]; then
            echo "$HOME/.local/bin/code"
        fi
    fi
}

# Pull venvoy image if it doesn't exist or force update
if ! $CONTAINER_RUNTIME image inspect "$IMAGE_URI" &> /dev/null; then
    echo "📦 Downloading venvoy bootstrap environment..."
    echo "   This may take a few minutes on first run..."
    if [ "$CONTAINER_RUNTIME" = "apptainer" ] || [ "$CONTAINER_RUNTIME" = "singularity" ]; then
        # For Apptainer/Singularity, use --force to overwrite existing SIF files
        # Progress is shown by default
        if ! $CONTAINER_RUNTIME pull --force "$IMAGE_URI"; then
            handle_container_error "Failed to pull bootstrap image" "$CONTAINER_RUNTIME"
        fi
    else
        # Docker/Podman show progress by default - let it display
        if ! $CONTAINER_RUNTIME pull "$IMAGE_URI"; then
            handle_container_error "Failed to pull bootstrap image" "$CONTAINER_RUNTIME"
        fi
    fi
    echo "✅ Bootstrap environment ready"
elif [ "\$1" = "update" ] || [ "\$1" = "upgrade" ]; then
    echo "🔄 Updating venvoy environment..."
    if [ "$CONTAINER_RUNTIME" = "apptainer" ] || [ "$CONTAINER_RUNTIME" = "singularity" ]; then
        # For Apptainer/Singularity, use --force to overwrite existing SIF files
        if ! $CONTAINER_RUNTIME pull --force "$IMAGE_URI"; then
            handle_container_error "Failed to update bootstrap image" "$CONTAINER_RUNTIME"
        fi
    else
        # Docker/Podman show progress by default
        if ! $CONTAINER_RUNTIME pull "$IMAGE_URI"; then
            handle_container_error "Failed to update bootstrap image" "$CONTAINER_RUNTIME"
        fi
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

# Handle run command specially
if [ "$1" = "run" ]; then
    # Parse run command arguments
    shift  # Remove 'run' from arguments
    RUN_NAME="venvoy-env"
    RUN_COMMAND=""
    RUN_MOUNTS=""
    
    while [[ $# -gt 0 ]]; do
        case $1 in
            --name)
                RUN_NAME="$2"
                shift 2
                ;;
            --command)
                RUN_COMMAND="$2"
                shift 2
                ;;
            --mount)
                if [ -z "$RUN_MOUNTS" ]; then
                    RUN_MOUNTS="-v $2"
                else
                    RUN_MOUNTS="$RUN_MOUNTS -v $2"
                fi
                shift 2
                ;;
            *)
                echo "Unknown option: $1"
                exit 1
                ;;
        esac
    done
    
    # Check if environment exists and is valid, auto-detect if default not found
    ENV_DIR="$HOME/.venvoy/environments"
    if [ ! -d "$HOME/.venvoy/environments/$RUN_NAME" ] || [ ! -f "$HOME/.venvoy/environments/$RUN_NAME/config.yaml" ]; then
        # Try to auto-detect if there's only one valid environment
        if [ -d "$ENV_DIR" ]; then
            # Count valid environments (those with config.yaml)
            VALID_ENVS=()
            for env_path in "$ENV_DIR"/*; do
                if [ -d "$env_path" ] && [ -f "$env_path/config.yaml" ]; then
                    VALID_ENVS+=("$(basename "$env_path")")
                fi
            done
            
            VALID_COUNT=${#VALID_ENVS[@]}
            if [ "$VALID_COUNT" -eq 1 ]; then
                # Only one valid environment exists, use it
                AUTO_DETECTED_NAME="${VALID_ENVS[0]}"
                echo "⚠️  Environment '$RUN_NAME' not found or incomplete, but found one valid environment: '$AUTO_DETECTED_NAME'"
                RUN_NAME="$AUTO_DETECTED_NAME"
            elif [ "$VALID_COUNT" -gt 1 ]; then
                # Multiple valid environments exist, list them
                echo "❌ Environment '$RUN_NAME' not found or incomplete."
                echo ""
                echo "📋 Available environments:"
                for env_name in "${VALID_ENVS[@]}"; do
                    echo "   • $env_name"
                done
                echo ""
                echo "💡 Use: venvoy run --name <environment-name>"
                exit 1
            else
                # No valid environments found
                echo "❌ Environment '$RUN_NAME' not found. No valid environments exist."
                echo "💡 Create one with: venvoy init --name $RUN_NAME"
                exit 1
            fi
        else
            echo "❌ Environment '$RUN_NAME' not found. No environments exist."
            echo "💡 Create one with: venvoy init --name $RUN_NAME"
            exit 1
        fi
    fi
    
    echo "🏃 Launching environment: $RUN_NAME"
    
    # Load environment configuration
    if [ -f "$HOME/.venvoy/environments/$RUN_NAME/config.yaml" ]; then
        # Extract python_version from YAML, handling single quotes, double quotes, and no quotes
        # Use head -1 to get only the first match (top-level python_version, not nested ones)
        PYTHON_VERSION_RAW=$(grep "^python_version:" "$HOME/.venvoy/environments/$RUN_NAME/config.yaml" | head -1)
        PYTHON_VERSION=$(echo "$PYTHON_VERSION_RAW" | sed -E "s/^python_version:[[:space:]]*['\"]?([0-9]+\.[0-9]+)['\"]?[[:space:]]*$/\1/" | tr -d '[:space:]')
        
        # If that didn't work, try a more flexible pattern (but still get first match)
        if [ -z "$PYTHON_VERSION" ] || [ "$PYTHON_VERSION" = "python_version" ] || ! echo "$PYTHON_VERSION" | grep -qE '^[0-9]+\.[0-9]+$'; then
            PYTHON_VERSION_RAW=$(grep "python_version:" "$HOME/.venvoy/environments/$RUN_NAME/config.yaml" | grep -v "^[[:space:]]" | head -1)
            PYTHON_VERSION=$(echo "$PYTHON_VERSION_RAW" | sed -E "s/.*python_version:[[:space:]]*['\"]?([0-9]+\.[0-9]+)['\"]?.*/\1/" | tr -d '[:space:]')
        fi
        
        # Final validation - must be in format X.Y and not contain any non-digit characters
        if [ -z "$PYTHON_VERSION" ] || ! echo "$PYTHON_VERSION" | grep -qE '^[0-9]+\.[0-9]+$'; then
            echo "❌ Could not extract python_version from config.yaml"
            echo "   Raw line: '$PYTHON_VERSION_RAW'"
            echo "   Extracted value: '$PYTHON_VERSION'"
            echo "💡 Try reinitializing the environment: venvoy init --name $RUN_NAME --force"
            exit 1
        fi
        
        if [ "$CONTAINER_RUNTIME" = "podman" ]; then
            # Podman requires fully qualified image names
            IMAGE_NAME="docker.io/zaphodbeeblebrox3rd/venvoy:python$PYTHON_VERSION"
        else
            IMAGE_NAME="zaphodbeeblebrox3rd/venvoy:python$PYTHON_VERSION"
        fi
    else
        echo "❌ Environment configuration not found for '$RUN_NAME'"
        echo ""
        ENV_DIR="$HOME/.venvoy/environments"
        if [ -d "$ENV_DIR" ]; then
            ENV_COUNT=$(find "$ENV_DIR" -mindepth 1 -maxdepth 1 -type d 2>/dev/null | wc -l)
            if [ "$ENV_COUNT" -gt 0 ]; then
                echo "📋 Available environments:"
                for env_path in "$ENV_DIR"/*; do
                    if [ -d "$env_path" ] && [ -f "$env_path/config.yaml" ]; then
                        env_name=$(basename "$env_path")
                        echo "   • $env_name"
                    fi
                done
                echo ""
            fi
        fi
        echo "💡 Use: venvoy run --name <environment-name>"
        echo "   Or create a new environment: venvoy init --name $RUN_NAME"
        exit 1
    fi
    
    # Ensure image is available
    # Format image URI for pulling based on runtime
    if [ "$CONTAINER_RUNTIME" = "apptainer" ] || [ "$CONTAINER_RUNTIME" = "singularity" ]; then
        PULL_IMAGE_URI="docker://$IMAGE_NAME"
    elif [ "$CONTAINER_RUNTIME" = "podman" ]; then
        PULL_IMAGE_URI="$IMAGE_NAME"  # Already has docker.io prefix
    else
        PULL_IMAGE_URI="$IMAGE_NAME"
    fi
    
    # Validate image name format
    if [ -z "$IMAGE_NAME" ] || [ "$IMAGE_NAME" = "docker.io/zaphodbeeblebrox3rd/venvoy:python" ] || [ "$IMAGE_NAME" = "zaphodbeeblebrox3rd/venvoy:python" ]; then
        echo "❌ Invalid image name format: '$IMAGE_NAME'"
        echo "   Python version: '$PYTHON_VERSION'"
        echo "💡 Try reinitializing the environment: venvoy init --name $RUN_NAME --force"
        exit 1
    fi
    
    if ! $CONTAINER_RUNTIME image inspect "$PULL_IMAGE_URI" &> /dev/null; then
        echo "📦 Downloading environment image..."
        echo "   This may take a few minutes on first run..."
        if [ "$CONTAINER_RUNTIME" = "apptainer" ] || [ "$CONTAINER_RUNTIME" = "singularity" ]; then
            # Apptainer/Singularity shows progress by default
            if ! $CONTAINER_RUNTIME pull --force "$PULL_IMAGE_URI"; then
                echo "❌ Failed to download image"
                exit 1
            fi
        else
            # Docker/Podman show progress by default - let it display
            if ! $CONTAINER_RUNTIME pull "$PULL_IMAGE_URI"; then
                echo "❌ Failed to download image"
                exit 1
            fi
        fi
        echo "✅ Environment image ready"
    else
        echo "✅ Environment image already available"
    fi
    
    # Get host user's UID and GID for permission mapping
    HOST_UID=$(id -u)
    HOST_GID=$(id -g)
    
    # Check for available editors
    CURSOR_AVAILABLE=false
    VSCODE_AVAILABLE=false
    if check_cursor_available; then
        CURSOR_AVAILABLE=true
    elif check_vscode_available; then
        VSCODE_AVAILABLE=true
    fi
    
    # Determine container name for editor connection (use $$ for process ID to ensure uniqueness)
    CONTAINER_NAME="venvoy-${RUN_NAME}-$$"
    
    # If editor is available and no custom command specified, launch editor
    if [ -z "$RUN_COMMAND" ] && { [ "$CURSOR_AVAILABLE" = true ] || [ "$VSCODE_AVAILABLE" = true ]; }; then
        # Determine which editor to use (prefer Cursor)
        if [ "$CURSOR_AVAILABLE" = true ]; then
            EDITOR_TYPE="cursor"
            EDITOR_CMD=$(get_editor_command "cursor")
        else
            EDITOR_TYPE="vscode"
            EDITOR_CMD=$(get_editor_command "vscode")
        fi
        
        echo "🚀 Starting container in background..."
        echo "🧠 Launching $EDITOR_TYPE connected to container..."
        echo ""
        
        # Start container in detached mode
        if [ "$CONTAINER_RUNTIME" = "docker" ]; then
            test_container_access "$CONTAINER_RUNTIME"
            docker run -d --name "$CONTAINER_NAME" \
                --user "$HOST_UID:$HOST_GID" \
                -v "$PWD:/workspace" \
                -v "$HOME:/host-home" \
                -w /home/venvoy \
                -e VENVOY_HOST_RUNTIME="$CONTAINER_RUNTIME" \
                -e VENVOY_HOST_HOME="/host-home" \
                $RUN_MOUNTS \
                "$IMAGE_NAME" sleep infinity || {
                    echo "❌ Failed to start container"
                    exit 1
                }
            
            # Wait a moment for container to be ready
            sleep 2
            
            # Launch editor connected to container
            if [ "$EDITOR_TYPE" = "cursor" ]; then
                "$EDITOR_CMD" --folder-uri "vscode-remote://attached-container+${CONTAINER_NAME}/home/venvoy" 2>/dev/null || {
                    echo "⚠️  Failed to launch Cursor. Stopping container and falling back to shell..."
                    docker stop "$CONTAINER_NAME" >/dev/null 2>&1
                    docker rm "$CONTAINER_NAME" >/dev/null 2>&1
                    CURSOR_AVAILABLE=false
                    VSCODE_AVAILABLE=false
                }
            else
                "$EDITOR_CMD" --folder-uri "vscode-remote://attached-container+${CONTAINER_NAME}/home/venvoy" 2>/dev/null || {
                    echo "⚠️  Failed to launch VSCode. Stopping container and falling back to shell..."
                    docker stop "$CONTAINER_NAME" >/dev/null 2>&1
                    docker rm "$CONTAINER_NAME" >/dev/null 2>&1
                    CURSOR_AVAILABLE=false
                    VSCODE_AVAILABLE=false
                }
            fi
            
            if [ "$CURSOR_AVAILABLE" = true ] || [ "$VSCODE_AVAILABLE" = true ]; then
                echo "✅ $EDITOR_TYPE connected to container!"
                echo "💡 Container is running in background: $CONTAINER_NAME"
                echo "💡 When you're done, stop the container with: $CONTAINER_RUNTIME stop $CONTAINER_NAME"
                echo "💡 Or use: $CONTAINER_RUNTIME rm -f $CONTAINER_NAME"
                exit 0
            fi
        elif [ "$CONTAINER_RUNTIME" = "podman" ]; then
            podman run -d --name "$CONTAINER_NAME" \
                --userns=keep-id \
                -v "$PWD:/workspace" \
                -v "$HOME:/host-home" \
                -w /home/venvoy \
                -e VENVOY_HOST_RUNTIME="$CONTAINER_RUNTIME" \
                -e VENVOY_HOST_HOME="/host-home" \
                ${RUN_MOUNTS} \
                "$PULL_IMAGE_URI" sleep infinity || {
                    echo "❌ Failed to start container"
                    exit 1
                }
            
            # Wait a moment for container to be ready
            sleep 2
            
            # Launch editor connected to container
            if [ "$EDITOR_TYPE" = "cursor" ]; then
                "$EDITOR_CMD" --folder-uri "vscode-remote://attached-container+${CONTAINER_NAME}/home/venvoy" 2>/dev/null || {
                    echo "⚠️  Failed to launch Cursor. Stopping container and falling back to shell..."
                    podman stop "$CONTAINER_NAME" >/dev/null 2>&1
                    podman rm "$CONTAINER_NAME" >/dev/null 2>&1
                    CURSOR_AVAILABLE=false
                    VSCODE_AVAILABLE=false
                }
            else
                "$EDITOR_CMD" --folder-uri "vscode-remote://attached-container+${CONTAINER_NAME}/home/venvoy" 2>/dev/null || {
                    echo "⚠️  Failed to launch VSCode. Stopping container and falling back to shell..."
                    podman stop "$CONTAINER_NAME" >/dev/null 2>&1
                    podman rm "$CONTAINER_NAME" >/dev/null 2>&1
                    CURSOR_AVAILABLE=false
                    VSCODE_AVAILABLE=false
                }
            fi
            
            if [ "$CURSOR_AVAILABLE" = true ] || [ "$VSCODE_AVAILABLE" = true ]; then
                echo "✅ $EDITOR_TYPE connected to container!"
                echo "💡 Container is running in background: $CONTAINER_NAME"
                echo "💡 When you're done, stop the container with: $CONTAINER_RUNTIME stop $CONTAINER_NAME"
                echo "💡 Or use: $CONTAINER_RUNTIME rm -f $CONTAINER_NAME"
                exit 0
            fi
        fi
        # If we get here, editor launch failed, fall through to shell
    fi
    
    # No editor available or editor launch failed - use interactive shell
    echo "🚀 Starting container..."
    if [ "$CURSOR_AVAILABLE" = false ] && [ "$VSCODE_AVAILABLE" = false ]; then
        echo "   No editor detected - launching interactive shell..."
    else
        echo "   Editor launch failed - falling back to interactive shell..."
    fi
    echo ""
    
    # Run the environment with interactive shell
    # Start in /home/venvoy (container's home) - users can cd to /workspace for their project
    if [ "$CONTAINER_RUNTIME" = "docker" ]; then
        test_container_access "$CONTAINER_RUNTIME"
        # Docker: Use --user to map host UID/GID for read/write access
        docker run --rm -it \
            --user "$HOST_UID:$HOST_GID" \
            -v "$PWD:/workspace" \
            -v "$HOME:/host-home" \
            -w /home/venvoy \
            -e VENVOY_HOST_RUNTIME="$CONTAINER_RUNTIME" \
            -e VENVOY_HOST_HOME="/host-home" \
            $RUN_MOUNTS \
            "$IMAGE_NAME" ${RUN_COMMAND:-bash} || {
                echo ""
                echo "❌ Failed to run Docker container"
                echo "💡 Check Docker permissions or try: sudo usermod -aG docker \$USER"
                exit 1
            }
    elif [ "$CONTAINER_RUNTIME" = "apptainer" ] || [ "$CONTAINER_RUNTIME" = "singularity" ]; then
        # Apptainer/Singularity: User namespace is handled automatically, mount as read/write
        # Note: Editor connection not supported for Apptainer/Singularity, use shell
        $CONTAINER_RUNTIME exec \
            --bind "$PWD:/workspace" \
            --bind "$HOME:/host-home" \
            --pwd /home/venvoy \
            --env VENVOY_HOST_RUNTIME="$CONTAINER_RUNTIME" \
            --env VENVOY_HOST_HOME="/host-home" \
            $RUN_MOUNTS \
            "$IMAGE_URI" ${RUN_COMMAND:-bash}
    elif [ "$CONTAINER_RUNTIME" = "podman" ]; then
        # Podman: Use --userns=keep-id to map host UID/GID automatically for read/write access
        # Mount host home to /host-home but use container's home as HOME to avoid .bashrc permission issues
        podman run --rm -it \
            --userns=keep-id \
            -v "$PWD:/workspace" \
            -v "$HOME:/host-home" \
            -w /home/venvoy \
            -e VENVOY_HOST_RUNTIME="$CONTAINER_RUNTIME" \
            -e VENVOY_HOST_HOME="/host-home" \
            ${RUN_MOUNTS} \
            "$PULL_IMAGE_URI" ${RUN_COMMAND:-bash} || {
                echo ""
                echo "❌ Failed to run Podman container"
                echo "   Image: $PULL_IMAGE_URI"
                echo "💡 Check Podman installation and image availability"
                exit 1
            }
    else
        echo "❌ Unsupported container runtime: $CONTAINER_RUNTIME"
        exit 1
    fi
    
    exit 0
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
                    
                    # Remove venvoy-related lines more carefully
                    # Remove the installer comment and the following export line
                    sed -i.bak '/# Added by venvoy installer/,+1d' "$shell_file"
                    
                    # Remove venvoy installation directory from existing PATH entries
                    sed -i.bak "s|$INSTALL_DIR:||g" "$shell_file"
                    sed -i.bak "s|:$INSTALL_DIR||g" "$shell_file"
                    sed -i.bak "s|$INSTALL_DIR||g" "$shell_file"
                    
                    # Clean up any empty PATH exports
                    sed -i.bak '/^export PATH=":\$PATH"$/d' "$shell_file"
                    sed -i.bak '/^export PATH="\$PATH"$/d' "$shell_file"
                    
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
        
        # Try to remove with the detected runtime using correct commands
        if command -v "$CONTAINER_RUNTIME" &> /dev/null; then
            if [ "$CONTAINER_RUNTIME" = "docker" ] || [ "$CONTAINER_RUNTIME" = "podman" ]; then
                # Docker/Podman use 'rmi' command
                if $CONTAINER_RUNTIME image inspect zaphodbeeblebrox3rd/venvoy:bootstrap &> /dev/null; then
                    $CONTAINER_RUNTIME rmi zaphodbeeblebrox3rd/venvoy:bootstrap &> /dev/null || true
                    echo "✅ Removed bootstrap image"
                fi
            elif [ "$CONTAINER_RUNTIME" = "apptainer" ] || [ "$CONTAINER_RUNTIME" = "singularity" ]; then
                # Apptainer/Singularity use cache clean instead of rmi
                echo "🧹 Cleaning Apptainer/Singularity cache..."
                $CONTAINER_RUNTIME cache clean --force &> /dev/null || true
                echo "✅ Cleaned container cache"
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

    # Get host user's UID and GID for permission mapping
    HOST_UID=$(id -u)
    HOST_GID=$(id -g)
    
    # Run normal venvoy commands inside the container with mounted source
    if [ "$CONTAINER_RUNTIME" = "docker" ]; then
        # Docker execution with source code mounted
        test_container_access "$CONTAINER_RUNTIME"
        docker run --rm -it \
            --user "$HOST_UID:$HOST_GID" \
            -v "$PWD:/workspace" \
            -v "$HOME:/host-home" \
            -v "$VENVOY_SOURCE_DIR:/venvoy-source" \
            -w /workspace \
            -e VENVOY_SOURCE_DIR="/venvoy-source" \
            -e VENVOY_HOST_RUNTIME="$CONTAINER_RUNTIME" \
            -e VENVOY_HOST_HOME="/host-home" \
            "$VENVOY_IMAGE" "$@" || {
                echo ""
                echo "❌ Failed to run Docker container"
                echo "💡 Check Docker permissions or try: sudo usermod -aG docker \$USER"
                exit 1
            }
    elif [ "$CONTAINER_RUNTIME" = "apptainer" ] || [ "$CONTAINER_RUNTIME" = "singularity" ]; then
        # Apptainer/Singularity execution with source code mounted
        # User namespace is handled automatically, mount as read/write
        $CONTAINER_RUNTIME exec \
            --bind "$PWD:/workspace" \
            --bind "$HOME:/host-home" \
            --bind "$VENVOY_SOURCE_DIR:/venvoy-source" \
            --pwd /workspace \
            --env VENVOY_SOURCE_DIR="/venvoy-source" \
            --env VENVOY_HOST_RUNTIME="$CONTAINER_RUNTIME" \
            --env VENVOY_HOST_HOME="/host-home" \
            "$IMAGE_URI" /usr/local/bin/venvoy-entrypoint "$@"
    elif [ "$CONTAINER_RUNTIME" = "podman" ]; then
        # Podman execution with source code mounted
        # Use --userns=keep-id to map host UID/GID automatically for read/write access
        podman run --rm -it \
            --userns=keep-id \
            -v "$PWD:/workspace" \
            -v "$HOME:/host-home" \
            -v "$VENVOY_SOURCE_DIR:/venvoy-source" \
            -w /workspace \
            -e VENVOY_SOURCE_DIR="/venvoy-source" \
            -e VENVOY_HOST_RUNTIME="$CONTAINER_RUNTIME" \
            -e VENVOY_HOST_HOME="/host-home" \
            "$IMAGE_URI" "$@"
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
        
        # Add venvoy installation directory to PATH using the management function
        if [[ "$SHELL_RC" == *"fish"* ]]; then
            # Fish shell has different syntax
            if ! grep -q "set -gx PATH.*$INSTALL_DIR" "$SHELL_RC" 2>/dev/null; then
                echo "" >> "$SHELL_RC"
                echo "# Added by venvoy installer" >> "$SHELL_RC"
                echo "set -gx PATH \"$INSTALL_DIR\" \$PATH" >> "$SHELL_RC"
                echo "📝 Added venvoy to PATH in $(basename "$SHELL_RC")"
                PATH_UPDATED=true
            else
                echo "📝 venvoy already in PATH"
            fi
        else
            # Use the PATH management function for bash/zsh
            manage_path_entry "$SHELL_RC" "$INSTALL_DIR" "venvoy installation directory"
            if [[ $? -eq 0 ]]; then
                PATH_UPDATED=true
            fi
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
    if [ "$CONTAINER_RUNTIME" = "podman" ]; then
        # Podman requires fully qualified image names
        $CONTAINER_RUNTIME pull "docker.io/zaphodbeeblebrox3rd/venvoy:bootstrap" 2>/dev/null || true
    else
        $CONTAINER_RUNTIME pull "zaphodbeeblebrox3rd/venvoy:bootstrap" 2>/dev/null || true
    fi
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
    echo "   1. Run: venvoy init --python-version <python-version> --name <environment-name>"
    echo "   2. Run: venvoy run --name <environment-name>"
    echo "      (This will automatically launch Cursor/VSCode if available)"
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
    echo "   1. Run: venvoy init --python-version <python-version> --name <environment-name>"
    echo "   2. Run: venvoy run --name <environment-name>"
    echo "      (This will automatically launch Cursor/VSCode if available)"
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