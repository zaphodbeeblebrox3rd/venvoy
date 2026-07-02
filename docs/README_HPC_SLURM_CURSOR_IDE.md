# venvoy on an HPC cluster with SLURM, connected to local Cursor

This guide walks through running a venvoy environment as a SLURM job on a compute
node and connecting to it from the Cursor IDE on your laptop. The connection
tunnels through the cluster login node, so the compute node is never exposed
directly.

For a terminal-only SLURM workflow, see
[README_HPC_SLURM_TERMINAL.md](README_HPC_SLURM_TERMINAL.md). For PBS or Torque
clusters, see
[README_HPC_PBS_TORQUE_TERMINAL.md](README_HPC_PBS_TORQUE_TERMINAL.md).

## When to use this scenario

- Your cluster uses SLURM and you have SSH access to the login node.
- You want to edit and run code on a compute node using Cursor on your laptop.
- Your cluster provides Apptainer or Singularity (also works with Docker or
  Podman where available).

## How it works

venvoy runs an SSH server inside the environment container on the compute node,
bound to the compute node loopback interface. Cursor Remote-SSH on your laptop
reaches it using an SSH ProxyJump through the login node. Unlike the local
Cursor scenario, this does not use a Docker socket, so it works with Apptainer
and Singularity.

```mermaid
flowchart LR
    Laptop[Local Cursor Remote-SSH]
    Login[Login node]
    Compute[Compute node]
    Sshd[sshd inside venvoy container]
    Laptop -->|ssh ProxyJump| Login
    Login -->|ssh| Compute
    Compute -->|loopback| Sshd
```

## Prerequisites

On the cluster:

- SLURM access and the ability to obtain an allocation with `srun` or `sbatch`.
- Apptainer or Singularity available (module load if needed).
- venvoy installed in your user account (see Installation below).
- A venvoy environment image that includes an SSH server. The current venvoy
  images bundle openssh-server. If your cached image predates this, run
  `venvoy update` or re-pull so the image contains `/usr/sbin/sshd`. The
  `venvoy remote` preflight check verifies this and reports a clear error if
  the image is missing sshd.

On your laptop:

- You can already SSH into the cluster login node.
- Your laptop SSH public key is present in `~/.ssh/authorized_keys` on the
  cluster. venvoy authorizes those same keys for the container, so the key you
  use to reach the login node also authenticates into the container.
- Cursor is installed with the Remote-SSH extension.

## Installation on the cluster

Load your container runtime, then run the bootstrap installer, which sets up the
`venvoy` command in your user account using pipx (no root required):

```bash
module load apptainer   # or: module load singularity

# Install venvoy
curl -fsSL https://raw.githubusercontent.com/zaphodbeeblebrox3rd/venvoy/main/install.sh | bash

# The installer places venvoy in ~/.local/bin; ensure it is on your PATH
export PATH="$HOME/.local/bin:$PATH"

venvoy runtime-info     # expect Apptainer/Singularity and HPC Environment True
```

Initialize the environment you want to serve, if you have not already:

```bash
venvoy init --runtime python --python-version 3.11 --name my-research
```

## Storage requirements

venvoy keeps its container image as a SIF file in your home directory under
`~/.venvoy/si`, and Apptainer or Singularity keeps a download cache in your home
directory as well (`~/.apptainer/cache` or `~/.singularity/cache`). In this
scenario, Cursor also installs its remote server into your cluster home directory
(`~/.cursor-server`) on first connect. On clusters with small home quotas, plan
for all three. The figures below are conservative planning estimates.

| Item | Python 3.12 environment | R 4.5 environment |
| --- | --- | --- |
| SIF image in ~/.venvoy/si | 2 to 3 GB | 4 to 6 GB |
| Runtime download cache | 2 to 3 GB | 4 to 6 GB |
| Cursor remote server in ~/.cursor-server | 0.3 to 0.5 GB | 0.3 to 0.5 GB |
| Home total with cache in home | 5 to 7 GB | 9 to 13 GB |
| Home total with cache on scratch | 2.5 to 3.5 GB | 4.5 to 6.5 GB |

The Python figures assume packages such as numpy, scipy, pandas, matplotlib,
seaborn, requests, and beautifulsoup4. The R environment uses the combined
Python and R image, which also includes a LaTeX toolchain and spatial libraries,
so it is considerably larger.

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
du -sh ~/.venvoy ~/.cursor-server
apptainer cache list      # or: singularity cache list
```

## Step 1: start the remote environment on a compute node

Request an allocation and start the SSH bridge. Provide the hostname you SSH into
to reach the cluster with `--login-node`.

```bash
# Get an interactive allocation on a compute node
srun --pty bash

# Serve the environment over SSH (keeps running until you stop it)
venvoy remote --name my-research --login-node login.hpc.example.edu
```

`venvoy remote` runs preflight checks, starts sshd inside the container, and
prints a single command to run on your laptop, for example:

```bash
venvoy connect eyJ2Ijox...long-token...
```

Keep this job running while you work. Press Ctrl-C to stop it.

### Useful venvoy remote options

- `--login-node <host>`: login node hostname users SSH into. If omitted, venvoy
  uses `VENVOY_LOGIN_NODE` or `SLURM_SUBMIT_HOST` if set; otherwise supply it on
  the laptop with `venvoy connect ... --login-node <host>`.
- `--port <n>`: fixed SSH port instead of an auto-selected free port.
- `--bind-address <addr>`: defaults to `127.0.0.1` (most secure, uses a double
  ProxyJump through login and compute). Use `0.0.0.0` only if your cluster
  permits direct TCP from the login node to arbitrary compute node ports.
- `--mount host:container`: bind additional directories, such as scratch.
- `--pubkey-file <path>`: authorize a specific public key file instead of your
  cluster `~/.ssh/authorized_keys` and `~/.ssh/*.pub`.

Example with scratch mounted:

```bash
venvoy remote --name my-research \
  --login-node login.hpc.example.edu \
  --mount /scratch/$USER/data:/workspace/data
```

## Step 2: connect from your laptop

Paste the printed command into a terminal on your laptop:

```bash
venvoy connect eyJ2Ijox...long-token...
```

This writes a managed entry in your `~/.ssh/config` that tunnels through the
login node, then launches Cursor Remote-SSH into the container. On first connect,
Cursor installs its remote server automatically.

### Useful venvoy connect options

- `--login-node <host>`: override or provide the login node hostname if it was
  not embedded in the token.
- `--alias <name>`: SSH host alias to create. Defaults to `venvoy-<name>`.
- `--workspace <path>`: folder to open inside the container. Defaults to
  `/workspace`.
- `--editor cursor|code`: editor to launch. Defaults to `cursor`.
- `--no-open`: write the SSH config only, do not launch the editor.
- `--print-config`: print the SSH config block that would be written and exit.

Examples:

```bash
# Provide the login node if it was not known to the job
venvoy connect eyJ2Ijox... --login-node login.hpc.example.edu

# Only configure SSH, then open Cursor manually later
venvoy connect eyJ2Ijox... --no-open

# Preview the SSH config block
venvoy connect eyJ2Ijox... --print-config
```

After connecting, open the folder inside the container (default `/workspace`).
Your cluster home directory is available and writable inside the session.

## Step 3: stop the session

When finished, return to the compute node terminal running `venvoy remote` and
press Ctrl-C. This stops the SSH server and cleans up the ephemeral host keys.
Releasing or ending the SLURM allocation also stops the environment.

## Security notes

- The SSH server binds to the compute node loopback by default and is reached
  only through the login and compute nodes over SSH.
- venvoy reuses your existing SSH keys; no new long-lived credentials are
  created. Host keys are ephemeral and regenerated each session.

## Troubleshooting

- Image does not contain an SSH server: the preflight check reports this. Run
  `venvoy update` or re-pull the image so it includes `/usr/sbin/sshd`.
- No SSH public keys found to authorize: add your laptop public key to
  `~/.ssh/authorized_keys` on the cluster, or pass `--pubkey-file`.
- Login node hostname is required: pass `--login-node` on either `venvoy remote`
  or `venvoy connect`, or set `VENVOY_LOGIN_NODE` before launching.
- Cursor cannot connect: confirm you can `ssh login.hpc.example.edu` from your
  laptop, that the Remote-SSH extension is installed, and try
  `venvoy connect ... --print-config` to inspect the generated SSH entry.
- Direct connection blocked: if your cluster does not allow the login node to
  reach compute node loopback via a second SSH hop, re-run `venvoy remote` with
  `--bind-address 0.0.0.0` for a single-hop jump.

## Rollback

The remote bridge is gated by a single flag. To disable both `venvoy remote` and
`venvoy connect`, set `REMOTE_ENABLED = False` in
[../src/venvoy/remote.py](../src/venvoy/remote.py).

## Back to index

Return to the setup guide index in the main [README](../README.md).
