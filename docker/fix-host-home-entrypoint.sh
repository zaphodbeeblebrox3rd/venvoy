#!/bin/bash
# Entrypoint script to fix /host-home permissions before running command
# This runs as the container user (via --user) but uses sudo if available to fix permissions

# Function to fix permissions if we have sudo access
fix_permissions() {
    # Check if we're running as root (shouldn't happen with --user, but check anyway)
    if [ "$(id -u)" = "0" ]; then
        # Running as root, can fix permissions directly
        if [ -d /host-home ] && mountpoint -q /host-home 2>/dev/null; then
            # Get the user's UID/GID from environment or current user
            TARGET_UID=${HOST_UID:-$(stat -c '%u' /host-home 2>/dev/null || echo "1000")}
            TARGET_GID=${HOST_GID:-$(stat -c '%g' /host-home 2>/dev/null || echo "1000")}
            chown -R "${TARGET_UID}:${TARGET_GID}" /host-home 2>/dev/null || true
            chmod 755 /host-home 2>/dev/null || true
        fi
    elif command -v sudo >/dev/null 2>&1 && sudo -n true 2>/dev/null; then
        # Have sudo access, use it to fix permissions
        if [ -d /host-home ] && mountpoint -q /host-home 2>/dev/null; then
            TARGET_UID=${HOST_UID:-$(id -u)}
            TARGET_GID=${HOST_GID:-$(id -g)}
            sudo chown -R "${TARGET_UID}:${TARGET_GID}" /host-home 2>/dev/null || true
            sudo chmod 755 /host-home 2>/dev/null || true
        fi
    fi
}

# Try to fix permissions (may not work if no sudo, but that's okay)
fix_permissions

# Execute the original command
exec "$@"

