# venvoy on an HPC cluster with SLURM in the terminal

This guide walks through installing, configuring, and running venvoy on a
High-Performance Computing cluster that uses the SLURM scheduler, using a
terminal workflow. It covers both interactive sessions and batch job
submission. On HPC, venvoy automatically prefers Apptainer or Singularity, which
do not require root access.

If you want to connect Devin on your laptop to a SLURM compute node,
see [README_HPC_SLURM_DEVIN_SRUN.md](README_HPC_SLURM_DEVIN_SRUN.md) or
[README_HPC_SLURM_DEVIN_SBATCH.md](README_HPC_SLURM_DEVIN_SBATCH.md). For PBS or
Torque clusters, see
[README_HPC_PBS_TORQUE_TERMINAL.md](README_HPC_PBS_TORQUE_TERMINAL.md).

## When to use this scenario

- Your cluster uses SLURM (commands like `sbatch`, `srun`, `squeue`).
- You work over SSH in a terminal on the login and compute nodes.
- You want reproducible containerized environments without root access.

## How it works

You log into the cluster login node over SSH, request resources with SLURM, and
run venvoy on the allocated compute node. venvoy detects the HPC environment
(for example the `SLURM_JOB_ID` variable) and uses Apptainer or Singularity.

```mermaid
flowchart LR
    User[Your laptop SSH]
    Login[Login node]
    Compute[Compute node]
    Venvoy[venvoy via apptainer]
    User --> Login
    Login -->|srun or sbatch| Compute
    Compute --> Venvoy
```

## Prerequisites

- SSH access to the cluster login node.
- Apptainer or Singularity available on the cluster. Most clusters provide this
  as a module. Check with your system administrators if unsure.
- Python available on the login node for installing venvoy (a `python` or
  `module load python` is usually available).

## Installation

venvoy is installed with its bootstrap installer, which sets up the `venvoy`
command in your user account using pipx. No root access is required.

First load the container runtime module your cluster provides, then run the
installer:

```bash
# Load the container runtime provided by your cluster
module load apptainer
# or
module load singularity

# Install venvoy (user-level, no root required)
curl -fsSL https://raw.githubusercontent.com/zaphodbeeblebrox3rd/venvoy/main/install.sh | bash
```

The installer places the `venvoy` command in `~/.local/bin`. Ensure that
directory is on your PATH:

```bash
export PATH="$HOME/.local/bin:$PATH"
```

If you prefer a direct Python-based install, venvoy can also be installed with
pipx (which is what the bootstrap installer uses under the hood):

```bash
pipx install git+https://github.com/zaphodbeeblebrox3rd/venvoy.git
```

## Verify your setup

```bash
venvoy runtime-info
```

You should see Apptainer or Singularity as the runtime and an HPC Environment
value of True. If it reports Docker or a non-HPC environment, confirm the module
is loaded and that you are on a cluster node.

## Storage requirements

venvoy keeps its container image as a SIF file in your home directory under
`~/.venvoy/si`, and Apptainer or Singularity keeps a download cache in your home
directory as well (`~/.apptainer/cache` or `~/.singularity/cache`). On clusters
with small home quotas, plan for both. The image dominates usage, so the exact
package list changes the total only slightly. The figures below are conservative
planning estimates.

| Environment | SIF image in ~/.venvoy/si | Runtime download cache | Home total with cache in home | Home total with cache on scratch |
| --- | --- | --- | --- | --- |
| Python 3.12 with numpy, scipy, pandas, matplotlib, seaborn, requests, beautifulsoup4 | 2 to 3 GB | 2 to 3 GB | 5 to 6 GB | 2 to 3 GB |
| R 4.5 with comparable packages such as tidyverse, data.table, ggplot2 | 4 to 6 GB | 4 to 6 GB | 8 to 12 GB | 4 to 6 GB |

The R environment uses the combined Python and R image, which also includes a
LaTeX toolchain and spatial libraries, so it is considerably larger than the
Python environment.

To keep home usage low, redirect the download cache to scratch before pulling the
image, and clear it once the SIF has been built:

```bash
# Redirect the download cache off your home directory
export APPTAINER_CACHEDIR=/scratch/$USER/apptainer-cache
# or, for Singularity
export SINGULARITY_CACHEDIR=/scratch/$USER/singularity-cache

# After the image has been pulled and converted, clear the download cache
apptainer cache clean     # or: singularity cache clean
```

Check actual usage at any time:

```bash
du -sh ~/.venvoy
apptainer cache list      # or: singularity cache list
```

Environment exports (`venvoy export --format archive`) are also large, roughly
1 to 5 GB for Python and more for R. Write those to scratch with
`--output /scratch/$USER/...` rather than your home directory.

## Initialize an environment

```bash
# Python environment
venvoy init --runtime python --python-version 3.11 --name my-research

# R environment
venvoy init --runtime r --r-version 4.4 --name my-stats
```

venvoy pulls the container image and converts it to a SIF file for Apptainer or
Singularity automatically. On clusters with restricted registry access, see the
offline archives note below.

## Interactive session

Request an interactive allocation, then run venvoy:

```bash
# Start an interactive session on a compute node
srun --pty bash

# Confirm the runtime on the compute node
venvoy runtime-info

# Enter the environment shell with data mounted from scratch
venvoy run --name my-research --mount /scratch/$USER/data:/workspace/data
```

Inside the container, use uv, pip, or R to install packages and run your work.

## Batch job submission

Create a submission script, for example `run_analysis.sbatch`:

```bash
#!/bin/bash
#SBATCH --job-name=venvoy-analysis
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --time=02:00:00
#SBATCH --output=venvoy-%j.out

# Load the container runtime if required on your cluster
module load apptainer

# Make sure venvoy is on PATH for the batch shell
export PATH="$HOME/.local/bin:$PATH"

# Run your analysis inside the venvoy environment
venvoy run --name my-research \
  --mount /scratch/$USER/data:/workspace/data \
  --command "python analysis.py"
```

Submit and monitor the job:

```bash
sbatch run_analysis.sbatch
squeue -u $USER
scontrol show job <job_id>
```

The `--command` form runs non-interactively and exits when finished, which is
the correct pattern for batch jobs.

## Data mounts

Use bind mounts to bring cluster storage into the container. venvoy translates
the syntax to the correct runtime automatically.

```bash
venvoy run --name my-research --mount /scratch/$USER/data:/workspace/data
venvoy run --name my-research --mount /home/$USER/code:/workspace/code
```

## Offline and restricted networks

Some clusters block access to public container registries. Prepare an archive
where you do have access, then move it to the cluster.

```bash
# On a machine with registry access
venvoy export --name my-research --format archive --output my-research.tar.gz

# On the cluster
venvoy import my-research.tar.gz --format archive
venvoy run --name my-research
```

For cross-architecture package caches, use `--format wheelhouse`.

## Reproducibility

```bash
# Export a comprehensive archive for collaborators or submission
venvoy export --name my-research --format archive

# View export history
venvoy history --name my-research
```

## Troubleshooting

- No supported container runtime found: load the apptainer or singularity
  module and confirm with `venvoy runtime-info`.
- Permission denied errors: ensure you are using Apptainer or Singularity, not
  Docker, and check permissions on your data directories.
- Image pulling fails: your cluster may restrict registry access. Use the
  offline archive workflow above.
- venvoy command not found in a batch job: export the user bin directory on
  PATH inside the script, as shown in the batch example.

See also the deeper reference in
[HPC_COMPATIBILITY.md](HPC_COMPATIBILITY.md).

## Back to index

Return to the setup guide index in the main [README](../README.md).
