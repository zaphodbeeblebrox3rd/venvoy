# venvoy

![License: Apache 2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg)
![Python Versions](https://img.shields.io/badge/Python-3.9%2B-blue.svg)
![Docker](https://img.shields.io/badge/Docker-Required-blue.svg)
![AI Ready](https://img.shields.io/badge/AI-Ready-brightgreen.svg)
![Cross Platform](https://img.shields.io/badge/Platform-Linux%20%7C%20macOS%20%7C%20Windows-lightgrey.svg)

A multi-OS, multi-architecture, immutable, portable, and shareable AI-ready Python environment

## 🚀 Overview

Developers, Hobbyists, Researchers, and IT Professionals - have you had these headaches?
- Developed a project in a python environment thinking that you could export it (pip freeze, conda export, etc) for reproducability and found otherwise?
- Worked on a data science project on an old RHEL 7 server and then tried to resume work on the project on a newer RHEL 8/9/10 machine?
- Ran a statistical analysis for scientific research that needed to be independently validated by other researchers, and ran into a lot of headaches?
- Started on a project with a very specific python environment on an x86_64 machine and then tried to begin collaborating with someone with an ARM architecture?

venvoy might be the right solution for you!

`venvoy` is a revolutionary AI-powered Python environment management tool that creates truly portable environments using Docker. Unlike traditional virtual environments that are tied to specific systems, venvoy environments can run anywhere Docker is available, making them perfect for:

- **Cross-platform development** - Work seamlessly across Windows, macOS, and Linux
- **AI-powered coding** - Built-in support for Cursor and VSCode with AI extensions
- **Team collaboration** - Share identical AI-ready environments with your team
- **Reproducible research** - Archive environments for long-term reproducibility  
- **CI/CD pipelines** - Consistent environments from development to production
- **Multi-architecture support** - Build for AMD64, ARM64, and more

## ✨ Features

- 🐍 **Python 3.9-3.13 support** - Choose your Python version
- 🧠 **AI-powered editors** - Cursor (AI-first) and VSCode with AI extensions
- 🐳 **Docker-based isolation** - Complete environment encapsulation
- 🏗️ **Multi-architecture builds** - AMD64, ARM64, and more
- 📦 **Wheel caching** - Offline package installation support
- 💾 **Multiple export formats** - YAML, Dockerfile, or tarball
- 🤖 **AI-ready environment** - Pre-configured for AI/ML development
- 🏠 **Home directory mounting** - Access your files from containers
- ⚡ **Ultra-fast package managers** - mamba, uv, and pip for optimal performance

## 📋 Prerequisites

The prerequisites will be handled for you automatically if they are missing:
- Docker (will be installed automatically if missing)
- AI Editor: Cursor (recommended) or VSCode (will prompt for installation)
- Python 3.9 or higher only required for alternative/development installations

## 🛠️ Installation

### 🚀 **One-Liner Installation (Recommended)**

**(Recommended)Linux/macOS/WSL:**
```bash
curl -fsSL https://raw.githubusercontent.com/zaphodbeeblebrox3rd/venvoy/main/install.sh | bash
```

**Windows PowerShell:**
If you're not using WSL, you are in unfamiliar territory, and just want to get started.
```powershell
iwr -useb https://raw.githubusercontent.com/zaphodbeeblebrox3rd/venvoy/main/install.ps1 | iex
```

**Requirements:** Only Docker is needed! No Python installation required on host.

### 🔧 **How Bootstrap Installation Works**

The bootstrap installer:
1. **Detects your platform** (Linux/macOS/Windows)
2. **Checks for Docker** (installs if missing on Linux)
3. **Creates a containerized venvoy** that runs entirely in Docker
4. **Adds venvoy to PATH** so you can run `venvoy` commands
5. **First run builds bootstrap image** with Python + venvoy inside

**Result:** You get a fully functional `venvoy` command without installing Python!

### 📦 **Alternative Methods**

**From PyPI (requires Python):**
```bash
pip install venvoy
```

**From Source (requires Python):**
```bash
git clone https://github.com/zaphodbeeblebros3rd/venvoy.git
cd venvoy
pip install -e .
```

**Development Installation:**
```bash
git clone https://github.com/zaphodbeeblebrox3rd/venvoy.git
cd venvoy
make install-dev
```

## 🎯 Quick Start

### 1. Initialize a New Environment
```bash
# Create a Python 3.11 environment (default)
venvoy init

# Create with specific Python version
venvoy init --python-version 3.12 --name my-project

# Force reinitialize existing environment
venvoy init --force
```

> **💡 Note**: If you see an "environment already exists" error, use `--force` to reinitialize or `--name` to create a new environment with a different name.

**AI Editor Integration**: During initialization, venvoy will detect available AI-powered editors (Cursor and VSCode). You'll be prompted to choose your preferred editor or can opt for an enhanced interactive shell with AI-ready environment setup.

### 2. Run Your Environment
```bash
# Launch environment (AI editor if available, otherwise interactive shell)
venvoy run

# Force interactive shell mode
venvoy run --command /bin/bash

# Run specific command
venvoy run --command "python script.py"

# Mount additional directories
venvoy run --mount /host/data:/container/data
```

### 3. Manage Packages
Add packages to your `requirements.txt` or `requirements-dev.txt` files in the environment directory, then rebuild:

```bash
# Rebuild environment with new packages
venvoy init --force

# Or freeze current state with all wheels
venvoy freeze --include-dev
```

### 4. Build Multi-Architecture Images
```bash
# Build for multiple architectures
venvoy build --tag myregistry/myproject:latest

# Build and push to registry
venvoy build --tag myregistry/myproject:latest --push
```

### 5. Export for Sharing
```bash
# Export as environment YAML
venvoy export --format yaml --output environment.yaml

# Export as standalone Dockerfile
venvoy export --format dockerfile --output Dockerfile

# Export as tarball for offline use
venvoy export --format tarball --output project.tar.gz
```

### 6. Configure Environment Settings
```bash
# Check and update AI editor integration settings
venvoy configure --name my-project

# Learn about package managers
venvoy package-managers

# List all environments
venvoy list
```

## 📁 Auto-Save Environment Tracking

venvoy automatically tracks and saves your environment changes:

### 🏠 **venvoy-projects Directory**
- **Location**: `~/venvoy-projects/[environment-name]/`
- **Auto-created**: Created automatically for each environment
- **Contents**: `environment.yml` and `.last_updated` timestamp

### 📝 **Automatic environment.yml Generation**
- **Real-time monitoring**: Detects package installations/removals as they happen
- **Smart categorization**: Separates conda and pip packages automatically
- **Exit save**: Final save when container stops
- **Conda-compatible**: Standard `environment.yml` format for easy sharing

### 🔄 **When Auto-Save Triggers**
1. **Package Installation**: `pip install`, `mamba install`, `uv pip install`
2. **Package Removal**: `pip uninstall`, `mamba remove`
3. **Package Updates**: Version changes detected automatically
4. **Container Exit**: Final state captured when session ends

### 📋 **Example Auto-Generated environment.yml**
```yaml
name: my-project
channels:
  - conda-forge
  - defaults
dependencies:
  - numpy=1.24.3
  - pandas=2.0.2
  - matplotlib=3.7.1
  - pip:
    - fastapi==0.100.0
    - uvicorn==0.22.0
```

## 📦 Package Manager Performance

venvoy includes three package managers optimized for different use cases:

### 🐍 **mamba** - Lightning-fast conda replacement
- **10-100x faster** dependency resolution than conda
- Drop-in replacement for conda commands
- Best for: Scientific packages, AI/ML libraries, complex dependencies
- Usage: `mamba install -c conda-forge tensorflow pytorch scikit-learn`

### 🦄 **uv** - Ultra-fast Python package installer  
- **10-100x faster** than pip for pure Python packages
- Written in Rust for maximum performance
- Best for: Web frameworks, pure Python libraries, development tools
- Usage: `uv pip install fastapi uvicorn requests`

### 🐍 **pip** - Standard Python package installer
- Universal compatibility and fallback option
- Best for: Legacy packages, special cases
- Usage: `pip install some-special-package`

### 💡 **Smart Package Installation Strategy**
venvoy automatically uses the best package manager for each situation:
1. **mamba** for conda-forge packages and scientific libraries
2. **uv** for PyPI packages and pure Python libraries  
3. **pip** as a reliable fallback

## 📚 Detailed Workflow

### `venvoy init` - Environment Initialization

The `init` command performs the following steps:

1. **Platform Detection** - Identifies OS, architecture, and available tools
2. **Docker Setup** - Ensures Docker is installed and running
3. **VSCode Check** - Verifies VSCode installation (optional)
4. **Environment Creation** - Creates directory structure and configuration
5. **Dockerfile Generation** - Creates optimized multi-stage Dockerfile
6. **Container Build** - Builds the Docker image with Python and miniconda
7. **Home Mounting** - Configures access to host home directory

### `venvoy freeze` - Environment Snapshotting

The `freeze` command creates a complete snapshot:

1. **Dependency Analysis** - Scans requirements.txt files
2. **Ultra-fast Downloads** - Uses `uv` for 10-100x faster wheel downloads
3. **Fallback Strategy** - Falls back to `pip download` if needed
4. **Source Building** - Builds wheels from source if needed
5. **Vendor Directory** - Stores all wheels in `vendor/` folder
6. **Snapshot Creation** - Creates timestamped environment snapshot

### `venvoy build` - Multi-Architecture Building

The `build` command uses Docker BuildX:

1. **BuildX Setup** - Configures multi-architecture builder
2. **Platform Targeting** - Builds for linux/amd64, linux/arm64
3. **Layer Optimization** - Optimizes Docker layers for size
4. **Registry Push** - Optionally pushes to container registry

### `venvoy run` - Container Execution

The `run` command launches your environment with different modes:

**With VSCode Available:**
1. **Container Launch** - Starts container in detached mode
2. **VSCode Connection** - Automatically connects VSCode to container
3. **Remote Development** - Full IDE experience inside container
4. **Volume Mounting** - Access to home directory and workspace

**Without VSCode (Interactive Shell):**
1. **Volume Mounting** - Mounts home directory and current workspace
2. **User Mapping** - Maps host user ID to container user
3. **Environment Activation** - Automatically activates conda environment
4. **Enhanced Shell** - Custom prompt with environment information
5. **TTY Allocation** - Provides interactive terminal access

### `venvoy export` - Sharing and Archival

Export formats include:

- **YAML** - Environment specification for reconstruction
- **Dockerfile** - Standalone Dockerfile for custom builds  
- **Tarball** - Complete offline package with all dependencies

## 🏗️ Architecture

```
venvoy/
├── src/venvoy/
│   ├── cli.py              # Command-line interface
│   ├── core.py             # Core environment management
│   ├── docker_manager.py   # Docker operations
│   ├── platform_detector.py # Cross-platform detection
│   └── templates/          # Dockerfile templates
├── ~/.venvoy/              # User configuration
│   └── environments/       # Environment storage
│       └── <env-name>/
│           ├── Dockerfile
│           ├── docker-compose.yml
│           ├── requirements.txt
│           ├── requirements-dev.txt
│           ├── vendor/     # Cached wheels
│           └── config.yaml
```

## 🔧 Configuration

Each environment has a `config.yaml` file:

```yaml
name: my-project
python_version: "3.11"
created: "2024-01-01T00:00:00"
platform:
  system: windows
  architecture: amd64
base_image: python:3.11-slim
packages: []
dev_packages: []
```

## 🛠️ Troubleshooting

### Environment Already Exists Error

If you see an error like:
```
RuntimeError: Environment 'venvoy-env' already exists at ~/.venvoy/environments/venvoy-env. 
This directory contains your environment configuration, Dockerfile, and requirements. 
Use --force to reinitialize and overwrite the existing environment.
```

**Solutions:**

1. **Reinitialize the existing environment:**
   ```bash
   venvoy init --force
   ```

2. **Use a different environment name:**
   ```bash
   venvoy init --name my-new-project
   ```

3. **Start working with the existing environment:**
   ```bash
   venvoy run
   ```

4. **List all environments to see what's available:**
   ```bash
   venvoy list
   ```

### Docker Not Running

If you get Docker-related errors:
```bash
# Start Docker Desktop (macOS/Windows)
# Or on Linux:
sudo systemctl start docker
sudo systemctl enable docker
```

### Permission Issues

If you encounter permission errors:
```bash
# Add your user to the docker group (Linux)
sudo usermod -aG docker $USER
# Then log out and back in
```

### AI Editor Not Detected

If Cursor or VSCode isn't detected:
1. **Cursor**: Download from [cursor.sh](https://cursor.sh)
2. **VSCode**: Download from [code.visualstudio.com](https://code.visualstudio.com)
3. **Manual launch**: Use `venvoy run --command /bin/bash` for interactive shell

## 🧪 Testing

```bash
# Run all tests
make test

# Run with coverage
pytest tests/ --cov=src/venvoy --cov-report=html

# Run specific test
pytest tests/test_platform_detector.py -v
```

## 🎨 Development

```bash
# Format code
make format

# Run linting
make lint

# Install pre-commit hooks
make install-dev
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the Apache 2.0 License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Docker team for the containerization platform
- Python Software Foundation for the language
- Anaconda team for miniconda
- All contributors and users of venvoy

## 🔗 Links

- [Documentation](https://venvoy.readthedocs.io)
- [PyPI Package](https://pypi.org/project/venvoy/)
- [Docker Hub](https://hub.docker.com/r/zaphodbeeblebrox3rd/venvoy)
- [Issues](https://github.com/zaphodbeeblebrox3rd/venvoy/issues)
- [Discussions](https://github.com/zaphodbeeblebrox3rd/venvoy/discussions)
