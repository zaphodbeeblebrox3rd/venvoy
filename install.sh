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
    # Detect if docker is actually Podman wrapper
    DOCKER_VERSION_OUT=$(docker --version 2>/dev/null || true)
    if echo "$DOCKER_VERSION_OUT" | grep -qi "podman"; then
        # docker command is a Podman shim; prefer Podman runtime
        if command -v podman &> /dev/null; then
            CONTAINER_RUNTIME="podman"
            echo "⚠️  Detected docker as Podman wrapper, using Podman runtime"
        else
            CONTAINER_RUNTIME="docker"
        fi
    else
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

# Check for podman-docker if using Podman (needed for Devin/VSCode Remote Containers)
if [ "$CONTAINER_RUNTIME" = "podman" ]; then
    # Check if podman-docker is installed
    PODMAN_DOCKER_INSTALLED=false
    if command -v docker > /dev/null 2>&1; then
        if docker --version 2>&1 | grep -qi podman; then
            PODMAN_DOCKER_INSTALLED=true
        fi
    fi
    
    # Check if Devin or VSCode might be available
    DEVIN_OR_VSCODE_AVAILABLE=false
    if command -v devin-desktop &> /dev/null || \
       [ -f "/Applications/Devin.app/Contents/Resources/app/bin/devin-desktop" ] || \
       [ -f "$HOME/Applications/Devin.app/Contents/Resources/app/bin/devin-desktop" ] || \
       command -v code &> /dev/null || \
       [ -f "/Applications/Visual Studio Code.app/Contents/Resources/app/bin/code" ] || \
       [ -f "$HOME/Applications/Visual Studio Code.app/Contents/Resources/app/bin/code" ]; then
        DEVIN_OR_VSCODE_AVAILABLE=true
    fi
    
    if [ "$PODMAN_DOCKER_INSTALLED" = false ] && [ "$DEVIN_OR_VSCODE_AVAILABLE" = true ]; then
        echo ""
        echo "💡 Devin/VSCode detected, but podman-docker is not installed."
        echo "   podman-docker is recommended for Devin/VSCode Remote Containers support with Podman."
        echo ""
        read -p "Would you like to install podman-docker now? (y/n) " -n 1 -r
        echo ""
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            case $PLATFORM in
                linux)
                    if command -v apt-get &> /dev/null; then
                        echo "📦 Installing podman-docker..."
                        sudo apt-get update && sudo apt-get install -y podman-docker || {
                            echo "⚠️  Failed to install podman-docker."
                            echo "   If you do not have sudo rights, please contact your system administrator to install podman-docker to enable connectivity from vscode and devin into launched containers"
                            echo "   Otherwise, you can install it manually with: sudo apt install podman-docker"
                        }
                    elif command -v dnf &> /dev/null; then
                        echo "📦 Installing podman-docker..."
                        sudo dnf install -y podman-docker || {
                            echo "⚠️  Failed to install podman-docker."
                            echo "   If you do not have sudo rights, please contact your system administrator to install podman-docker to enable connectivity from vscode and devin into launched containers"
                            echo "   Otherwise, you can install it manually with: sudo dnf install podman-docker"
                        }
                    elif command -v yum &> /dev/null; then
                        echo "📦 Installing podman-docker..."
                        sudo yum install -y podman-docker || {
                            echo "⚠️  Failed to install podman-docker."
                            echo "   If you do not have sudo rights, please contact your system administrator to install podman-docker to enable connectivity from vscode and devin into launched containers"
                            echo "   Otherwise, you can install it manually with: sudo yum install podman-docker"
                        }
                    elif command -v pacman &> /dev/null; then
                        echo "📦 Installing podman-docker..."
                        sudo pacman -S --noconfirm podman-docker || {
                            echo "⚠️  Failed to install podman-docker."
                            echo "   If you do not have sudo rights, please contact your system administrator to install podman-docker to enable connectivity from vscode and devin into launched containers"
                            echo "   Otherwise, you can install it manually with: sudo pacman -S podman-docker"
                        }
                    else
                        echo "⚠️  Could not detect package manager. Please install podman-docker manually:"
                        echo "   For Debian/Ubuntu: sudo apt install podman-docker"
                        echo "   For Fedora/RHEL: sudo dnf install podman-docker"
                        echo "   For Arch: sudo pacman -S podman-docker"
                    fi
                    ;;
                macos)
                    if command -v brew &> /dev/null; then
                        echo "📦 Installing podman-docker..."
                        brew install podman-docker || {
                            echo "⚠️  Failed to install podman-docker."
                            echo "   If you do not have sudo rights, please contact your system administrator to install podman-docker to enable connectivity from vscode and devin into launched containers"
                            echo "   Otherwise, you can install it manually with: brew install podman-docker"
                        }
                    else
                        echo "⚠️  Homebrew not found. Please install podman-docker manually:"
                        echo "   brew install podman-docker"
                    fi
                    ;;
                *)
                    echo "⚠️  Please install podman-docker manually for your platform"
                    ;;
            esac
        else
            echo "ℹ️  Skipping podman-docker installation."
            echo "   You can install it later if you want Devin/VSCode Remote Containers support:"
            case $PLATFORM in
                linux)
                    echo "   sudo apt install podman-docker  # or equivalent for your distro"
                    ;;
                macos)
                    echo "   brew install podman-docker"
                    ;;
            esac
        fi
        echo ""
    elif [ "$PODMAN_DOCKER_INSTALLED" = false ]; then
        echo "💡 Tip: Install podman-docker for Devin/VSCode Remote Containers support:"
        case $PLATFORM in
            linux)
                echo "   sudo apt install podman-docker  # or equivalent for your distro"
                ;;
            macos)
                echo "   brew install podman-docker"
                ;;
        esac
        echo ""
    fi
    
    # Set up Podman socket for Devin/VSCode Remote Containers compatibility
    # This is critical because Devin spawns child processes that run 'docker inspect'
    # and these processes need access to the Podman socket
    if [ "$DEVIN_OR_VSCODE_AVAILABLE" = true ] && [ "$PLATFORM" = "linux" ]; then
        echo "🔧 Setting up Podman socket for Devin/VSCode compatibility..."
        
        PODMAN_SOCKET_SETUP_SUCCESS=false
        
        # Step 1: Enable the systemd user podman socket if available
        if command -v systemctl &> /dev/null; then
            # Check if user socket unit exists
            if systemctl --user list-unit-files podman.socket &> /dev/null; then
                # Enable and start the socket
                if systemctl --user enable --now podman.socket 2>/dev/null; then
                    echo "   ✅ Enabled systemd user podman socket"
                    PODMAN_SOCKET_SETUP_SUCCESS=true
                    PODMAN_USER_SOCKET="${XDG_RUNTIME_DIR:-/run/user/$(id -u)}/podman/podman.sock"
                else
                    echo "   ⚠️  Could not enable systemd user podman socket"
                fi
            fi
        fi
        
        # Step 2: Set up DOCKER_HOST in environment.d for desktop applications
        # This makes DOCKER_HOST available to all processes in the user session
        if [ "$PODMAN_SOCKET_SETUP_SUCCESS" = true ]; then
            ENVIRONMENT_D_DIR="$HOME/.config/environment.d"
            mkdir -p "$ENVIRONMENT_D_DIR"
            
            # Create environment file for Podman socket
            cat > "$ENVIRONMENT_D_DIR/podman-docker.conf" << 'ENVEOF'
# Podman socket configuration for Docker compatibility
# This allows Devin, VSCode, and other tools that expect Docker to work with Podman
DOCKER_HOST=unix://${XDG_RUNTIME_DIR}/podman/podman.sock
ENVEOF
            echo "   ✅ Created $ENVIRONMENT_D_DIR/podman-docker.conf"
            
            # Also add to bashrc for terminal sessions
            if ! grep -q "DOCKER_HOST.*podman.sock" "$HOME/.bashrc" 2>/dev/null; then
                echo '' >> "$HOME/.bashrc"
                echo '# Podman socket for Docker compatibility (added by venvoy)' >> "$HOME/.bashrc"
                echo 'export DOCKER_HOST="unix://${XDG_RUNTIME_DIR}/podman/podman.sock"' >> "$HOME/.bashrc"
                echo "   ✅ Added DOCKER_HOST to ~/.bashrc"
            fi
            
            # Export for current session
            export DOCKER_HOST="unix://${XDG_RUNTIME_DIR:-/run/user/$(id -u)}/podman/podman.sock"
            
            # Step 2b: Create podman configuration to work with the user socket
            # This allows podman/docker commands to work without DOCKER_HOST being set
            CONTAINERS_CONF_DIR="$HOME/.config/containers"
            mkdir -p "$CONTAINERS_CONF_DIR"
            
            cat > "$CONTAINERS_CONF_DIR/containers.conf" << CONTAINERSCONF
[engine]
# Use the systemd user socket for Docker-compatible tools
# This allows Devin/VSCode to connect to containers without DOCKER_HOST
remote = false

[engine.service_destinations]
  [engine.service_destinations.default]
    uri = "unix:///run/user/$(id -u)/podman/podman.sock"
CONTAINERSCONF
            echo "   ✅ Created $CONTAINERS_CONF_DIR/containers.conf"
            
            # Step 2c: Create a docker wrapper script that sets DOCKER_HOST
            # This is critical because Devin's child processes don't inherit environment variables
            # and call docker directly without DOCKER_HOST set
            DOCKER_WRAPPER_DIR="$HOME/.local/bin"
            mkdir -p "$DOCKER_WRAPPER_DIR"
            
            cat > "$DOCKER_WRAPPER_DIR/docker" << 'DOCKERWRAPPER'
#!/bin/bash
# Docker wrapper for Podman compatibility with Devin/VSCode
# Created by venvoy installer
# This ensures DOCKER_HOST is set for Podman socket access

# Set DOCKER_HOST if not already set
if [ -z "$DOCKER_HOST" ]; then
    XDG_RUNTIME_DIR="${XDG_RUNTIME_DIR:-/run/user/$(id -u)}"
    if [ -S "$XDG_RUNTIME_DIR/podman/podman.sock" ]; then
        export DOCKER_HOST="unix://$XDG_RUNTIME_DIR/podman/podman.sock"
    elif [ -S "/run/podman/podman.sock" ]; then
        export DOCKER_HOST="unix:///run/podman/podman.sock"
    fi
fi

# Call podman
exec /usr/bin/podman "$@"
DOCKERWRAPPER
            chmod +x "$DOCKER_WRAPPER_DIR/docker"
            echo "   ✅ Created docker wrapper at $DOCKER_WRAPPER_DIR/docker"
            
            # Ensure ~/.local/bin is in PATH
            if ! grep -q 'export PATH="$HOME/.local/bin' "$HOME/.bashrc" 2>/dev/null; then
                echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$HOME/.bashrc"
                echo "   ✅ Added ~/.local/bin to PATH in ~/.bashrc"
            fi
        fi
        
        # Step 3: Update Devin settings to use the docker wrapper
        DEVIN_SETTINGS_DIR="$HOME/.config/Devin/User"
        if [ -d "$DEVIN_SETTINGS_DIR" ] || [ -d "$HOME/.config/Devin" ]; then
            mkdir -p "$DEVIN_SETTINGS_DIR"
            DEVIN_SETTINGS="$DEVIN_SETTINGS_DIR/settings.json"
            
            # Check if settings file exists and has content
            if [ -f "$DEVIN_SETTINGS" ] && [ -s "$DEVIN_SETTINGS" ]; then
                # Backup existing settings
                cp "$DEVIN_SETTINGS" "$DEVIN_SETTINGS.venvoy-backup" 2>/dev/null || true
                
                # Check if docker settings already exist
                if ! grep -q '"remote.devinDevContainers.dockerPath"' "$DEVIN_SETTINGS" 2>/dev/null; then
                    # Add docker settings before the closing brace
                    # Use a temp file to avoid issues
                    TEMP_SETTINGS=$(mktemp)
                    # Remove trailing } and whitespace, add our settings, then close
                    sed '$ s/}$//' "$DEVIN_SETTINGS" | sed -e :a -e '/^[[:space:]]*$/d;N;ba' > "$TEMP_SETTINGS"
                    cat >> "$TEMP_SETTINGS" << DEVINSETTINGS
,
    "remote.devinDevContainers.dockerPath": "$HOME/.local/bin/docker",
    "docker.environment": {
        "DOCKER_HOST": "unix:///run/user/$(id -u)/podman/podman.sock"
    }
}
DEVINSETTINGS
                    mv "$TEMP_SETTINGS" "$DEVIN_SETTINGS"
                    echo "   ✅ Updated Devin settings for Podman (using docker wrapper)"
                fi
            else
                # Create new settings file
                cat > "$DEVIN_SETTINGS" << DEVINSETTINGS
{
    "remote.devinDevContainers.dockerPath": "$HOME/.local/bin/docker",
    "docker.environment": {
        "DOCKER_HOST": "unix:///run/user/$(id -u)/podman/podman.sock"
    }
}
DEVINSETTINGS
                echo "   ✅ Created Devin settings for Podman (using docker wrapper)"
            fi
        fi
        
        # Step 4: Create a local desktop file override for Devin with DOCKER_HOST
        DEVIN_DESKTOP_FILE=""
        for candidate in devin.desktop devin-desktop.desktop; do
            if [ -f "/usr/share/applications/$candidate" ]; then
                DEVIN_DESKTOP_FILE="$candidate"
                break
            fi
        done
        if [ -n "$DEVIN_DESKTOP_FILE" ]; then
            LOCAL_APPS_DIR="$HOME/.local/share/applications"
            mkdir -p "$LOCAL_APPS_DIR"
            
            # Create override that sets DOCKER_HOST before launching Devin
            cat > "$LOCAL_APPS_DIR/$DEVIN_DESKTOP_FILE" << DESKTOPEOF
[Desktop Entry]
Name=Devin
Comment=The AI Code Editor.
GenericName=Text Editor
Exec=env DOCKER_HOST=unix:///run/user/$(id -u)/podman/podman.sock /usr/bin/devin-desktop %F
Icon=devin
Type=Application
StartupNotify=false
StartupWMClass=Devin
Categories=TextEditor;Development;IDE;
MimeType=application/x-devin-workspace;
Actions=new-empty-window;
Keywords=devin;

[Desktop Action new-empty-window]
Name=New Empty Window
Exec=env DOCKER_HOST=unix:///run/user/$(id -u)/podman/podman.sock /usr/bin/devin-desktop --new-window %F
Icon=devin
DESKTOPEOF
            # Update desktop database
            update-desktop-database "$LOCAL_APPS_DIR" 2>/dev/null || true
            echo "   ✅ Created Devin desktop launcher with DOCKER_HOST"
        fi
        
        if [ "$PODMAN_SOCKET_SETUP_SUCCESS" = true ]; then
            echo "   ✅ Podman socket setup complete for Devin/VSCode"
            echo ""
            echo "   ⚠️  IMPORTANT: You may need to log out and back in, or reboot,"
            echo "      for the DOCKER_HOST environment variable to take effect in GUI apps."
            echo ""
        else
            echo "   ⚠️  Could not set up Podman socket automatically."
            echo "      You may need to run: systemctl --user enable --now podman.socket"
            echo ""
        fi
    fi
fi

# Create installation directory
INSTALL_DIR="$HOME/.venvoy/bin"
mkdir -p "$INSTALL_DIR"

# Ensure host home mount exists and is writable for container (/host-home)
HOST_HOME_DIR="$HOME/.venvoy/home"
if [ ! -d "$HOST_HOME_DIR" ]; then
    mkdir -p "$HOST_HOME_DIR"
fi
# Always ensure ownership and perms so the container can write
chown -R "$(id -u)":"$(id -g)" "$HOST_HOME_DIR" 2>/dev/null || true
chmod 755 "$HOST_HOME_DIR" 2>/dev/null || true

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
    # Detect if docker is actually Podman wrapper
    DOCKER_VERSION_OUT=$(docker --version 2>/dev/null || true)
    if echo "$DOCKER_VERSION_OUT" | grep -qi "podman"; then
        # docker command is a Podman shim; use Podman runtime
        CONTAINER_RUNTIME="podman"
    elif docker info &> /dev/null; then
        CONTAINER_RUNTIME="docker"
    elif command -v podman &> /dev/null; then
        # Docker is installed but not accessible, use Podman instead
        CONTAINER_RUNTIME="podman"
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
# Create ~/.venvoy/home directory for container mount
mkdir -p "$VENVOY_DIR/home"
chmod 755 "$VENVOY_DIR/home"

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

# Function to check if Devin is available
check_devin_available() {
    command -v devin-desktop &> /dev/null || \
    [ -f "/Applications/Devin.app/Contents/Resources/app/bin/devin-desktop" ] || \
    [ -f "$HOME/Applications/Devin.app/Contents/Resources/app/bin/devin-desktop" ] || \
    [ -f "/usr/bin/devin-desktop" ] || \
    [ -f "/usr/local/bin/devin-desktop" ] || \
    [ -f "$HOME/.local/bin/devin-desktop" ]
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
    if [ "$editor" = "devin" ]; then
        if command -v devin-desktop &> /dev/null; then
            echo "devin-desktop"
        elif [ -f "/Applications/Devin.app/Contents/Resources/app/bin/devin-desktop" ]; then
            echo "/Applications/Devin.app/Contents/Resources/app/bin/devin-desktop"
        elif [ -f "$HOME/Applications/Devin.app/Contents/Resources/app/bin/devin-desktop" ]; then
            echo "$HOME/Applications/Devin.app/Contents/Resources/app/bin/devin-desktop"
        elif [ -f "/usr/bin/devin-desktop" ]; then
            echo "/usr/bin/devin-desktop"
        elif [ -f "/usr/local/bin/devin-desktop" ]; then
            echo "/usr/local/bin/devin-desktop"
        elif [ -f "$HOME/.local/bin/devin-desktop" ]; then
            echo "$HOME/.local/bin/devin-desktop"
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
    # Check if --help is requested - if so, pass through to Python CLI
    if [ "$2" = "--help" ] || [ "$2" = "-h" ]; then
        # Pass through to Python CLI for help (will be handled below)
        :
    else
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

# Handle run command specially (unless --help is requested)
if [ "$1" = "run" ] && [ "$2" != "--help" ] && [ "$2" != "-h" ]; then
    # Parse run command arguments
    shift  # Remove 'run' from arguments
    RUN_NAME="venvoy-env"
    RUN_COMMAND=""
    RUN_MOUNTS=""
    
    # First pass: collect all options
    POSITIONAL_ARGS=()
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
            --help|-h)
                # Pass --help to the Python CLI
                shift
                break
                ;;
            --*)
                # Unknown option starting with --
                echo "Unknown option: $1"
                echo "Use 'venvoy run --help' for usage information"
                exit 1
                ;;
            *)
                # Collect positional arguments for second pass
                POSITIONAL_ARGS+=("$1")
                shift
                ;;
        esac
    done
    
    # Second pass: handle positional arguments (only if --name wasn't explicitly set)
    if [ ${#POSITIONAL_ARGS[@]} -gt 0 ]; then
        if [ "$RUN_NAME" = "venvoy-env" ]; then
            # Use first positional argument as name
            RUN_NAME="${POSITIONAL_ARGS[0]}"
            # If there are more positional args, that's an error
            if [ ${#POSITIONAL_ARGS[@]} -gt 1 ]; then
                echo "Unexpected argument: ${POSITIONAL_ARGS[1]}"
                echo "Use 'venvoy run --help' for usage information"
                exit 1
            fi
        else
            # --name was explicitly set, so positional args are unexpected
            echo "Unexpected argument: ${POSITIONAL_ARGS[0]}"
            echo "Cannot specify both --name and a positional argument for the environment name"
            echo "Use 'venvoy run --help' for usage information"
            exit 1
        fi
    fi
    
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
        # First, try to extract image_name directly from config (new format)
        IMAGE_NAME_RAW=$(grep "^image_name:" "$HOME/.venvoy/environments/$RUN_NAME/config.yaml" | head -1)
        IMAGE_NAME_FROM_CONFIG=$(echo "$IMAGE_NAME_RAW" | sed -E "s/^image_name:[[:space:]]*['\"]?([^'\"]+)['\"]?[[:space:]]*$/\1/" | tr -d '[:space:]')
        
        if [ -n "$IMAGE_NAME_FROM_CONFIG" ] && [ "$IMAGE_NAME_FROM_CONFIG" != "image_name" ]; then
            # Use image_name from config if available
            IMAGE_NAME="$IMAGE_NAME_FROM_CONFIG"
        else
            # Fall back to constructing from python_version and r_version
            # Extract python_version from YAML
            PYTHON_VERSION_RAW=$(grep "^python_version:" "$HOME/.venvoy/environments/$RUN_NAME/config.yaml" | head -1)
            PYTHON_VERSION=$(echo "$PYTHON_VERSION_RAW" | sed -E "s/^python_version:[[:space:]]*['\"]?([0-9]+\.[0-9]+)['\"]?[[:space:]]*$/\1/" | tr -d '[:space:]')
            
            # If that didn't work, try a more flexible pattern
            if [ -z "$PYTHON_VERSION" ] || [ "$PYTHON_VERSION" = "python_version" ] || ! echo "$PYTHON_VERSION" | grep -qE '^[0-9]+\.[0-9]+$'; then
                PYTHON_VERSION_RAW=$(grep "python_version:" "$HOME/.venvoy/environments/$RUN_NAME/config.yaml" | grep -v "^[[:space:]]" | head -1)
                PYTHON_VERSION=$(echo "$PYTHON_VERSION_RAW" | sed -E "s/.*python_version:[[:space:]]*['\"]?([0-9]+\.[0-9]+)['\"]?.*/\1/" | tr -d '[:space:]')
            fi
            
            # Extract r_version from YAML
            R_VERSION_RAW=$(grep "^r_version:" "$HOME/.venvoy/environments/$RUN_NAME/config.yaml" | head -1)
            R_VERSION=$(echo "$R_VERSION_RAW" | sed -E "s/^r_version:[[:space:]]*['\"]?([0-9]+\.[0-9]+)['\"]?[[:space:]]*$/\1/" | tr -d '[:space:]')
            
            # If r_version not found, try flexible pattern
            if [ -z "$R_VERSION" ] || [ "$R_VERSION" = "r_version" ] || ! echo "$R_VERSION" | grep -qE '^[0-9]+\.[0-9]+$'; then
                R_VERSION_RAW=$(grep "r_version:" "$HOME/.venvoy/environments/$RUN_NAME/config.yaml" | grep -v "^[[:space:]]" | head -1)
                R_VERSION=$(echo "$R_VERSION_RAW" | sed -E "s/.*r_version:[[:space:]]*['\"]?([0-9]+\.[0-9]+)['\"]?.*/\1/" | tr -d '[:space:]')
            fi
            
            # Final validation - must have python_version
            if [ -z "$PYTHON_VERSION" ] || ! echo "$PYTHON_VERSION" | grep -qE '^[0-9]+\.[0-9]+$'; then
                echo "❌ Could not extract python_version from config.yaml"
                echo "   Raw line: '$PYTHON_VERSION_RAW'"
                echo "   Extracted value: '$PYTHON_VERSION'"
                echo "💡 Try reinitializing the environment: venvoy init --name $RUN_NAME --force"
                exit 1
            fi
            
            # If r_version is missing, try to determine from python_version (backward compatibility)
            if [ -z "$R_VERSION" ] || ! echo "$R_VERSION" | grep -qE '^[0-9]+\.[0-9]+$'; then
                # Map Python version to default R version
                case "$PYTHON_VERSION" in
                    3.13) R_VERSION="4.5" ;;
                    3.12) R_VERSION="4.4" ;;
                    3.11) R_VERSION="4.3" ;;
                    3.10) R_VERSION="4.2" ;;
                    *)
                        echo "⚠️  Could not determine R version for Python $PYTHON_VERSION, defaulting to 4.3"
                        R_VERSION="4.3"
                        ;;
                esac
            fi
            
            # Construct combined image tag
            IMAGE_TAG="python${PYTHON_VERSION}-r${R_VERSION}"
            if [ "$CONTAINER_RUNTIME" = "podman" ]; then
                # Podman requires fully qualified image names
                IMAGE_NAME="docker.io/zaphodbeeblebrox3rd/venvoy:${IMAGE_TAG}"
            else
                IMAGE_NAME="zaphodbeeblebrox3rd/venvoy:${IMAGE_TAG}"
            fi
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
        # Podman requires fully qualified image names (docker.io/ prefix)
        # Normalize image name if it doesn't already have the prefix
        if [[ "$IMAGE_NAME" != docker.io/* ]] && [[ "$IMAGE_NAME" == */* ]]; then
            PULL_IMAGE_URI="docker.io/$IMAGE_NAME"
        else
            PULL_IMAGE_URI="$IMAGE_NAME"
        fi
    else
        PULL_IMAGE_URI="$IMAGE_NAME"
    fi
    
    # Validate image name format
    if [ -z "$IMAGE_NAME" ] || [ "$IMAGE_NAME" = "docker.io/zaphodbeeblebrox3rd/venvoy:" ] || [ "$IMAGE_NAME" = "zaphodbeeblebrox3rd/venvoy:" ]; then
        echo "❌ Invalid image name format: '$IMAGE_NAME'"
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
    DEVIN_AVAILABLE=false
    VSCODE_AVAILABLE=false
    if check_devin_available; then
        DEVIN_AVAILABLE=true
    elif check_vscode_available; then
        VSCODE_AVAILABLE=true
    fi
    
    # Determine container name for editor connection (use $$ for process ID to ensure uniqueness)
    CONTAINER_NAME="venvoy-${RUN_NAME}-$$"
    
    # Hex-encode the container name for the vscode-remote URI
    # VSCode Dev Containers expects the container name to be hex-encoded in the URI
    CONTAINER_NAME_HEX=$(echo -n "$CONTAINER_NAME" | xxd -p | tr -d '\n')
    # Devin's dev containers extension expects a hex-encoded JSON container config
    CONTAINER_CONFIG_HEX=$(echo -n "{\"containerId\":\"${CONTAINER_NAME}\"}" | xxd -p | tr -d '\n')
    
    # If editor is available and no custom command specified, launch editor
    if [ -z "$RUN_COMMAND" ] && { [ "$DEVIN_AVAILABLE" = true ] || [ "$VSCODE_AVAILABLE" = true ]; }; then
        # Determine which editor to use (prefer Devin)
        if [ "$DEVIN_AVAILABLE" = true ]; then
            EDITOR_TYPE="devin"
            EDITOR_CMD=$(get_editor_command "devin")
            # Devin Desktop resolves dev-container+<hex(JSON {"containerId": ...})>
            REMOTE_URI="vscode-remote://dev-container+${CONTAINER_CONFIG_HEX}/host-home"
        else
            EDITOR_TYPE="vscode"
            EDITOR_CMD=$(get_editor_command "vscode")
            REMOTE_URI="vscode-remote://attached-container+${CONTAINER_NAME_HEX}/host-home"
        fi
        
        echo "🚀 Starting container in background..."
        echo "🧠 Launching $EDITOR_TYPE connected to container..."
        echo ""
        
        # Start container in detached mode
        if [ "$CONTAINER_RUNTIME" = "docker" ]; then
            test_container_access "$CONTAINER_RUNTIME"
            # Run directly as host UID/GID to avoid su prompts; fix-host-home is unnecessary when using host IDs
            docker run -d --name "$CONTAINER_NAME" \
                --user "$(id -u):$(id -g)" \
                -v "$PWD:/workspace" \
                -v "$HOME/.venvoy/home:/host-home" \
                -w /home/venvoy \
                -e VENVOY_HOST_RUNTIME="$CONTAINER_RUNTIME" \
                -e VENVOY_HOST_HOME="/host-home" \
                -e HOST_UID="$HOST_UID" \
                -e HOST_GID="$HOST_GID" \
                $RUN_MOUNTS \
                "$IMAGE_NAME" sleep infinity || {
                    echo "❌ Failed to start container"
                    exit 1
                }
            
            # Wait a moment for container to be ready
            sleep 2
            
            # Launch editor connected to container
            if [ "$EDITOR_TYPE" = "devin" ]; then
                "$EDITOR_CMD" --folder-uri "${REMOTE_URI}" 2>/dev/null || {
                    echo "⚠️  Failed to launch Devin. Stopping container and falling back to shell..."
                    docker stop "$CONTAINER_NAME" >/dev/null 2>&1
                    docker rm "$CONTAINER_NAME" >/dev/null 2>&1
                    DEVIN_AVAILABLE=false
                    VSCODE_AVAILABLE=false
                }
            else
                "$EDITOR_CMD" --folder-uri "${REMOTE_URI}" 2>/dev/null || {
                    echo "⚠️  Failed to launch VSCode. Stopping container and falling back to shell..."
                    docker stop "$CONTAINER_NAME" >/dev/null 2>&1
                    docker rm "$CONTAINER_NAME" >/dev/null 2>&1
                    DEVIN_AVAILABLE=false
                    VSCODE_AVAILABLE=false
                }
            fi
            
            if [ "$DEVIN_AVAILABLE" = true ] || [ "$VSCODE_AVAILABLE" = true ]; then
                echo "✅ $EDITOR_TYPE connected to container!"
                echo "💡 Container is running in background: $CONTAINER_NAME"
                echo "💡 When you're done, stop the container with: venvoy exit --name $RUN_NAME"
                exit 0
            fi
        elif [ "$CONTAINER_RUNTIME" = "podman" ]; then
            # Podman: use --userns=keep-id to map host UID to same UID inside container
            podman run -d --name "$CONTAINER_NAME" \
                --userns=keep-id \
                -v "$PWD:/workspace" \
                -v "$HOME/.venvoy/home:/host-home" \
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
            
            # For Podman, Devin/VSCode Remote Containers needs Docker-compatible API
            # Priority order for socket detection:
            # 1. Systemd user socket (most reliable for Devin - set up during install)
            # 2. XDG_RUNTIME_DIR socket
            # 3. System Docker socket (if accessible)
            # 4. System Podman socket (if accessible)
            # 5. Fall back to manual socket setup
            DOCKER_HOST_SET=false
            XDG_RUNTIME_DIR="${XDG_RUNTIME_DIR:-/run/user/$(id -u)}"
            
            # First priority: Check systemd user podman socket (set up during install)
            SYSTEMD_USER_SOCKET="$XDG_RUNTIME_DIR/podman/podman.sock"
            if [ -S "$SYSTEMD_USER_SOCKET" ] && [ -r "$SYSTEMD_USER_SOCKET" ]; then
                export DOCKER_HOST="unix://$SYSTEMD_USER_SOCKET"
                DOCKER_HOST_SET=true
                echo "✅ Using systemd user Podman socket: $SYSTEMD_USER_SOCKET"
            # Second: Try to enable systemd user socket if not running
            elif command -v systemctl &> /dev/null && systemctl --user list-unit-files podman.socket &> /dev/null; then
                echo "🔧 Enabling systemd user podman socket..."
                if systemctl --user enable --now podman.socket 2>/dev/null; then
                    sleep 1
                    if [ -S "$SYSTEMD_USER_SOCKET" ] && [ -r "$SYSTEMD_USER_SOCKET" ]; then
                        export DOCKER_HOST="unix://$SYSTEMD_USER_SOCKET"
                        DOCKER_HOST_SET=true
                        echo "✅ Enabled and using systemd user Podman socket"
                    fi
                fi
            fi
            
            # Fallback: Check system sockets if user socket not available
            if [ "$DOCKER_HOST_SET" = false ]; then
                if [ -S "/var/run/docker.sock" ] && [ -r "/var/run/docker.sock" ]; then
                    export DOCKER_HOST="unix:///var/run/docker.sock"
                    DOCKER_HOST_SET=true
                    echo "✅ Using system Docker socket: /var/run/docker.sock"
                elif [ -S "/run/podman/podman.sock" ] && [ -r "/run/podman/podman.sock" ]; then
                    export DOCKER_HOST="unix:///run/podman/podman.sock"
                    DOCKER_HOST_SET=true
                    echo "✅ Using system Podman socket: /run/podman/podman.sock"
                elif command -v docker > /dev/null 2>&1 && docker --version 2>&1 | grep -qi podman; then
                    if docker info > /dev/null 2>&1; then
                        unset DOCKER_HOST
                        DOCKER_HOST_SET=true
                        echo "✅ Using podman-docker for Docker compatibility"
                    fi
                fi
            fi
            
            # Last resort: Start manual Podman API service
            if [ "$DOCKER_HOST_SET" = false ]; then
                PODMAN_SOCKET_DIR="$HOME/.local/share/containers/podman-socket"
                mkdir -p "$PODMAN_SOCKET_DIR"
                PODMAN_SOCKET="$PODMAN_SOCKET_DIR/podman.sock"
                
                if [ -S "$PODMAN_SOCKET" ] && [ -r "$PODMAN_SOCKET" ]; then
                    export DOCKER_HOST="unix://$PODMAN_SOCKET"
                    DOCKER_HOST_SET=true
                    echo "✅ Using existing user Podman socket: $PODMAN_SOCKET"
                else
                    if ! pgrep -f "podman system service.*$PODMAN_SOCKET" > /dev/null; then
                        echo "🔧 Starting Podman API service for Devin/VSCode..."
                        podman system service --time=0 unix://"$PODMAN_SOCKET" > /dev/null 2>&1 &
                        PODMAN_SERVICE_PID=$!
                        
                        for i in {1..10}; do
                            if [ -S "$PODMAN_SOCKET" ] && [ -r "$PODMAN_SOCKET" ]; then
                                break
                            fi
                            sleep 0.5
                        done
                        
                        if [ -S "$PODMAN_SOCKET" ] && [ -r "$PODMAN_SOCKET" ]; then
                            export DOCKER_HOST="unix://$PODMAN_SOCKET"
                            DOCKER_HOST_SET=true
                            echo "✅ Podman API service started: $PODMAN_SOCKET"
                        else
                            echo "⚠️  Warning: Podman API service socket not accessible"
                            echo "   Devin Remote Containers may not work properly"
                        fi
                    else
                        # Service is running, check if socket is accessible
                        if [ -S "$PODMAN_SOCKET" ] && [ -r "$PODMAN_SOCKET" ]; then
                            export DOCKER_HOST="unix://$PODMAN_SOCKET"
                            DOCKER_HOST_SET=true
                            echo "✅ Using existing Podman API service: $PODMAN_SOCKET"
                        fi
                    fi
                fi
            fi
            
            # Verify Docker/Podman access works with the selected socket
            if [ "$DOCKER_HOST_SET" = true ] || [ -z "$DOCKER_HOST" ]; then
                if DOCKER_HOST="${DOCKER_HOST:-}" docker inspect "$CONTAINER_NAME" > /dev/null 2>&1; then
                    echo "✅ Verified container access for Remote Containers"
                else
                    echo "⚠️  Warning: Cannot verify container access - Devin may have issues"
                    echo "   Attempting to fix socket permissions..."
                    
                    # Try to make socket accessible if it's a user socket
                    if [ -n "$DOCKER_HOST" ] && [ -S "${DOCKER_HOST#unix://}" ]; then
                        SOCKET_PATH="${DOCKER_HOST#unix://}"
                        if [ -w "$(dirname "$SOCKET_PATH")" ]; then
                            chmod 666 "$SOCKET_PATH" 2>/dev/null || true
                        fi
                    fi
                fi
            fi
            
            # For Devin/VSCode Remote Containers, we need to ensure the socket is accessible
            # Create a helper script that sets up the environment and launches the editor
            # This script ensures Devin can access Docker/Podman
            EDITOR_LAUNCHER=$(mktemp)
            cat > "$EDITOR_LAUNCHER" << EOFLAUNCHER
#!/bin/bash
# Launcher script for Devin/VSCode with proper Docker/Podman socket access
# This ensures the editor can run 'docker inspect' successfully

# Priority order for socket detection (same as main script):
# 1. Systemd user socket (most reliable)
# 2. System sockets
# 3. Manual socket

XDG_RUNTIME_DIR="\${XDG_RUNTIME_DIR:-/run/user/\$(id -u)}"
SYSTEMD_USER_SOCKET="\$XDG_RUNTIME_DIR/podman/podman.sock"

# First, check for systemd user socket (set up during venvoy install)
if [ -S "\$SYSTEMD_USER_SOCKET" ] && [ -r "\$SYSTEMD_USER_SOCKET" ]; then
    export DOCKER_HOST="unix://\$SYSTEMD_USER_SOCKET"
# Then try inherited DOCKER_HOST
elif [ -n "${DOCKER_HOST:-}" ]; then
    export DOCKER_HOST="${DOCKER_HOST}"
# Then try system sockets
elif [ -S "/var/run/docker.sock" ] && [ -r "/var/run/docker.sock" ]; then
    export DOCKER_HOST="unix:///var/run/docker.sock"
elif [ -S "/run/podman/podman.sock" ] && [ -r "/run/podman/podman.sock" ]; then
    export DOCKER_HOST="unix:///run/podman/podman.sock"
elif [ -S "\$HOME/.local/share/containers/podman-socket/podman.sock" ] && [ -r "\$HOME/.local/share/containers/podman-socket/podman.sock" ]; then
    export DOCKER_HOST="unix://\$HOME/.local/share/containers/podman-socket/podman.sock"
fi

# Final test - can we inspect the container?
if command -v docker > /dev/null 2>&1; then
    if ! docker inspect "${CONTAINER_NAME}" > /dev/null 2>&1; then
        echo "Warning: docker inspect failed for ${CONTAINER_NAME}" >&2
        echo "DOCKER_HOST=\${DOCKER_HOST:-<unset>}" >&2
        echo "This may cause Devin Remote Containers to fail" >&2
    fi
fi

# Launch the editor with the container URI (hex-encoded container name)
exec "$EDITOR_CMD" --folder-uri "${REMOTE_URI}" "\$@"
EOFLAUNCHER
            chmod +x "$EDITOR_LAUNCHER"
            
            # CRITICAL: Devin spawns child processes that run 'docker inspect'
            # These processes need access to the Podman socket
            # We check for the user socket first (most reliable), then fall back
            
            echo ""
            echo "🔍 Pre-flight check: Verifying Devin can access Docker/Podman..."
            
            SOCKET_ISSUE=false
            XDG_RUNTIME_DIR="${XDG_RUNTIME_DIR:-/run/user/$(id -u)}"
            SYSTEMD_USER_SOCKET="$XDG_RUNTIME_DIR/podman/podman.sock"
            
            if [ "$CONTAINER_RUNTIME" = "podman" ]; then
                # First, check if the systemd user socket is available (best option)
                if [ -S "$SYSTEMD_USER_SOCKET" ] && [ -r "$SYSTEMD_USER_SOCKET" ]; then
                    echo "✅ Systemd user Podman socket available: $SYSTEMD_USER_SOCKET"
                    # Test that docker inspect works with this socket
                    if DOCKER_HOST="unix://$SYSTEMD_USER_SOCKET" docker inspect "$CONTAINER_NAME" > /dev/null 2>&1; then
                        echo "✅ docker inspect works with user socket"
                    else
                        echo "⚠️  docker inspect failed with user socket"
                        SOCKET_ISSUE=true
                    fi
                else
                    echo "⚠️  Systemd user Podman socket not available"
                    echo "   Expected at: $SYSTEMD_USER_SOCKET"
                    
                    # Try to enable it
                    if command -v systemctl &> /dev/null; then
                        echo "   🔧 Attempting to enable systemd user podman socket..."
                        if systemctl --user enable --now podman.socket 2>/dev/null; then
                            sleep 1
                            if [ -S "$SYSTEMD_USER_SOCKET" ] && [ -r "$SYSTEMD_USER_SOCKET" ]; then
                                echo "   ✅ Socket enabled successfully!"
                            else
                                SOCKET_ISSUE=true
                            fi
                        else
                            echo "   ❌ Could not enable socket"
                            SOCKET_ISSUE=true
                        fi
                    else
                        SOCKET_ISSUE=true
                    fi
                    
                    # Fall back to checking system socket
                    if [ "$SOCKET_ISSUE" = true ]; then
                        if [ -S "/run/podman/podman.sock" ] && [ -r "/run/podman/podman.sock" ]; then
                            echo "   ✅ System Podman socket accessible"
                            SOCKET_ISSUE=false
                        elif [ -S "/var/run/docker.sock" ] && [ -r "/var/run/docker.sock" ]; then
                            echo "   ✅ Docker socket accessible"
                            SOCKET_ISSUE=false
                        fi
                    fi
                fi
            fi
            
            # Final test: docker inspect without explicitly setting DOCKER_HOST
            # This simulates what Devin's child processes will do
            if [ "$SOCKET_ISSUE" = false ]; then
                # Temporarily unset to test default behavior
                SAVED_DOCKER_HOST="${DOCKER_HOST:-}"
                unset DOCKER_HOST
                if docker inspect "$CONTAINER_NAME" > /dev/null 2>&1; then
                    echo "✅ docker inspect works without DOCKER_HOST"
                else
                    # Try with the user socket explicitly
                    if DOCKER_HOST="unix://$SYSTEMD_USER_SOCKET" docker inspect "$CONTAINER_NAME" > /dev/null 2>&1; then
                        echo "✅ docker inspect works with DOCKER_HOST set"
                        echo "   ⚠️  Note: Devin may still have issues if DOCKER_HOST is not in environment"
                        echo "   💡 If Devin fails, log out and back in to apply environment changes"
                    else
                        echo "❌ docker inspect FAILED"
                        SOCKET_ISSUE=true
                    fi
                fi
                # Restore
                if [ -n "$SAVED_DOCKER_HOST" ]; then
                    export DOCKER_HOST="$SAVED_DOCKER_HOST"
                fi
            fi
            
            # If there's a socket issue, provide guidance and offer alternatives
            if [ "$SOCKET_ISSUE" = true ]; then
                echo ""
                echo "⚠️  Socket access issue detected - Devin may fail!"
                echo ""
                echo "   🔧 RECOMMENDED FIXES (try in order):"
                echo ""
                echo "   1. Enable the systemd user podman socket:"
                echo "      systemctl --user enable --now podman.socket"
                echo ""
                echo "   2. Log out and back in to apply environment changes"
                echo ""
                echo "   3. If still failing, check if you need to restart after venvoy install"
                echo ""
                echo "   Alternative: Use interactive shell instead:"
                echo "      venvoy run --name $RUN_NAME --command /bin/bash"
                echo ""
                
                # Don't exit - let the user try anyway, maybe the launcher script will work
                echo "   Attempting to launch Devin anyway..."
            else
                echo "✅ All checks passed - Devin should work!"
            fi
            
            # Launch editor connected to container
            if [ "$EDITOR_TYPE" = "devin" ]; then
                # Launch Devin in background and capture any immediate errors
                "$EDITOR_LAUNCHER" > /tmp/devin-launch.log 2>&1 &
                DEVIN_PID=$!
                
                # Wait a moment to see if Devin starts successfully
                sleep 3
                
                # Check if Devin process is still running and if there were errors
                if ! kill -0 "$DEVIN_PID" 2>/dev/null; then
                    # Process died, check the log
                    if grep -qi "docker\|socket\|permission" /tmp/devin-launch.log 2>/dev/null; then
                        DEVIN_ERROR=1
                    fi
                fi
                
                # Also check if Devin window opened (heuristic: check for devin processes)
                if ! pgrep -f "[Dd]evin" > /dev/null 2>&1; then
                    sleep 2  # Give it more time
                    if ! pgrep -f "[Dd]evin" > /dev/null 2>&1; then
                        DEVIN_ERROR=1
                    fi
                fi
                
                # Clean up launcher
                rm -f "$EDITOR_LAUNCHER"
                
                # Check if Devin launched successfully
                if [ "${DEVIN_ERROR:-0}" = "1" ]; then
                    echo ""
                    echo "⚠️  Failed to launch Devin with Remote Containers extension."
                    echo ""
                    if [ "$CONTAINER_RUNTIME" = "podman" ]; then
                        echo "💡 Devin's Remote Containers extension requires Docker-compatible API."
                        echo ""
                        echo "   The issue: Devin tries to run 'docker inspect' but it fails with Podman."
                        echo ""
                        echo "   ⚠️  RECOMMENDED SOLUTION: Install podman-docker"
                        echo "   This makes the 'docker' command work with Podman automatically:"
                        echo ""
                        echo "      sudo apt install podman-docker    # Debian/Ubuntu"
                        echo "      sudo dnf install podman-docker    # Fedora/RHEL"
                        echo "      sudo pacman -S podman-docker      # Arch Linux"
                        echo ""
                        echo "   After installing, restart Devin and try again."
                        echo ""
                        echo "   Alternative solutions (if podman-docker not available):"
                        echo "   1. Make Podman socket accessible (if using system socket):"
                        echo "      sudo chmod 666 /run/podman/podman.sock"
                        echo ""
                        echo "   2. Set DOCKER_HOST in your shell profile:"
                        if [ -n "${DOCKER_HOST:-}" ]; then
                            echo "      Add to ~/.bashrc or ~/.zshrc:"
                            echo "      export DOCKER_HOST=\"${DOCKER_HOST}\""
                        else
                            echo "      export DOCKER_HOST=\"unix://\$HOME/.local/share/containers/podman-socket/podman.sock\""
                        fi
                        echo "      Then restart Devin from a new terminal."
                        echo ""
                        echo "   3. Use interactive shell instead:"
                        echo "      venvoy run --name $RUN_NAME --command /bin/bash"
                    else
                        echo "💡 Make sure Docker is running and accessible:"
                        echo "      sudo systemctl start docker"
                        echo "      sudo usermod -aG docker $USER  # then log out and back in"
                    fi
                    echo ""
                    echo "Stopping container and falling back to shell..."
                    podman stop "$CONTAINER_NAME" >/dev/null 2>&1
                    podman rm "$CONTAINER_NAME" >/dev/null 2>&1
                    DEVIN_AVAILABLE=false
                    VSCODE_AVAILABLE=false
                fi
            else
                # VSCode - use the same launcher approach
                "$EDITOR_LAUNCHER" > /tmp/vscode-launch.log 2>&1 &
                VSCODE_PID=$!
                
                sleep 3
                
                if ! kill -0 "$VSCODE_PID" 2>/dev/null; then
                    if grep -qi "docker\|socket\|permission" /tmp/vscode-launch.log 2>/dev/null; then
                        VSCODE_ERROR=1
                    fi
                fi
                
                if ! pgrep -f "[Cc]ode" > /dev/null 2>&1; then
                    sleep 2
                    if ! pgrep -f "[Cc]ode" > /dev/null 2>&1; then
                        VSCODE_ERROR=1
                    fi
                fi
                
                rm -f "$EDITOR_LAUNCHER"
                
                if [ "${VSCODE_ERROR:-0}" = "1" ]; then
                    echo ""
                    echo "⚠️  Failed to launch VSCode with Remote Containers extension."
                    echo ""
                    if [ "$CONTAINER_RUNTIME" = "podman" ]; then
                        echo "💡 VSCode's Remote Containers extension requires Docker-compatible API."
                        echo ""
                        echo "   Solutions:"
                        echo "   1. Install podman-docker for compatibility:"
                        echo "      sudo apt install podman-docker  # or equivalent for your distro"
                        echo ""
                        echo "   2. Or ensure Podman socket is accessible:"
                        echo "      sudo chmod 666 /run/podman/podman.sock  # if using system socket"
                        echo ""
                        echo "   3. Or use the interactive shell instead:"
                        echo "      venvoy run --name $RUN_NAME --command /bin/bash"
                    else
                        echo "💡 Make sure Docker is running and accessible:"
                        echo "      sudo systemctl start docker"
                        echo "      sudo usermod -aG docker $USER  # then log out and back in"
                    fi
                    echo ""
                    echo "Stopping container and falling back to shell..."
                    podman stop "$CONTAINER_NAME" >/dev/null 2>&1
                    podman rm "$CONTAINER_NAME" >/dev/null 2>&1
                    DEVIN_AVAILABLE=false
                    VSCODE_AVAILABLE=false
                fi
            fi
            
            if [ "$DEVIN_AVAILABLE" = true ] || [ "$VSCODE_AVAILABLE" = true ]; then
                echo "✅ $EDITOR_TYPE connected to container!"
                echo "💡 Container is running in background: $CONTAINER_NAME"
                echo "💡 When you're done, stop the container with: venvoy exit --name $RUN_NAME"
                exit 0
            fi
        fi
        # If we get here, editor launch failed, fall through to shell
    fi
    
    # No editor available or editor launch failed - use interactive shell
    echo "🚀 Starting container..."
    if [ "$DEVIN_AVAILABLE" = false ] && [ "$VSCODE_AVAILABLE" = false ]; then
        echo "   No editor detected - launching interactive shell..."
    else
        echo "   Editor launch failed - falling back to interactive shell..."
    fi
    echo ""
    
    # Run the environment with interactive shell
    # Start in /home/venvoy (container's home) - users can cd to /workspace for their project
    if [ "$CONTAINER_RUNTIME" = "docker" ]; then
        test_container_access "$CONTAINER_RUNTIME"
        # Run directly as host UID/GID to avoid su/pam issues
        docker run --rm -it \
            --user "$(id -u):$(id -g)" \
            -v "$PWD:/workspace" \
            -v "$HOME/.venvoy/home:/host-home" \
            -w /home/venvoy \
            -e VENVOY_HOST_RUNTIME="$CONTAINER_RUNTIME" \
            -e VENVOY_HOST_HOME="/host-home" \
            -e HOST_UID="$HOST_UID" \
            -e HOST_GID="$HOST_GID" \
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
            --bind "$HOME/.venvoy/home:/host-home" \
            --pwd /home/venvoy \
            --env VENVOY_HOST_RUNTIME="$CONTAINER_RUNTIME" \
            --env VENVOY_HOST_HOME="/host-home" \
            $RUN_MOUNTS \
            "$IMAGE_URI" ${RUN_COMMAND:-bash}
    elif [ "$CONTAINER_RUNTIME" = "podman" ]; then
        # Podman: use --userns=keep-id to map host UID to same UID inside container
        podman run --rm -it \
            --userns=keep-id \
            -v "$PWD:/workspace" \
            -v "$HOME/.venvoy/home:/host-home" \
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

# Handle uninstall command specially (unless --help is requested)
if [ "$1" = "uninstall" ] && [ "$2" != "--help" ] && [ "$2" != "-h" ]; then
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
    # Check if venvoy is installed as a Python package on the host
    # If so, use that instead of running inside a container
    if command -v python3 &> /dev/null; then
        if python3 -c "import venvoy.cli" 2>/dev/null; then
            # venvoy is installed as a Python package - use it directly on the host
            python3 -c "from venvoy.cli import main; main()" "$@"
            exit $?
        fi
    fi
    
    # Check if we're in a venvoy development directory and can run it directly
    if [[ "$USE_LOCAL_CODE" = true ]]; then
        VENVOY_SOURCE_DIR="$(pwd)"
        if [[ -f "$VENVOY_SOURCE_DIR/src/venvoy/cli.py" ]] && command -v python3 &> /dev/null; then
            # We have the source code and Python - run it directly on the host
            echo "🔧 Using local venvoy development code from $VENVOY_SOURCE_DIR"
            
            # Check if dependencies are installed, install if missing
            # Check core dependencies: yaml (from pyyaml), click, rich, requests
            if ! python3 -c "import yaml, click, rich, requests" 2>/dev/null; then
                echo "📦 Installing venvoy dependencies for development..."
                if [[ -f "$VENVOY_SOURCE_DIR/requirements.txt" ]]; then
                    python3 -m pip install --user -q -r "$VENVOY_SOURCE_DIR/requirements.txt" || {
                        echo "⚠️  Failed to install dependencies. Trying with pip3..."
                        pip3 install --user -q -r "$VENVOY_SOURCE_DIR/requirements.txt" || {
                            echo "❌ Failed to install dependencies. Please install manually:"
                            echo "   pip install -r $VENVOY_SOURCE_DIR/requirements.txt"
                            exit 1
                        }
                    }
                else
                    echo "⚠️  requirements.txt not found. Installing core dependencies..."
                    python3 -m pip install --user -q pyyaml click docker rich packaging requests || {
                        pip3 install --user -q pyyaml click docker rich packaging requests || {
                            echo "❌ Failed to install dependencies. Please install manually:"
                            echo "   pip install pyyaml click docker rich packaging requests"
                            exit 1
                        }
                    }
                fi
                echo "✅ Dependencies installed"
            fi
            
            export PYTHONPATH="$VENVOY_SOURCE_DIR/src:$PYTHONPATH"
            python3 -c "import sys; sys.path.insert(0, '$VENVOY_SOURCE_DIR/src'); from venvoy.cli import main; main()" "$@"
            exit $?
        fi
    fi
    
    # Fall back to container execution only if Python/venvoy isn't available on host
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
    
    # Run normal venvoy commands inside the container with mounted source (fallback only)
    if [ "$CONTAINER_RUNTIME" = "docker" ]; then
        # Docker execution with source code mounted
        test_container_access "$CONTAINER_RUNTIME"
        docker run --rm -it \
            --user "$HOST_UID:$HOST_GID" \
            -v "$PWD:/workspace" \
            -v "$HOME/.venvoy/home:/host-home" \
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
            --bind "$HOME/.venvoy/home:/host-home" \
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
            -v "$HOME/.venvoy/home:/host-home" \
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
        echo "      • Improved container runtime selection and handling"
        echo "      • New export wheelhouse option for full offline support of multi-architecture image archive independent of repository availability"
        echo "      • Removal of dependency on conda"
    fi
    echo "   1. Run: venvoy init --python-version <python-version> --name <environment-name>"
    echo "   2. Run: venvoy run --name <environment-name>"
    echo "      (This will automatically launch Devin/VSCode if available)"
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
        echo "      • Improved container runtime selection and handling"
        echo "      • New export wheelhouse option for full offline support of multi-architecture image archive independent of repository availability"
        echo "      • Removal of dependency on conda"
    fi
    echo "   1. Run: venvoy init --python-version <python-version> --name <environment-name>"
    echo "   2. Run: venvoy run --name <environment-name>"
    echo "      (This will automatically launch Devin/VSCode if available)"
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