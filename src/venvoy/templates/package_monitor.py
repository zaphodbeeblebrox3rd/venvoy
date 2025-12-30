#!/usr/bin/env python3
"""
Package Monitor for venvoy containers

This script runs inside the container and monitors for package changes,
triggering auto-saves of environment.yml when packages are installed/removed.
"""

import os
import sys
import time
import json
import subprocess
from pathlib import Path
from datetime import datetime


def get_installed_packages():
    """Get current list of installed packages"""
    try:
        result = subprocess.run([
            'pip', 'freeze'
        ], capture_output=True, text=True, check=True)

        packages = {}
        for line in result.stdout.strip().split('\n'):
            if line and '==' in line:
                name, version = line.split('==', 1)
                packages[name] = version

        return packages
    except subprocess.CalledProcessError:
        return {}


def save_package_state(packages, state_file):
    """Save current package state to file"""
    with open(state_file, 'w') as f:
        json.dump(packages, f, indent=2)


def load_package_state(state_file):
    """Load previous package state from file"""
    if not state_file.exists():
        return {}

    try:
        with open(state_file, 'r') as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return {}


def trigger_environment_save():
    """Signal the host to save environment.yml"""
    # Create a signal file that the host can monitor
    signal_file = Path('/tmp/venvoy_package_changed')
    with open(signal_file, 'w') as f:
        f.write(datetime.now().isoformat())

    print("📦 Package change detected - signaling environment save")


def monitor_packages():
    """Monitor for package changes"""
    state_file = Path('/tmp/venvoy_package_state.json')

    # Get initial state
    current_packages = get_installed_packages()
    save_package_state(current_packages, state_file)

    print("🔍 Starting package monitor...")
    print(f"📊 Monitoring {len(current_packages)} initial packages")

    while True:
        time.sleep(5)  # Check every 5 seconds

        new_packages = get_installed_packages()

        # Compare with previous state
        if new_packages != current_packages:
            # Find what changed
            added = set(new_packages.keys()) - set(current_packages.keys())
            removed = set(current_packages.keys()) - set(new_packages.keys())
            updated = {
                pkg for pkg in new_packages.keys() & current_packages.keys()
                if new_packages[pkg] != current_packages[pkg]
            }

            if added:
                print(f"➕ Added packages: {', '.join(added)}")
            if removed:
                print(f"➖ Removed packages: {', '.join(removed)}")
            if updated:
                print(f"🔄 Updated packages: {', '.join(updated)}")

            # Trigger environment save
            trigger_environment_save()

            # Update state
            current_packages = new_packages
            save_package_state(current_packages, state_file)


if __name__ == "__main__":
    # Run in background if requested
    if len(sys.argv) > 1 and sys.argv[1] == '--daemon':
        # Fork to background
        try:
            pid = os.fork()
            if pid > 0:
                sys.exit(0)  # Parent exits
        except OSError:
            pass  # Windows doesn't support fork

    try:
        monitor_packages()
    except KeyboardInterrupt:
        print("\n🛑 Package monitor stopped")
    except Exception as e:
        print(f"❌ Package monitor error: {e}")
