#!/bin/bash
# venvoy Uninstaller
# Removes venvoy installation and cleans up PATH entries

set -e

echo "🗑️  venvoy Uninstaller"
echo "===================="

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

INSTALL_DIR="$HOME/.venvoy/bin"
VENVOY_DIR="$HOME/.venvoy"
PROJECTS_DIR="$HOME/venvoy-projects"

# Confirm uninstallation
echo ""
echo "This will remove:"
echo "  📁 Installation directory: $INSTALL_DIR"
echo "  📁 Configuration directory: $VENVOY_DIR"
echo "  📁 Projects directory: $PROJECTS_DIR"
echo "  🔗 PATH entries in shell configuration files"
echo "  🐳 Docker images (venvoy/bootstrap:latest and venvoy/* images)"
echo ""

read -p "Are you sure you want to uninstall venvoy? (y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "❌ Uninstallation cancelled"
    exit 0
fi

echo ""
echo "🗑️  Removing venvoy..."

# Remove installation directory
if [[ -d "$INSTALL_DIR" ]]; then
    rm -rf "$INSTALL_DIR"
    echo "✅ Removed installation directory"
fi

# Remove configuration directory
if [[ -d "$VENVOY_DIR" ]]; then
    rm -rf "$VENVOY_DIR"
    echo "✅ Removed configuration directory"
fi

# Ask about projects directory
if [[ -d "$PROJECTS_DIR" ]]; then
    echo ""
    read -p "Remove projects directory with environment exports? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        rm -rf "$PROJECTS_DIR"
        echo "✅ Removed projects directory"
    else
        echo "📁 Kept projects directory: $PROJECTS_DIR"
    fi
fi

# Remove PATH entries from shell configuration files
case $PLATFORM in
    linux|macos)
        # Check common shell configuration files
        SHELL_FILES=(
            "$HOME/.bashrc"
            "$HOME/.zshrc" 
            "$HOME/.config/fish/config.fish"
            "$HOME/.profile"
            "$HOME/.bash_profile"
        )
        
        for SHELL_FILE in "${SHELL_FILES[@]}"; do
            if [[ -f "$SHELL_FILE" ]] && grep -q "$INSTALL_DIR" "$SHELL_FILE" 2>/dev/null; then
                # Create backup
                cp "$SHELL_FILE" "$SHELL_FILE.venvoy-backup"
                
                # Remove venvoy PATH entries
                sed -i.tmp '/# Added by venvoy installer/,+2d' "$SHELL_FILE" 2>/dev/null || true
                sed -i.tmp "\|$INSTALL_DIR|d" "$SHELL_FILE" 2>/dev/null || true
                rm -f "$SHELL_FILE.tmp" 2>/dev/null || true
                
                echo "✅ Cleaned PATH from $SHELL_FILE"
                echo "   📋 Backup saved as: $SHELL_FILE.venvoy-backup"
            fi
        done
        
        # Remove system-wide symlink if it exists
        if [[ -L "/usr/local/bin/venvoy" ]]; then
            rm -f "/usr/local/bin/venvoy" 2>/dev/null || true
            echo "✅ Removed system-wide symlink"
        fi
        ;;
esac

# Remove Docker images
echo ""
echo "🐳 Cleaning up Docker images..."

# Remove bootstrap image
if docker image inspect venvoy/bootstrap:latest &> /dev/null; then
    docker rmi venvoy/bootstrap:latest
    echo "✅ Removed bootstrap image"
fi

# Remove venvoy environment images
VENVOY_IMAGES=$(docker images --format "table {{.Repository}}:{{.Tag}}" | grep "^venvoy/" | grep -v "bootstrap" || true)
if [[ -n "$VENVOY_IMAGES" ]]; then
    echo "Found venvoy environment images:"
    echo "$VENVOY_IMAGES"
    echo ""
    read -p "Remove all venvoy environment images? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "$VENVOY_IMAGES" | while read -r image; do
            if [[ -n "$image" ]]; then
                docker rmi "$image" 2>/dev/null || true
            fi
        done
        echo "✅ Removed venvoy environment images"
    fi
fi

# Remove stopped containers
VENVOY_CONTAINERS=$(docker ps -a --format "table {{.Names}}" | grep "venvoy\|bootstrap" || true)
if [[ -n "$VENVOY_CONTAINERS" ]]; then
    echo "$VENVOY_CONTAINERS" | while read -r container; do
        if [[ -n "$container" && "$container" != "NAMES" ]]; then
            docker rm "$container" 2>/dev/null || true
        fi
    done
    echo "✅ Removed venvoy containers"
fi

echo ""
echo "🎉 venvoy uninstalled successfully!"
echo ""
echo "📋 Next steps:"
echo "   1. Restart your terminal to update PATH"
echo "   2. Remove any remaining Docker volumes manually if needed:"
echo "      docker volume ls | grep venvoy"
echo ""
echo "💡 To reinstall venvoy later, run the installer again" 