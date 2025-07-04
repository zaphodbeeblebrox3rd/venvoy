#!/bin/bash
# venvoy macOS PATH Diagnostic Script

echo "🔍 venvoy macOS PATH Diagnostic"
echo "================================"

# Check current shell
echo "📋 Current shell information:"
echo "   SHELL: $SHELL"
echo "   ZSH_VERSION: $ZSH_VERSION"
echo "   BASH_VERSION: $BASH_VERSION"

# Check for venvoy in various locations
echo ""
echo "🔍 Checking for venvoy installation:"

# Check pipx installation
if command -v pipx &> /dev/null; then
    echo "✅ pipx is installed"
    if pipx list | grep -q venvoy; then
        echo "✅ venvoy is installed via pipx"
        pipx list | grep venvoy
    else
        echo "❌ venvoy is NOT installed via pipx"
    fi
else
    echo "❌ pipx is not installed"
fi

# Check bootstrap script
BOOTSTRAP_PATH="$HOME/.venvoy/bin/venvoy"
if [ -f "$BOOTSTRAP_PATH" ]; then
    echo "✅ Bootstrap script exists at: $BOOTSTRAP_PATH"
    if [ -x "$BOOTSTRAP_PATH" ]; then
        echo "✅ Bootstrap script is executable"
    else
        echo "❌ Bootstrap script is NOT executable"
    fi
else
    echo "❌ Bootstrap script NOT found at: $BOOTSTRAP_PATH"
fi

# Check system-wide symlink
if [ -L "/usr/local/bin/venvoy" ]; then
    echo "✅ System-wide symlink exists at: /usr/local/bin/venvoy"
    echo "   Points to: $(readlink /usr/local/bin/venvoy)"
else
    echo "❌ System-wide symlink NOT found at: /usr/local/bin/venvoy"
fi

# Check PATH
echo ""
echo "🔍 Current PATH analysis:"
echo "   Current PATH: $PATH"

# Check if venvoy directories are in PATH
VENVOY_DIRS=(
    "$HOME/.venvoy/bin"
    "$HOME/.local/bin"
    "/usr/local/bin"
)

for dir in "${VENVOY_DIRS[@]}"; do
    if [[ ":$PATH:" == *":$dir:"* ]]; then
        echo "✅ $dir is in PATH"
    else
        echo "❌ $dir is NOT in PATH"
    fi
done

# Check shell configuration files
echo ""
echo "🔍 Shell configuration files:"

SHELL_FILES=(
    "$HOME/.zshrc"
    "$HOME/.bashrc"
    "$HOME/.bash_profile"
    "$HOME/.profile"
    "$HOME/.config/fish/config.fish"
)

for file in "${SHELL_FILES[@]}"; do
    if [ -f "$file" ]; then
        echo "📄 $file exists"
        if grep -q "venvoy" "$file" 2>/dev/null; then
            echo "   ✅ Contains venvoy configuration"
            grep -n "venvoy" "$file" | head -3
        else
            echo "   ❌ No venvoy configuration found"
        fi
    else
        echo "📄 $file does not exist"
    fi
done

# Try to find venvoy executable
echo ""
echo "🔍 Searching for venvoy executable:"
if command -v venvoy &> /dev/null; then
    echo "✅ 'which venvoy' found: $(which venvoy)"
else
    echo "❌ 'which venvoy' not found"
    
    # Search in common locations
    echo "🔍 Searching in common locations:"
    for dir in "${VENVOY_DIRS[@]}"; do
        if [ -f "$dir/venvoy" ]; then
            echo "   ✅ Found at: $dir/venvoy"
        fi
    done
    
    # Search with find
    echo "🔍 Searching with find:"
    find "$HOME" -name "venvoy" -type f -executable 2>/dev/null | head -5
fi

# Check if we can run venvoy directly
echo ""
echo "🔍 Testing direct execution:"

# Try bootstrap script
if [ -x "$BOOTSTRAP_PATH" ]; then
    echo "Testing bootstrap script..."
    if "$BOOTSTRAP_PATH" --help &> /dev/null; then
        echo "✅ Bootstrap script works"
    else
        echo "❌ Bootstrap script failed"
    fi
fi

# Try pipx
if command -v pipx &> /dev/null && pipx list | grep -q venvoy; then
    echo "Testing pipx execution..."
    if pipx run venvoy --help &> /dev/null; then
        echo "✅ pipx execution works"
    else
        echo "❌ pipx execution failed"
    fi
fi

echo ""
echo "💡 Recommendations:"
echo "1. If venvoy is installed via pipx but not in PATH, try:"
echo "   source ~/.zshrc  # or ~/.bashrc"
echo "2. If bootstrap script exists but not in PATH, add to shell config:"
echo "   export PATH=\"\$HOME/.venvoy/bin:\$PATH\""
echo "3. If nothing works, reinstall with:"
echo "   curl -fsSL https://raw.githubusercontent.com/zaphodbeeblebrox3rd/venvoy/main/install.sh | bash" 