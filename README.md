# venvoy

> This project is in beta.  It requires extensive testing but is in a working state.
> I want to be able to establish some reasonable guarantee that this will provide
> cross-platform and cross-architecture compatibility beyond reproach.

![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)
![Python Versions](https://img.shields.io/badge/Python-3.10%2B-blue.svg)
![R Versions](https://img.shields.io/badge/R-4.2%2B-blue.svg)
![Docker](https://img.shields.io/badge/Docker-Supported-blue.svg)
![Apptainer](https://img.shields.io/badge/Apptainer-Supported-blue.svg)
![Singularity](https://img.shields.io/badge/Singularity-Supported-blue.svg)
![Podman](https://img.shields.io/badge/Podman-Supported-blue.svg)
![HPC Compatible](https://img.shields.io/badge/HPC-Compatible-brightgreen.svg)
![AI Ready](https://img.shields.io/badge/AI-Ready-brightgreen.svg)
![Cross Platform](https://img.shields.io/badge/Platform-Linux%20%7C%20macOS%20%7C%20Windows-lightgrey.svg)
![Cross Architecture](https://img.shields.io/badge/Architecture-amd64%20%7C%20arm64-blue.svg)

**Scientifically reproducible, containerized Python and R environments for data science**

## 🔬 Core Mission: Scientific Reproducibility

venvoy creates **truly portable Python and R environments** that deliver **identical results** across any platform. Built for data scientists, researchers, and teams who need:

- **Exact same numerical results** from the same analysis, regardless of hardware
- **Bit-for-bit identical outputs** across Intel, Apple Silicon, and ARM servers  
- **Complete environment snapshots** that can be shared with colleagues and reviewers
- **Long-term archival** for research validation and replication studies
- **Guaranteed reproducibility** for regulatory compliance and peer review
- **HPC cluster compatibility** for research computing without root access

## 🎯 Why This Matters for Data Science

### **Research Collaboration**
- **Peer review**: Reviewers can run your exact environment and reproduce results
- **Team collaboration**: All members get identical results regardless of their hardware
- **Cross-institutional**: Share environments between universities, companies, labs

### **Scientific Integrity** 
- **Publication reproducibility**: Research can be validated years later with identical setup
- **Regulatory compliance**: FDA, clinical trials, and other regulated environments
- **Academic standards**: Meet journal requirements for computational reproducibility

### **Real-World Problems venvoy Solves**
- **"Works on my machine"**: Eliminate environment differences between team members
- **Architecture conflicts**: Same code, same results on x86_64, ARM64, Apple Silicon
- **Version drift**: Lock down exact package versions for long-term reproducibility
- **Platform dependencies**: Handle Windows/Linux/macOS differences seamlessly
- **Hardware specifics**: Manage CUDA vs Metal vs CPU-only package variants
- **HPC access barriers**: Work on research clusters without root access or Docker
- **Container runtime conflicts**: Automatic detection of Docker, Apptainer, Singularity, Podman

## 🚀 Overview

Developers, Hobbyists, Researchers, and IT Professionals - have you had these headaches?
- **Package builds that are still running** after waking up from a long nap?
- **Published research that can't be reproduced** because the original Python environment is lost or incompatible?
- **Peer review failures** when reviewers can't replicate your computational results on their systems?
- **Cross-platform collaboration breakdown** where the same analysis produces different results on Intel vs ARM architectures?
- **Regulatory compliance issues** where you can't demonstrate exact reproducibility of your statistical models?
- **"Works on my machine" syndrome** that prevents your team from validating each other's data science work?
- **Version drift disasters** where updating one package breaks your entire analysis pipeline?

**venvoy solves these fundamental scientific reproducibility problems.**

### What Venvoy Is

`venvoy` creates **containerized Python and R environments** that deliver **identical sofware environments** across any platform. Unlike traditional virtual environments that are tied to specific systems and architectures, venvoy environments guarantee the same numerical outputs whether running on:

- **Research institutions** - Share exact environments between universities and labs
- **Cross-platform teams** - Intel workstations, Apple Silicon laptops, ARM cloud servers
- **Regulatory environments** - FDA submissions, clinical trials, financial modeling
- **Long-term archival** - Reproduce results years later for validation studies
- **Peer review** - Reviewers get your exact computational environment
- **Multi-architecture deployment** - Seamless scaling from laptop to cloud infrastructure
- **HPC clusters** - Work on research computing clusters without root access

### What Venvoy is Not
Venvoy is not a way to eliminate hardware-level differences that affect floating-point math, random number generation, etc.  Plese see docs\ARCHITECTURAL_DIFFERENCE_EXAMPLES for more detail on this issue.

Here is a brief summary of strategies you can use to eliminate or at least minimize the impact of CPU architecture differences on reproducibility of your computations.  For more detail, see docs\ARCHITECTURAL_STRATEGIES.md
1. **Use explicit precision types** - Always specify `np.float64` or `np.float32` rather than relying on defaults
2. **Set tolerances for comparisons and document them** - Use `np.allclose()` with appropriate `rtol` and `atol` instead of exact equality, and document expected precision bounds in your code and documentation
3. **Pin your BLAS/LAPACK backend** - Specify the OpenBLAS linear algebra library to use across the board instead of allowing the system to fall back on its own BLAS implementation.
4. **Avoid extended precision accumulation** - Use `math.fsum()` or Kahan summation for long-running sums
5. **Use deterministic algorithms** - Disable non-deterministic GPU operations and set `PYTHONHASHSEED`
6. **Run validation tests across architectures** - Include numerical tolerance tests in your CI/CD pipeline
7. **Consider fixed-point or arbitrary precision** - Use `decimal.Decimal` or `mpmath` for calculations requiring exact reproducibility


### 🌐 **How Cross-Platform Magic Works:**
- **🏢 HPC Clusters & Research Computing**: Apptainer/Singularity containers without root access
- **🏢 Enterprise & Shared Systems**: Secure container execution without admin privileges
- **🪟 Windows**: Docker Desktop + WSL2 runs Linux containers seamlessly
- **🍎 macOS**: Docker Desktop virtualizes Linux containers transparently  
- **🐧 Linux (with root)**: Docker/Podman with full container privileges
- **🎯 Result**: Identical Python environments regardless of your host OS or privilege level!

**🏗️ Multi-Architecture Support:**
- **Intel/AMD x86_64**: Full native performance on desktop and server
- **Apple Silicon (M1/M2)**: Optimized ARM64 containers for maximum performance
- **ARM64 Servers**: Cloud-native support for ARM-based infrastructure
- **Automatic Selection**: Docker automatically pulls the correct architecture for your system

> Enterprise platforms (IBM Power/mainframes) may be made available; if you are interested please support the project and let me know.
{ .is-info }

**🔧 Multi-Runtime Container Support:**
- **Docker**: Traditional containers for development environments
- **Apptainer**: Modern HPC container runtime (no root access required)
- **Singularity**: Legacy HPC container runtime (widely adopted)
- **Podman**: Rootless containers for enterprise environments
- **Automatic Detection**: Venvoy chooses the best available runtime for your environment

## ✨ Features

- 🐍 **Python 3.10-3.13 support** - Choose your Python version (paired with R versions)
- 📊 **R 4.2-4.5 support** - Choose your R version
- 🧠 **AI-powered editors** - Cursor (AI-first) and VSCode with AI extensions
- 🐳 **Multi-runtime containers** - Docker, Apptainer, Singularity, and Podman
- 🏢 **HPC compatibility** - Works on clusters without root access
- 🔧 **Automatic runtime detection** - Chooses best container technology for your environment
- 🏗️ **Multi-architecture builds** - AMD64, ARM64, ARM32 with automatic selection
- 🌐 **Cross-platform compatibility** - Works on Windows, macOS, and Linux
- 📦 **Wheel caching** - Offline package installation support
- 💾 **Multiple export formats** - YAML, Dockerfile, tarball, and comprehensive archives
- 🤖 **AI-ready environment** - Pre-configured for AI/ML development
- 🏠 **Home directory mounting** - Access your files from containers
- ⚡ **Ultra-fast package managers** - mamba, uv, and pip for optimal performance
- 🔬 **Scientific reproducibility** - Complete environment snapshots for research validation

## 📋 Prerequisites

The prerequisites will be handled for you automatically if they are missing:
- **Container Runtime**: Docker, Apptainer, Singularity, or Podman (will be detected automatically)
- **AI Editor**: Cursor (recommended) or VSCode (will prompt for installation)
- **Python 3.10 or higher** only required for alternative/development installations

### 🏢 HPC Cluster Support

Venvoy automatically detects HPC environments and uses the appropriate container runtime:
- **Apptainer/Singularity**: No root access required, perfect for research clusters
- **Podman**: Rootless containers for enterprise environments
- **Docker**: Traditional containers for development environments

**Automatic Environment Detection:**
- Detects SLURM, PBS, LSF, SGE job schedulers
- Identifies HPC hostname patterns (login, compute, node, hpc, cluster)
- Adjusts runtime priority based on environment type

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
1. **Detects your platform** (Linux/macOS/Windows) and shell (bash/zsh/fish)
2. **Checks for Docker** (installs if missing on Linux)
3. **Creates a containerized venvoy** that runs entirely in Docker
4. **Adds venvoy to PATH** automatically in your shell configuration
5. **Creates system-wide symlink** when possible (Linux/macOS)
6. **Tests installation** and provides immediate feedback
7. **First run builds bootstrap image** with Python + venvoy inside

**PATH Integration Features:**
- ✅ **Multi-shell support** - Detects bash, zsh, fish, and more
- ✅ **Immediate availability** - Works in current session when possible
- ✅ **System-wide access** - Creates `/usr/local/bin` symlink when writable
- ✅ **Smart detection** - Prevents duplicate PATH entries
- ✅ **Cross-platform** - Works on Linux, macOS, Windows, and WSL

**Result:** You get a fully functional `venvoy` command available from any directory!

### 🔄 **Updating venvoy**

**One-Liner Updates (Recommended):**
The same one-liner installation commands act as updaters:

**Linux/macOS/WSL:**
```bash
curl -fsSL https://raw.githubusercontent.com/zaphodbeeblebrox3rd/venvoy/main/install.sh | bash
```

**Windows PowerShell:**
```powershell
iwr -useb https://raw.githubusercontent.com/zaphodbeeblebrox3rd/venvoy/main/install.ps1 | iex
```

**Built-in Update Commands:**
```bash
# Update venvoy to latest version
venvoy update

# Alternative update command
venvoy upgrade
```

**What Gets Updated:**
- ✅ **Bootstrap script** - Latest features and bug fixes
- ✅ **Docker image** - Latest venvoy code and dependencies
- ✅ **Platform detection** - Enhanced WSL and cross-platform support
- ✅ **Editor integration** - Improved AI editor detection
- ✅ **Uninstall functionality** - Working uninstall command
- ✅ **Error handling** - Better error messages and recovery

**Update Features:**
- 🔄 **Smart detection** - Automatically detects existing installations
- 🚀 **Zero downtime** - Updates happen seamlessly in background
- ✨ **Feature announcements** - Shows new features after update
- 🛡️ **Safe updates** - Preserves existing environments and configurations
- 📦 **Bootstrap updates** - Ensures latest Docker image is available

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

### ✅ **Installation Verification**

After installation, test that venvoy is available:
```bash
venvoy --help
```

**Check your container runtime:**
```bash
venvoy runtime-info
```

This will show you which container runtime venvoy will use and whether it detected an HPC environment.

If the command isn't found, restart your terminal or run:
```bash
source ~/.bashrc  # or ~/.zshrc for zsh users
```

### 🗑️ **Uninstallation**

**Recommended method (if venvoy is working):**
```bash
venvoy uninstall
```

**Alternative methods (if venvoy command is not available):**

**Linux/macOS/WSL:**
```bash
curl -fsSL https://raw.githubusercontent.com/zaphodbeeblebrox3rd/venvoy/main/uninstall.sh | bash
```

**Windows (PowerShell):**
```powershell
iwr -useb https://raw.githubusercontent.com/zaphodbeeblebrox3rd/venvoy/main/uninstall.ps1 | iex
```

**Uninstall options:**
```bash
# Quick uninstall with confirmation
venvoy uninstall

# Force uninstall without prompts
venvoy uninstall --force

# Keep environment exports
venvoy uninstall --keep-projects

# Keep Docker images
venvoy uninstall --keep-images

# Minimal cleanup (keep projects and images)
venvoy uninstall --keep-projects --keep-images
```

The uninstaller will:
- 🗑️ Remove all venvoy files and directories
- 🔧 Clean up PATH entries from shell configs
- 🐳 Optionally remove Docker images and containers
- 📁 Optionally preserve your environment exports

## 🎯 Quick Start

### 0. Verify Your Setup (Optional)
```bash
# Check your container runtime (especially important for HPC)
venvoy runtime-info
```

**💡 Pro Tip**: The `venvoy runtime-info` command is especially useful on HPC clusters to verify that venvoy will use Apptainer/Singularity instead of Docker.

### 1. Initialize a New Environment

#### Python Environments
```bash
# Create a Python 3.11 environment (default)
venvoy init

# Create with specific Python version
venvoy init --runtime python --python-version 3.12 --name my-project

# Force reinitialize existing environment
venvoy init --force
```

#### R Environments
```bash
# Create an R 4.4 environment (default)
venvoy init --runtime r --name my-r-project

# Create with specific R version
venvoy init --runtime r --r-version 4.3 --name biostatistics

# R environment with specific packages focus
venvoy init --runtime r --r-version 4.5 --name genomics-analysis
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

# Mount additional directories (works with all container runtimes)
venvoy run --mount /host/data:/container/data

# HPC example: Mount scratch directory
venvoy run --mount /scratch/data:/workspace/data
```

### 3. Restore Previous Environment (Optional)
```bash
# Interactively restore from a previous environment export
venvoy restore --name my-project

# View environment history
venvoy history --name my-project
```

### 4. Manage Packages
Add packages to your `requirements.txt` or `requirements-dev.txt` files in the environment directory, then rebuild:

```bash
# Rebuild environment with new packages
venvoy init --force

# Or freeze current state with all wheels
venvoy freeze --include-dev
```

### 5. Export for Sharing
```bash
# Export as environment YAML
venvoy export --format yaml --output environment.yaml

# Export as standalone Dockerfile
venvoy export --format dockerfile --output Dockerfile

# Export as tarball for offline use
venvoy export --format tarball --output project.tar.gz

# Export as comprehensive binary archive (for reproducibility on the same CPU Architecture)
venvoy export --format archive --output research.tar.gz

# Export as wheelhouse archive for cross-architecture reproducibility
venvoy export --format wheelhouse --output research.tar.gz

#### 📦 Comprehensive Binary Archives (Archive Format)

For **scientific reproducibility** and **long-term archival**, venvoy supports comprehensive binary archives:

```bash
# Create comprehensive archive (1-5GB file)
venvoy export --name my-research --format archive

# Import archive on any system (same architecture)
venvoy import research-archive-20240621_143022.tar.gz --format archive

# Force overwrite existing environment
venvoy import archive.tar.gz --format archive --force
```

**Binary archives contain:**
- ✅ Complete Docker image with all binaries and libraries
- ✅ System packages and dependencies with exact versions
- ✅ Full dependency trees and package manifests
- ✅ Platform and architecture information
- ✅ Self-contained restore scripts and documentation

**Use cases:**
- **Regulatory Compliance**: FDA, clinical trials, financial modeling
- **Peer Review**: Share exact computational environments with reviewers
- **Long-term Storage**: Archive environments for 5-10+ years
- **Package Abandonment Protection**: Continue using environments even if packages disappear from PyPI
- **Cross-institutional Collaboration**: Ensure identical results across different organizations
- **HPC Clusters**: Work on research clusters without root access
- **Multi-Runtime Environments**: Seamlessly switch between Docker, Apptainer, Singularity, and Podman

#### 🌐 Cross-Architecture Wheelhouse Archives

For **cross-architecture reproducibility** (works on both x86_64 and ARM64):

```bash
# Create wheelhouse archive (500MB-2GB file)
venvoy export --name my-research --format wheelhouse

# Import wheelhouse on any architecture (amd64 or arm64)
venvoy import research-wheelhouse-20240621_143022.tar.gz --format wheelhouse

# Build and use the environment
venvoy init --name my-research --force
venvoy run --name my-research
```

**Wheelhouse archives contain:**
- ✅ Python source distributions (architecture-independent)
- ✅ Python wheels for multiple architectures (amd64, arm64)
- ✅ R source packages (architecture-independent)
- ✅ R binary packages for multiple architectures
- ✅ Package manifests and metadata
- ❌ Does NOT include Docker image (must build after import)

**Use cases:**
- **Cross-Platform Development**: Work on Intel Mac, Apple Silicon, and Linux
- **Multi-Architecture Deployment**: Deploy to both x86_64 and ARM64 servers
- **Offline Package Installation**: Install packages without repository access
- **Architecture Portability**: Share environments across different CPU architectures

## 🏢 HPC Cluster Compatibility

Venvoy is designed to work seamlessly on High-Performance Computing (HPC) clusters where Docker may not be available or require root access.

### 🔧 Automatic Runtime Detection

Venvoy automatically detects your environment and chooses the best container runtime:

```bash
# Check what runtime venvoy will use
venvoy runtime-info
```

**Runtime Priority (HPC Environments):**
1. **Apptainer** - Most HPC-friendly, no root access required
2. **Singularity** - Legacy HPC container runtime
3. **Podman** - Rootless containers
4. **Docker** - Fallback (may require root)

**Runtime Priority (Development Environments):**
1. **Docker** - Most familiar
2. **Podman** - Rootless alternative
3. **Apptainer/Singularity** - Available but less common

**💡 Smart Detection**: Venvoy checks for all available runtimes and chooses the best one for your environment, ensuring maximum compatibility.

### 🚀 HPC Usage Examples

```bash
# On an HPC cluster with Apptainer/Singularity
venvoy runtime-info  # Shows: Runtime: apptainer, HPC Environment: True

# Initialize environment (works without root access)
venvoy init --runtime python --name my-research

# Run your analysis
venvoy run --name my-research --command "python analysis.py"

# Mount your data directories
venvoy run --name my-research --mount /scratch/data:/workspace/data

# Export for sharing with collaborators
venvoy export --name my-research --format archive
```

### 🔬 Scientific Computing Workflows

**SLURM Job Submission:**
```bash
#!/bin/bash
#SBATCH --job-name=venvoy-analysis
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --time=02:00:00

# Load any required modules
module load apptainer

# Run venvoy environment (automatically uses Apptainer/Singularity)
venvoy run --name my-research --command "python analysis.py"
```

**PBS Job Submission:**
```bash
#!/bin/bash
#PBS -N venvoy-analysis
#PBS -l nodes=1:ppn=1
#PBS -l walltime=2:00:00

# Run venvoy environment (automatically uses Apptainer/Singularity)
venvoy run --name my-research --command "python analysis.py"
```

**Interactive HPC Session:**
```bash
# Start interactive session
srun --pty bash

# Check runtime (should show Apptainer/Singularity)
venvoy runtime-info

# Initialize and run environment
venvoy init --name my-research
venvoy run --name my-research --mount /scratch/data:/workspace/data
```

### 📋 HPC Best Practices

1. **Use Apptainer/Singularity When Available**
   - No root access required
   - Designed specifically for HPC environments
   - Widely adopted in scientific computing

2. **Leverage Bind Mounts for Data**
   ```bash
   venvoy run --mount /scratch/data:/workspace/data
   venvoy run --mount /home/user/code:/workspace/code
   ```

3. **Export Environments for Reproducibility**
   ```bash
   # Export for sharing
   venvoy export --format archive --output research-env.tar.gz
   
   # Import on another system
   venvoy import research-env.tar.gz --format archive
   ```

4. **Monitor Resource Usage**
   - Works with standard HPC monitoring tools
   - SLURM's `squeue` and `scontrol`
   - PBS's `qstat`
   - System monitoring tools

5. **Verify Runtime Selection**
   ```bash
   # Always check what runtime will be used
   venvoy runtime-info
   
   # Should show Apptainer/Singularity on HPC clusters
   ```

6. **Handle Network Issues**
   - Some clusters have restricted Docker Hub access
   - Use comprehensive archives for offline environments
   - Contact system administrators for registry access

### 🔍 Troubleshooting HPC Issues

**Common Issues:**
- **"No supported container runtime found"** - Contact your HPC system administrators
- **Permission denied errors** - Ensure you're using Apptainer/Singularity (not Docker)
- **Image pulling fails** - Check network connectivity and registry access
- **Network timeouts** - Common on restricted clusters, use comprehensive archives

**Getting Help:**
```bash
# Check runtime information
venvoy runtime-info

# Verify HPC detection
python -c "from venvoy.container_manager import ContainerManager; print(ContainerManager()._is_hpc_environment())"

# Test runtime availability
python -c "from venvoy.container_manager import ContainerRuntime; print(ContainerManager()._check_runtime_available(ContainerRuntime.APPTAINER))"
```

**Network Issues on HPC Clusters:**
- Some clusters block Docker Hub access
- Use `venvoy export --format archive` to create offline environments
- Import archives with `venvoy import --format archive` for offline use
- Contact system administrators for registry access if needed

For detailed HPC documentation, see [docs/HPC_COMPATIBILITY.md](docs/HPC_COMPATIBILITY.md).

#### 📋 Complete Scientific Reproducibility Workflows

**Python Data Science Workflow:**
```bash
# 1. Create research environment
venvoy init --runtime python --name cancer-research --python-version 3.11

# 2. Run environment and install packages
venvoy run --name cancer-research
# Inside container:
mamba install -c conda-forge pandas numpy scipy scikit-learn matplotlib seaborn
uv pip install specific-research-package==1.2.3

# 3. Do your research work...
python analyze_data.py
jupyter notebook research_analysis.ipynb

# 4. Create comprehensive archive for submission/review
venvoy export --name cancer-research --format archive --output cancer-research-final.tar.gz

# 5. Years later, or on different system, restore exact environment
venvoy import cancer-research-final.tar.gz --format archive
venvoy run --name cancer-research
# Exact same results guaranteed!
```

**HPC Research Workflow:**
```bash
# 1. Check runtime (should show Apptainer/Singularity on HPC)
venvoy runtime-info

# 2. Create research environment
venvoy init --runtime python --name hpc-research --python-version 3.11

# 3. Run with data mounted from scratch directory
venvoy run --name hpc-research --mount /scratch/data:/workspace/data

# 4. Export for sharing with collaborators
venvoy export --name hpc-research --format archive

# 5. Submit as SLURM job
venvoy run --name hpc-research --command "python analysis.py"
```

**R Statistical Analysis Workflow:**
```bash
# 1. Create R research environment
venvoy init --runtime r --name biostatistics --r-version 4.4

# 2. Run environment and install packages
venvoy run --name biostatistics
# Inside container:
install.packages(c("survival", "meta", "forestplot"))
BiocManager::install(c("limma", "edgeR", "DESeq2"))

# 3. Do your statistical analysis...
Rscript clinical_trial_analysis.R
R -e "rmarkdown::render('statistical_report.Rmd')"

# 4. Create comprehensive archive for regulatory submission
venvoy export --name biostatistics --format archive --output fda-submission-env.tar.gz

# 5. Regulatory review or replication
venvoy import fda-submission-env.tar.gz --format archive
venvoy run --name biostatistics
# Exact statistical results guaranteed for regulatory compliance!
```

### 6. Configure Environment Settings
```bash
# Check and update AI editor integration settings
venvoy configure --name my-project

# Learn about package managers
venvoy package-managers

# List all environments
venvoy list

# View environment export history
venvoy history --name my-project

# Uninstall venvoy completely
venvoy uninstall
```

## 📁 Auto-Save Environment Tracking

venvoy automatically tracks and saves your environment changes:

### 🏠 **venvoy-projects Directory**
- **Location**: `~/venvoy-projects/[environment-name]/`
- **Auto-created**: Created automatically for each environment
- **Contents**: 
  - `environment.yml` (latest state)
  - `environment_YYYYMMDD_HHMMSS.yml` (timestamped exports)
  - `.last_updated` timestamp

### 📝 **Automatic environment.yml Generation**
- **Real-time monitoring**: Detects package installations/removals as they happen
- **Smart categorization**: Separates conda and pip packages automatically
- **Timestamped exports**: Each change creates a dated backup file
- **Exit save**: Final save when container stops
- **Conda-compatible**: Standard `environment.yml` format for easy sharing
- **History tracking**: Retain complete environment evolution history

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
3. **Editor Check** - Verifies AI editor installation (optional)
4. **Environment Setup** - Downloads pre-built environment for your Python version
5. **Configuration** - Creates directory structure and configuration
6. **Home Mounting** - Configures access to host home directory

### `venvoy freeze` - Environment Snapshotting

The `freeze` command creates a complete snapshot:

1. **Dependency Analysis** - Scans requirements.txt files
2. **Ultra-fast Downloads** - Uses `uv` for 10-100x faster wheel downloads
3. **Fallback Strategy** - Falls back to `pip download` if needed
4. **Source Building** - Builds wheels from source if needed
5. **Vendor Directory** - Stores all wheels in `vendor/` folder
6. **Snapshot Creation** - Creates timestamped environment snapshot



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

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Docker team for the containerization platform
- Python Software Foundation for the language
- R Core Team for the R language and statistical computing environment
- Anaconda team for miniconda
- All contributors and users of venvoy

## 🔗 Links

- [Documentation](https://venvoy.readthedocs.io)
- [PyPI Package](https://pypi.org/project/venvoy/)
- [Docker Hub](https://hub.docker.com/r/zaphodbeeblebrox3rd/venvoy)
- [Issues](https://github.com/zaphodbeeblebrox3rd/venvoy/issues)
- [Discussions](https://github.com/zaphodbeeblebrox3rd/venvoy/discussions)
