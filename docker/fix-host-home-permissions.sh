#!/bin/bash
# Fix permissions on /host-home mount point
# This script runs as root (via sudo or in an entrypoint) to fix permissions
# on the /host-home mount point so the container user can access it

# Get the current user's UID and GID
CURRENT_UID=${SUDO_UID:-$(id -u)}
CURRENT_GID=${SUDO_GID:-$(id -g)}

# If /host-home exists and is mounted, fix its permissions
if [ -d /host-home ] && mountpoint -q /host-home 2>/dev/null; then
    # Change ownership to match the current user
    chown -R "${CURRENT_UID}:${CURRENT_GID}" /host-home 2>/dev/null || true
    # Ensure directory is accessible
    chmod 755 /host-home 2>/dev/null || true
fi

