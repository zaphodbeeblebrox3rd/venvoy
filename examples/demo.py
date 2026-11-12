#!/usr/bin/env python3
"""
Demo script showing venvoy capabilities
"""

import sys
import platform
from pathlib import Path

def main():
    """Demonstrate venvoy environment"""
    print("🚀 Welcome to AI-powered venvoy demo!")
    print("=" * 60)
    
    # Show Python information
    print(f"🐍 Python Version: {sys.version}")
    print(f"🏠 Python Executable: {sys.executable}")
    print(f"📍 Platform: {platform.platform()}")
    print(f"🏗️  Architecture: {platform.machine()}")
    
    # Show environment information
    print("\n📂 Environment Information:")
    print(f"   Current Directory: {Path.cwd()}")
    print(f"   Home Directory: {Path.home()}")
    
    # Show if we're in a container
    if Path("/.dockerenv").exists():
        print("🐳 Running inside AI-ready Docker container!")
    else:
        print("💻 Running on host system")
    
    # Show available packages
    print("\n📦 Checking AI/ML packages:")
    ai_packages_to_check = [
        'numpy', 'pandas', 'matplotlib', 'seaborn', 'jupyter',
        'requests', 'sklearn', 'tensorflow', 'torch', 'transformers'
    ]
    
    for package in ai_packages_to_check:
        try:
            __import__(package)
            print(f"   ✅ {package} - Available")
        except ImportError:
            print(f"   ❌ {package} - Not installed (can be added to requirements.txt)")
    
    # Show package manager information
    print("\n📦 Package Manager Performance:")
    print("   • mamba: 10-100x faster than conda for dependency resolution")
    print("   • uv: 10-100x faster than pip for pure Python packages")
    print("   • pip: Standard fallback for maximum compatibility")
    
    # Show AI development tips
    print("\n🤖 AI Development Tips:")
    print("   • Use Devin for AI-powered coding assistance")
    print("   • Fast installs: `mamba install -c conda-forge tensorflow pytorch`")
    print("   • Quick Python packages: `uv pip install requests fastapi`")
    print("   • Pre-installed: numpy, pandas, matplotlib, jupyter")
    print("   • Your environment is portable across all platforms!")
    
    print("\n" + "=" * 60)
    print("Demo completed! Your AI-ready venvoy environment is working! 🎉🤖")

if __name__ == "__main__":
    main() 