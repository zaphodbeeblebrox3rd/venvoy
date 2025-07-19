# HPC Compatibility Guide

## Overview

Venvoy is designed to work seamlessly across different computing environments, including High-Performance Computing (HPC) clusters where Docker may not be available or require root access. This guide explains the container runtime abstraction and HPC compatibility features.

## The Problem with Docker on HPC

Traditional Docker containers require root access to run, which is typically not available to researchers on HPC clusters. This creates a significant barrier for scientific computing workflows.

## Solution: Container Runtime Abstraction

Venvoy implements a container runtime abstraction that automatically detects and uses the best available container technology for your environment:

### Supported Runtimes

1. **Apptainer/Singularity** (Recommended for HPC)
   - No root access required
   - Designed specifically for HPC environments
   - Runs containers as the user, not root
   - Widely adopted in scientific computing

2. **Podman**
   - Rootless containers
   - Docker-compatible commands
   - Growing adoption in enterprise environments

3. **Docker**
   - Traditional container runtime
   - Best for development environments
   - Fallback option when others aren't available

## Automatic Runtime Detection

Venvoy automatically detects your environment and chooses the best runtime:

### HPC Environment Detection

Venvoy detects HPC environments by checking for:
- Job scheduler environment variables (`SLURM_JOB_ID`, `PBS_JOBID`, etc.)
- Hostname patterns (`login`, `compute`, `node`, `hpc`, `cluster`)

### Runtime Priority (HPC Environments)

1. **Apptainer** - Most HPC-friendly
2. **Singularity** - Legacy HPC container runtime
3. **Podman** - Rootless alternative
4. **Docker** - Fallback (may not work without root)

### Runtime Priority (Development Environments)

1. **Docker** - Most familiar
2. **Podman** - Rootless alternative
3. **Apptainer/Singularity** - Available but less common

## Usage Examples

### Basic Usage (Runtime-Agnostic)

```python
from venvoy import VenvoyEnvironment

# Venvoy automatically detects the best runtime
env = VenvoyEnvironment("my-research-env")
env.initialize()
env.run("python my_analysis.py")
```

### Checking Runtime Information

```python
from venvoy.container_manager import ContainerManager

manager = ContainerManager()
info = manager.get_runtime_info()
print(f"Using {info['runtime']} {info['version']}")
print(f"HPC environment: {info['is_hpc']}")
```

### Manual Runtime Selection

```python
# You can also check what's available
from venvoy.container_manager import ContainerRuntime

# Check if Apptainer is available
if manager._check_runtime_available(ContainerRuntime.APPTAINER):
    print("Apptainer is available - perfect for HPC!")
```

## HPC-Specific Features

### 1. Automatic Environment Detection

Venvoy automatically detects when you're on an HPC cluster and adjusts its behavior accordingly.

### 2. SIF File Management

When using Apptainer/Singularity, Venvoy automatically:
- Converts Docker images to SIF format
- Manages SIF file storage
- Handles image pulling and caching

### 3. Bind Mount Compatibility

All container runtimes support bind mounts for data access:
- Docker: `-v /host/path:/container/path`
- Apptainer/Singularity: `--bind /host/path:/container/path`
- Podman: `-v /host/path:/container/path`

### 4. Environment Variable Handling

Environment variables are properly passed through all runtimes:
- Docker: `-e KEY=value`
- Apptainer/Singularity: `--env KEY=value`
- Podman: `-e KEY=value`

## Installation on HPC Clusters

### Prerequisites

Most HPC clusters already have Apptainer or Singularity installed. Check with your system administrators.

### Installing Venvoy

```bash
# Install venvoy (no root access required)
pip install --user venvoy

# Or install in a virtual environment
python -m venv venvoy-env
source venvoy-env/bin/activate
pip install venvoy
```

### Verifying Installation

```bash
# Check what runtime venvoy will use
python -c "from venvoy.container_manager import ContainerManager; print(ContainerManager().get_runtime_info())"
```

## Best Practices for HPC

### 1. Use Apptainer/Singularity When Available

These are specifically designed for HPC environments and don't require root access.

### 2. Leverage Bind Mounts for Data

Mount your research data directories into containers:

```python
# Venvoy automatically handles the correct syntax for your runtime
env.run("python analysis.py", additional_mounts=["/scratch/data:/workspace/data"])
```

### 3. Use Environment Exports for Reproducibility

Export your environments to share with collaborators:

```python
# Export environment for sharing
env.export_archive("my-research-env.tar.gz")

# Import on another system
env.import_archive("my-research-env.tar.gz")
```

### 4. Monitor Resource Usage

Venvoy works with standard HPC monitoring tools:
- SLURM's `squeue` and `scontrol`
- PBS's `qstat`
- System monitoring tools

## Troubleshooting

### Common Issues

1. **"No supported container runtime found"**
   - Install Apptainer, Singularity, or Podman
   - Contact your HPC system administrators

2. **Permission denied errors**
   - Ensure you're using Apptainer/Singularity (not Docker)
   - Check file permissions on your data directories

3. **Image pulling fails**
   - Check network connectivity
   - Verify image registry access
   - Try pulling manually to debug

### Getting Help

- Check runtime information: `python -c "from venvoy.container_manager import ContainerManager; print(ContainerManager().get_runtime_info())"`
- Verify HPC detection: `python -c "from venvoy.container_manager import ContainerManager; print(ContainerManager()._is_hpc_environment())"`
- Test runtime availability: `python -c "from venvoy.container_manager import ContainerRuntime; print(ContainerManager()._check_runtime_available(ContainerRuntime.APPTAINER))"`

## Migration from Docker

If you're currently using Docker and need to migrate to HPC:

1. **No code changes required** - Venvoy handles the abstraction
2. **Export your environment** - Use `env.export_archive()` to save your setup
3. **Import on HPC** - Use `env.import_archive()` to restore
4. **Test thoroughly** - Verify all dependencies work in the new environment

## Future Enhancements

Planned improvements for HPC compatibility:

1. **Charliecloud support** - Additional HPC container runtime
2. **Shifter support** - Cray-specific container runtime
3. **SLURM integration** - Direct job submission
4. **Multi-node support** - Distributed computing workflows
5. **GPU support** - CUDA and ROCm integration

## Contributing

We welcome contributions to improve HPC compatibility:

1. **Test on different HPC systems**
2. **Report issues** with specific runtime combinations
3. **Add support** for additional container runtimes
4. **Improve documentation** for your specific HPC environment

## References

- [Apptainer Documentation](https://apptainer.org/docs/)
- [Singularity Documentation](https://docs.sylabs.io/)
- [Podman Documentation](https://podman.io/getting-started/)
- [HPC Container Best Practices](https://hpc-container-toolkit.readthedocs.io/) 