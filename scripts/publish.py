#!/usr/bin/env python3
"""
Manual PyPI publishing script for venvoy
"""

import subprocess
import sys
import os
from pathlib import Path

def run_command(cmd, check=True):
    """Run a command and return the result"""
    print(f"🔄 Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.stdout:
        print(result.stdout)
    if result.stderr:
        print(result.stderr, file=sys.stderr)
    
    if check and result.returncode != 0:
        print(f"❌ Command failed with exit code {result.returncode}")
        sys.exit(1)
    
    return result

def check_prerequisites():
    """Check that required tools are installed"""
    print("🔍 Checking prerequisites...")
    
    # Check Python version
    if sys.version_info < (3, 9):
        print("❌ Python 3.9+ required")
        sys.exit(1)
    print(f"✅ Python {sys.version_info.major}.{sys.version_info.minor}")
    
    # Check required packages
    required_packages = ['build', 'twine']
    missing_packages = []
    
    for package in required_packages:
        result = run_command([sys.executable, '-c', f'import {package}'], check=False)
        if result.returncode != 0:
            missing_packages.append(package)
    
    if missing_packages:
        print(f"📦 Installing missing packages: {', '.join(missing_packages)}")
        run_command([sys.executable, '-m', 'pip', 'install'] + missing_packages)
    
    print("✅ All prerequisites satisfied")

def clean_dist():
    """Clean previous build artifacts"""
    print("🧹 Cleaning previous builds...")
    dist_dir = Path('dist')
    if dist_dir.exists():
        import shutil
        shutil.rmtree(dist_dir)
    print("✅ Cleaned dist directory")

def build_package():
    """Build the package"""
    print("🔨 Building package...")
    run_command([sys.executable, '-m', 'build'])
    
    # List built files
    dist_files = list(Path('dist').glob('*'))
    print(f"📦 Built files:")
    for file in dist_files:
        print(f"   {file}")
    
    return dist_files

def check_package(dist_files):
    """Check package with twine"""
    print("🔍 Checking package...")
    run_command(['twine', 'check'] + [str(f) for f in dist_files])
    print("✅ Package checks passed")

def get_version():
    """Get version from pyproject.toml"""
    import tomllib
    
    with open('pyproject.toml', 'rb') as f:
        data = tomllib.load(f)
    
    return data['project']['version']

def confirm_publish(target, version):
    """Get user confirmation for publishing"""
    print(f"\n📋 Ready to publish venvoy v{version} to {target}")
    print("⚠️  This action cannot be undone!")
    
    response = input(f"Continue with publishing to {target}? (yes/no): ").strip().lower()
    
    if response not in ['yes', 'y']:
        print("❌ Publishing cancelled")
        sys.exit(0)

def publish_to_testpypi(dist_files):
    """Publish to TestPyPI"""
    print("📤 Publishing to TestPyPI...")
    run_command(['twine', 'upload', '--repository', 'testpypi'] + [str(f) for f in dist_files])
    print("✅ Published to TestPyPI")
    print("🔗 Check: https://test.pypi.org/project/venvoy/")

def publish_to_pypi(dist_files):
    """Publish to PyPI"""
    print("📤 Publishing to PyPI...")
    run_command(['twine', 'upload'] + [str(f) for f in dist_files])
    print("✅ Published to PyPI")
    print("🔗 Check: https://pypi.org/project/venvoy/")

def main():
    """Main publishing workflow"""
    print("🚀 venvoy PyPI Publishing Script")
    print("=" * 40)
    
    # Check we're in the right directory
    if not Path('pyproject.toml').exists():
        print("❌ Must run from project root (pyproject.toml not found)")
        sys.exit(1)
    
    # Get version
    version = get_version()
    print(f"📦 Package version: {version}")
    
    # Check prerequisites
    check_prerequisites()
    
    # Clean and build
    clean_dist()
    dist_files = build_package()
    check_package(dist_files)
    
    # Choose target
    print("\n🎯 Choose publishing target:")
    print("1. TestPyPI (recommended for testing)")
    print("2. PyPI (production)")
    print("3. Both (TestPyPI first, then PyPI)")
    
    while True:
        choice = input("Enter choice (1/2/3): ").strip()
        if choice in ['1', '2', '3']:
            break
        print("❌ Please enter 1, 2, or 3")
    
    # Publish based on choice
    if choice in ['1', '3']:
        confirm_publish("TestPyPI", version)
        publish_to_testpypi(dist_files)
        
        if choice == '3':
            print("\n" + "="*40)
            input("Press Enter to continue to PyPI publishing...")
    
    if choice in ['2', '3']:
        confirm_publish("PyPI", version)
        publish_to_pypi(dist_files)
    
    print("\n🎉 Publishing complete!")
    print(f"📦 venvoy v{version} is now available!")

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n❌ Publishing cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Publishing failed: {e}")
        sys.exit(1) 