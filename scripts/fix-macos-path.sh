#!/bin/bash
# venvoy macOS PATH Fix Script

echo "🔧 venvoy macOS PATH Fix"
echo "========================"

# Detect shell
SHELL_RC=""
if [[ -n "$ZSH_VERSION" ]] || [[ "$SHELL" == *"zsh"* ]]; then
    SHELL_RC="$HOME/.zshrc"
    echo "📋 Detected zsh shell, using: $SHELL_RC"
elif [[ -n "$BASH_VERSION" ]] || [[ "$SHELL" == *"bash"* ]]; then
    SHELL_RC="$HOME/.bashrc"
    echo "📋 Detected bash shell, using: $SHELL_RC"
else
    SHELL_RC="$HOME/.zshrc"  # Default to zsh on macOS
    echo "📋 Defaulting to zsh config: $SHELL_RC"
fi

# Check if venvoy is installed via pipx
if command -v pipx &> /dev/null && pipx list | grep -q venvoy; then
    echo "✅ venvoy is installed via pipx"
    
    # Ensure ~/.local/bin is in PATH
    if [[ ":$PATH:" != *":$HOME/.local/bin:"* ]]; then
        echo "📝 Adding ~/.local/bin to PATH in $SHELL_RC"
        
        # Create shell RC file if it doesn't exist
        touch "$SHELL_RC"
        
        # Add to shell config if not already there
        if ! grep -q "$HOME/.local/bin" "$SHELL_RC" 2>/dev/null; then
            echo "" >> "$SHELL_RC"
            echo "# Added by venvoy path fix" >> "$SHELL_RC"
            echo "export PATH=\"\$HOME/.local/bin:\$PATH\"" >> "$SHELL_RC"
            echo "✅ Added ~/.local/bin to $SHELL_RC"
        else
            echo "✅ ~/.local/bin already in $SHELL_RC"
        fi
        
        # Add to current session
        export PATH="$HOME/.local/bin:$PATH"
        echo "✅ Added ~/.local/bin to current session PATH"
    else
        echo "✅ ~/.local/bin already in PATH"
    fi
fi

# Check if bootstrap script exists
BOOTSTRAP_PATH="$HOME/.venvoy/bin/venvoy"
if [ -f "$BOOTSTRAP_PATH" ]; then
    echo "✅ Bootstrap script found at: $BOOTSTRAP_PATH"
    
    # Ensure bootstrap directory is in PATH
    if [[ ":$PATH:" != *":$HOME/.venvoy/bin:"* ]]; then
        echo "📝 Adding ~/.venvoy/bin to PATH in $SHELL_RC"
        
        # Create shell RC file if it doesn't exist
        touch "$SHELL_RC"
        
        # Add to shell config if not already there
        if ! grep -q "$HOME/.venvoy/bin" "$SHELL_RC" 2>/dev/null; then
            echo "" >> "$SHELL_RC"
            echo "# Added by venvoy path fix" >> "$SHELL_RC"
            echo "export PATH=\"\$HOME/.venvoy/bin:\$PATH\"" >> "$SHELL_RC"
            echo "✅ Added ~/.venvoy/bin to $SHELL_RC"
        else
            echo "✅ ~/.venvoy/bin already in $SHELL_RC"
        fi
        
        # Add to current session
        export PATH="$HOME/.venvoy/bin:$PATH"
        echo "✅ Added ~/.venvoy/bin to current session PATH"
    else
        echo "✅ ~/.venvoy/bin already in PATH"
    fi
fi

# Create system-wide symlink if possible
if [ -w "/usr/local/bin" ] && [ -f "$BOOTSTRAP_PATH" ]; then
    if [ ! -L "/usr/local/bin/venvoy" ]; then
        echo "📝 Creating system-wide symlink in /usr/local/bin"
        ln -sf "$BOOTSTRAP_PATH" "/usr/local/bin/venvoy"
        echo "✅ Created symlink: /usr/local/bin/venvoy -> $BOOTSTRAP_PATH"
    else
        echo "✅ System-wide symlink already exists"
    fi
fi

# Test if venvoy is now available
echo ""
echo "🔍 Testing venvoy availability:"
if command -v venvoy &> /dev/null; then
    echo "✅ venvoy is now available at: $(which venvoy)"
    echo "🚀 Testing venvoy command..."
    if venvoy --help &> /dev/null; then
        echo "✅ venvoy command works!"
    else
        echo "❌ venvoy command failed"
    fi
else
    echo "❌ venvoy still not found in PATH"
    echo ""
    echo "💡 Try these steps:"
    echo "1. Restart your terminal"
    echo "2. Or run: source $SHELL_RC"
    echo "3. Or run: export PATH=\"\$HOME/.local/bin:\$HOME/.venvoy/bin:\$PATH\""
fi

echo ""
echo "📋 Summary of changes:"
echo "   Shell config: $SHELL_RC"
echo "   Bootstrap script: $BOOTSTRAP_PATH"
if [ -L "/usr/local/bin/venvoy" ]; then
    echo "   System symlink: /usr/local/bin/venvoy"
fi
echo ""
echo "💡 Next steps:"
echo "1. Restart your terminal or run: source $SHELL_RC"
echo "2. Test with: venvoy --help" 