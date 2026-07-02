# venvoy on a local machine in the terminal

This guide walks through installing, configuring, and running venvoy on your own
computer (laptop or workstation) using an interactive shell only, without an
IDE. venvoy starts a container locally and drops you into an enhanced,
AI-ready bash shell.

If you want the Cursor IDE experience instead, see
[README_LOCAL_CURSOR.md](README_LOCAL_CURSOR.md). If you are working on an HPC
cluster, see the SLURM or PBS guides listed in the main
[README](../README.md).

## When to use this scenario

- You run venvoy on your own machine.
- You prefer a command-line workflow (scripts, REPL, batch commands).
- You do not want or need an editor to launch automatically.

## How it works

venvoy starts a container with your home directory mounted at `/host-home` and
your current directory mounted at `/workspace`, then gives you an interactive
shell inside it. All package management happens inside the container.

```mermaid
flowchart LR
    Shell[Your terminal]
    Engine[Docker or Podman]
    Container[venvoy container shell]
    Shell --> Engine
    Engine --> Container
```

## Prerequisites

- A container runtime:
  - Windows or macOS: Docker Desktop
  - Linux: Docker or Podman
- No host Python installation is required when using the one-liner installer.

## Installation

### Linux, macOS, or WSL

```bash
curl -fsSL https://raw.githubusercontent.com/zaphodbeeblebrox3rd/venvoy/main/install.sh | bash
```

### Windows PowerShell

```powershell
iwr -useb https://raw.githubusercontent.com/zaphodbeeblebrox3rd/venvoy/main/install.ps1 | iex
```

After installation, restart your terminal (or run `source ~/.bashrc` or
`source ~/.zshrc`) so the `venvoy` command is on your PATH.

### Alternative: install with pipx

If you already have Python available and prefer a direct install, venvoy can be
installed with pipx (this is what the bootstrap installer uses under the hood):

```bash
pipx install git+https://github.com/zaphodbeeblebrox3rd/venvoy.git
```

## Verify your setup

```bash
venvoy --help
venvoy runtime-info
```

On a local machine you should see Docker (or Podman) and an HPC Environment
value of False. Make sure Docker Desktop is running before continuing.

## First-time setup

```bash
venvoy setup
```

This creates the venvoy home directory used for container mounts. In this
scenario you can ignore editor detection.

## Initialize an environment

Python:

```bash
# Default Python 3.11 environment
venvoy init --name my-project

# Specific Python version
venvoy init --runtime python --python-version 3.12 --name my-project
```

R:

```bash
venvoy init --runtime r --r-version 4.4 --name my-stats
```

Add `--force` to reinitialize an existing environment.

## Configuration

Per-environment settings live in `~/.venvoy/environments/<name>/config.yaml`.
To ensure the interactive shell is used even if an editor is installed, set the
environment to shell mode:

```bash
venvoy configure --name my-project
```

Choose the None option to use the interactive shell.

## Run in the terminal

Launch the environment and enter the shell:

```bash
venvoy run --name my-project
```

You will see an enhanced prompt with Python and package manager information.
Your home directory is at `/host-home` and your working directory at
`/workspace`.

### Run a single command and exit

```bash
venvoy run --name my-project --command "python analysis.py"
```

### Mount additional directories

```bash
venvoy run --name my-project --mount /path/to/data:/workspace/data
```

## Install packages

Inside the container:

```bash
# Ultra-fast Python installer
uv pip install pandas numpy scikit-learn

# Standard pip
pip install some-package

# R packages
R -e "install.packages('tidyverse')"
```

## Export and import for reproducibility

```bash
# Export a comprehensive binary archive
venvoy export --name my-project --format archive --output my-project.tar.gz

# Import on another machine of the same architecture
venvoy import my-project.tar.gz --format archive

# Cross-architecture package cache
venvoy export --name my-project --format wheelhouse
```

## Stop the environment

For a container started in the background, stop and remove it with:

```bash
venvoy exit --name my-project
```

If you are inside the interactive shell, type `exit` to leave it.

## Everyday commands

```bash
venvoy list
venvoy history --name my-project
venvoy delete --name my-project
```

## Troubleshooting

- Docker not running: start Docker Desktop (Windows/macOS) or the Docker service
  (Linux), then retry.
- Permission issues on Linux: add your user to the docker group, or use Podman.
- Command not found after install: restart the terminal or source your shell rc
  file.

## Back to index

Return to the setup guide index in the main [README](../README.md).
