# venvoy - AI-Ready Python Environments

[![Docker Pulls](https://img.shields.io/docker/pulls/zaphodbeeblebrox3rd/venvoy)](https://hub.docker.com/r/zaphodbeeblebrox3rd/venvoy)
[![Docker Image Size](https://img.shields.io/docker/image-size/zaphodbeeblebrox3rd/venvoy)](https://hub.docker.com/r/zaphodbeeblebrox3rd/venvoy)
[![Multi-Architecture](https://img.shields.io/badge/arch-amd64%2C%20arm64-blue)](https://hub.docker.com/r/zaphodbeeblebrox3rd/venvoy)

Pre-built, multi-architecture Python environments with AI/ML packages and ultra-fast package managers.

## 🚀 Quick Start

```bash
# Run Python 3.11 environment (default)
docker run --rm -it zaphodbeeblebrox3rd/venvoy:latest

# Run specific Python version
docker run --rm -it zaphodbeeblebrox3rd/venvoy:python3.12

# Mount your project directory
docker run --rm -it -v $(pwd):/workspace zaphodbeeblebrox3rd/venvoy:python3.11
```

## 📦 Available Tags

| Tag | Python Version | R Version | Architecture | Description |
|-----|----------------|----------|--------------|-------------|
| `latest` | 3.11 | 4.3 | amd64, arm64 | Default Python 3.11 / R 4.3 environment |
| `python3.13-r4.5` | 3.13 | 4.5 | amd64, arm64 | Python 3.13 / R 4.5 environment |
| `python3.12-r4.4` | 3.12 | 4.4 | amd64, arm64 | Python 3.12 / R 4.4 environment |
| `python3.11-r4.3` | 3.11 | 4.3 | amd64, arm64 | Python 3.11 / R 4.3 environment |
| `python3.11-r4.2` | 3.11 | 4.2 | amd64, arm64 | Python 3.11 / R 4.2 environment |
| `python3.10-r4.2` | 3.10 | 4.2 | amd64, arm64 | Python 3.10 / R 4.2 environment |

### 🚫 **Legacy Python Versions (Not Supported)**
venvoy focuses on **actively supported Python versions** only. We do not provide images for:
- **Python 3.8** (EOL October 2024) - High security risk, limited package support
- **Python 3.7** (EOL June 2023) - Very high security risk, most packages dropped support  
- **Python 3.6** (EOL December 2021) - Critical security risk, severely limited ecosystem

**Why we don't support EOL versions:**
- 🔒 **Security vulnerabilities** with no patches available
- 📦 **Package ecosystem collapse** - modern AI/ML libraries require Python 3.9+
- 🛠️ **Broken user experience** - environments that can't install popular packages
- 💼 **Professional standards** - supporting EOL software is not recommended

## ✨ What's Included

### 🐍 **Python Environment**
- **System Python** - Python from official Debian packages
- **UV** - Ultra-fast Python package installer (10-100x faster than pip)
- **Pip** - Standard Python package installer (fallback)

### 📊 **R Environment**
- **System R** - R from Debian CRAN repository
- **CRAN packages** - Install R packages via `install.packages()`

### 📊 **Pre-installed AI/ML Packages**
- **numpy** - Numerical computing
- **pandas** - Data analysis and manipulation
- **matplotlib** - Plotting and visualization
- **seaborn** - Statistical data visualization
- **scikit-learn** - Machine learning library
- **jupyter** - Interactive notebooks
- **ipython** - Enhanced interactive Python

### 🛠️ **Development Tools**
- **git** - Version control
- **curl** - Data transfer tool
- **vim/nano** - Text editors
- **htop** - Process monitor
- **rich** - Rich text and beautiful formatting
- **click** - Command line interface creation
- **fastapi** - Modern web framework
- **uvicorn** - ASGI server

## 🏗️ **Use with venvoy CLI**

For the best experience, use these images with the venvoy CLI tool:

```bash
# Install venvoy CLI
pip install venvoy

# Initialize environment (uses these pre-built images)
venvoy init --python-version 3.11

# Run environment with AI editor integration
venvoy run
```

Learn more: [github.com/zaphodbeeblebrox3rd/venvoy](https://github.com/zaphodbeeblebrox3rd/venvoy)

## 🔧 **Manual Usage**

### Basic Container
```bash
docker run --rm -it zaphodbeeblebrox3rd/venvoy:python3.11
```

### With Project Directory
```bash
docker run --rm -it \
  -v $(pwd):/workspace \
  -w /workspace \
  zaphodbeeblebrox3rd/venvoy:python3.11
```

### With Home Directory Access
```bash
docker run --rm -it \
  -v $HOME:/home/venvoy/host-home \
  -v $(pwd):/workspace \
  -w /workspace \
  zaphodbeeblebrox3rd/venvoy:python3.11
```

### Install Additional Packages
```bash
# Using uv (fastest for Python packages)
uv pip install tensorflow pytorch fastapi uvicorn

# Using pip (universal fallback)
pip install requests beautifulsoup4

# Install R packages
R -e "install.packages('tidyverse')"
# Or interactively:
R
> install.packages(c('tidyverse', 'devtools'))
```

### **How venvoy Works on so many platforms:**

**🪟 Windows:** Uses Docker Desktop with WSL2 to run Linux containers seamlessly  
**🍎 macOS:** Uses Docker Desktop with HyperKit/Virtualization.framework to run Linux containers  
**🐧 Linux:** Runs containers natively without virtualization overhead

*The magic: You get identical Python environments regardless of your host OS!*

### **Supported Architectures:**
- **linux/amd64** - Intel/AMD 64-bit (Windows PCs, Intel Macs, most servers)
- **linux/arm64** - ARM 64-bit (Apple Silicon Macs, ARM servers, AWS Graviton)

Docker automatically pulls the correct architecture for your system.

### **Enterprise Architecture Support:**
*IBM Power (ppc64le) and IBM mainframe (s390x) and Windows Server support available on request.  
If your organization needs these platforms, I'd be happy to add them for a consulting fee.*

## 📝 **License**

MIT License - See [LICENSE](https://github.com/zaphodbeeblebrox3rd/venvoy/blob/main/LICENSE)

## 🤝 **Contributing**

Issues and pull requests welcome at [github.com/zaphodbeeblebrox3rd/venvoy](https://github.com/zaphodbeeblebrox3rd/venvoy) 