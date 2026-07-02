"""
Remote development bridge for venvoy.

This module lets a user run a venvoy environment as a job on an HPC compute
node and connect to it from a local Cursor (or VSCode) instance on their
laptop. It works by running an SSH server *inside* the venvoy container on the
compute node and tunneling to it through the cluster login node using SSH
ProxyJump. Cursor's Remote-SSH then treats the container as a normal remote
host.

Why not the Dev Containers "attached-container" approach used elsewhere in
venvoy? That approach talks to a local Docker socket and requires persistent,
named containers. On HPC the runtime is almost always Apptainer/Singularity,
which has no daemon and no persistent named containers. An SSH server inside
the container is the one approach that works across Apptainer, Singularity,
Docker, and Podman.

Network path:

    local Cursor  --ssh-->  login node  --ssh-->  compute node  -->  sshd in container (127.0.0.1)

The container's sshd binds to the compute node loopback by default and is
reached with a double ProxyJump (login,compute), so no extra ports are exposed
on the cluster network and the user's existing SSH credentials are reused.

Rollback strategy:
    Set REMOTE_ENABLED = False below to disable the `venvoy remote` and
    `venvoy connect` commands without removing any code. Everything else in
    venvoy is unaffected.
"""

import base64
import getpass
import json
import os
import shutil
import socket
import stat
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional

from .container_manager import ContainerManager, ContainerRuntime

# Master feature flag. Flip to False to disable the remote/connect commands.
REMOTE_ENABLED = True

# Token format version. Bump if the token schema changes incompatibly.
TOKEN_VERSION = 1

# Path inside the container where the ephemeral sshd working directory is bound.
CONTAINER_WORKDIR = "/venvoy-remote"

# Container mount point for the user's host home (matches the rest of venvoy).
CONTAINER_HOST_HOME = "/host-home"

# Default workspace path inside the container that Cursor will open.
CONTAINER_WORKSPACE = "/workspace"

# SSH config markers so we can manage per-alias blocks idempotently.
SSH_BLOCK_START = "# >>> venvoy connect: {alias} >>>"
SSH_BLOCK_END = "# <<< venvoy connect: {alias} <<<"


class RemoteError(RuntimeError):
    """Raised when the remote bridge cannot be set up."""


def _find_free_port() -> int:
    """Pick a currently-free TCP port on loopback."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def encode_token(payload: Dict) -> str:
    """Encode a connection payload as a compact, copy-pasteable token."""
    raw = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("ascii")


def decode_token(token: str) -> Dict:
    """Decode a connection token back into a payload dict."""
    try:
        raw = base64.urlsafe_b64decode(token.encode("ascii"))
        payload = json.loads(raw.decode("utf-8"))
    except Exception as exc:  # noqa: BLE001 - want a friendly message
        raise RemoteError(
            "Invalid connection token. Copy the full token printed by "
            "'venvoy remote' on the cluster."
        ) from exc
    if not isinstance(payload, dict) or "compute_node" not in payload:
        raise RemoteError("Connection token is missing required fields.")
    return payload


def _detect_login_node(explicit: Optional[str]) -> Optional[str]:
    """
    Best-effort discovery of the login node hostname that a user SSHs into.

    We cannot always know this from inside a job, so we check, in order:
    explicit argument, VENVOY_LOGIN_NODE, SLURM_SUBMIT_HOST. If none are set we
    return None and the user must supply it on the connect side.
    """
    if explicit:
        return explicit
    for env_var in ("VENVOY_LOGIN_NODE", "SLURM_SUBMIT_HOST"):
        value = os.environ.get(env_var)
        if value:
            return value
    return None


def _detect_compute_node() -> str:
    """Hostname of the node the job is currently running on."""
    for env_var in ("SLURMD_NODENAME", "HOSTNAME"):
        value = os.environ.get(env_var)
        if value:
            return value
    return socket.gethostname()


class RemoteServer:
    """
    Runs on the compute node (inside a Slurm allocation).

    Starts an sshd inside the venvoy container and prints connection info.
    """

    def __init__(
        self,
        env,
        port: Optional[int] = None,
        bind_address: str = "127.0.0.1",
        login_node: Optional[str] = None,
        extra_mounts: Optional[List[str]] = None,
        authorized_key_files: Optional[List[str]] = None,
        workspace: str = CONTAINER_WORKSPACE,
    ):
        self.env = env
        self.container_manager: ContainerManager = env.container_manager
        self.runtime = self.container_manager.runtime
        self.port = port or _find_free_port()
        self.bind_address = bind_address
        self.login_node = _detect_login_node(login_node)
        self.compute_node = _detect_compute_node()
        self.extra_mounts = extra_mounts or []
        self.authorized_key_files = authorized_key_files
        self.workspace = workspace
        self.user = self._resolve_login_user()
        # Ephemeral working directory on the compute node's filesystem.
        self.workdir = env.config_dir / "remote" / env.name
        self.image_name = self._resolve_image_name()

    def _resolve_login_user(self) -> str:
        """
        SSH username to use when connecting into the container.

        For Apptainer/Singularity, the container runs as the calling user and
        Apptainer synthesizes a matching /etc/passwd entry, so we use the real
        cluster username. For Docker/Podman, the image ships a 'venvoy' user.
        """
        if self.runtime in (ContainerRuntime.APPTAINER, ContainerRuntime.SINGULARITY):
            return getpass.getuser()
        return "venvoy"

    def _resolve_image_name(self) -> str:
        """Determine the published image (or SIF source) to serve."""
        import yaml

        image_name = None
        if self.env.config_file.exists():
            with open(self.env.config_file, "r") as handle:
                config = yaml.safe_load(handle) or {}
            image_name = config.get("image_name")
            if not image_name:
                tag = self.env._get_combined_image_tag(
                    config.get("python_version", self.env.python_version),
                    config.get("r_version", self.env.r_version),
                )
                image_name = f"zaphodbeeblebrox3rd/venvoy:{tag}"
        if not image_name:
            tag = self.env._get_combined_image_tag(
                self.env.python_version, self.env.r_version
            )
            image_name = f"zaphodbeeblebrox3rd/venvoy:{tag}"
        return image_name

    def _collect_authorized_keys(self) -> str:
        """
        Gather public keys that may connect to the container.

        Defaults to the user's existing cluster authorized_keys plus any
        ~/.ssh/*.pub, so the same key they already use to reach the login node
        also authenticates to the container. Explicit files override this.
        """
        keys: List[str] = []
        if self.authorized_key_files:
            sources = [Path(p).expanduser() for p in self.authorized_key_files]
        else:
            ssh_dir = Path.home() / ".ssh"
            sources = [ssh_dir / "authorized_keys"]
            sources.extend(sorted(ssh_dir.glob("*.pub")))

        for source in sources:
            try:
                if source.exists():
                    for line in source.read_text().splitlines():
                        line = line.strip()
                        if line and not line.startswith("#") and line not in keys:
                            keys.append(line)
            except OSError:
                continue

        if not keys:
            raise RemoteError(
                "No SSH public keys found to authorize. Add your laptop's public "
                "key to ~/.ssh/authorized_keys on the cluster, or pass "
                "--pubkey-file <path>."
            )
        return "\n".join(keys) + "\n"

    def _check_sshd_in_image(self) -> None:
        """Verify the image actually ships an SSH server at /usr/sbin/sshd."""
        check = ["test", "-x", "/usr/sbin/sshd"]
        if self.runtime in (ContainerRuntime.APPTAINER, ContainerRuntime.SINGULARITY):
            runtime_bin = (
                "apptainer"
                if self.runtime == ContainerRuntime.APPTAINER
                else "singularity"
            )
            binary = shutil.which(runtime_bin)
            if not binary:
                raise RemoteError(f"{runtime_bin} not found in PATH")
            cmd = [binary, "exec", str(self._sif_path())] + check
        elif self.runtime in (ContainerRuntime.DOCKER, ContainerRuntime.PODMAN):
            runtime_bin = "docker" if self.runtime == ContainerRuntime.DOCKER else "podman"
            binary = shutil.which(runtime_bin)
            if not binary:
                raise RemoteError(f"{runtime_bin} not found in PATH")
            image = self.container_manager._normalize_image_name(self.image_name)
            cmd = [binary, "run", "--rm", image] + check
        else:
            raise RemoteError(f"Unsupported runtime for remote serve: {self.runtime}")

        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise RemoteError(
                f"The image '{self.image_name}' does not contain an SSH server "
                "(/usr/sbin/sshd). The remote bridge requires an updated venvoy "
                "image built with openssh-server. Rebuild and publish the venvoy "
                "images, then run 'venvoy update' and try again."
            )

    def preflight(self) -> None:
        """
        Fail fast, with clear guidance, before starting the server.

        Verifies the compute node has ssh-keygen, that at least one public key
        is available to authorize, and that the image contains an SSH server.
        """
        if not shutil.which("ssh-keygen"):
            raise RemoteError(
                "ssh-keygen not found on the compute node. Load an OpenSSH "
                "module or install openssh-client."
            )

        # Raises RemoteError with guidance if no keys are found.
        self._collect_authorized_keys()

        # Raises RemoteError if the image lacks sshd.
        self._check_sshd_in_image()

    def prepare(self) -> None:
        """Create the sshd working directory, host keys, and config."""
        if self.workdir.exists():
            shutil.rmtree(self.workdir, ignore_errors=True)
        self.workdir.mkdir(parents=True, exist_ok=True)
        self.workdir.chmod(0o755)

        # Host key (ephemeral, regenerated each session).
        host_key = self.workdir / "ssh_host_ed25519_key"
        keygen = shutil.which("ssh-keygen")
        if not keygen:
            raise RemoteError(
                "ssh-keygen not found on the compute node. Load an OpenSSH "
                "module or install openssh-client."
            )
        subprocess.run(
            [keygen, "-t", "ed25519", "-f", str(host_key), "-N", "", "-q"],
            check=True,
        )
        host_key.chmod(0o600)

        # Authorized keys.
        authorized = self.workdir / "authorized_keys"
        authorized.write_text(self._collect_authorized_keys())
        authorized.chmod(0o644)

        # sshd needs a runtime directory; provide one we control.
        pid_file = self.workdir / "sshd.pid"

        sshd_config = self.workdir / "sshd_config"
        sshd_config.write_text(
            "\n".join(
                [
                    f"Port {self.port}",
                    f"ListenAddress {self.bind_address}",
                    f"HostKey {CONTAINER_WORKDIR}/ssh_host_ed25519_key",
                    f"PidFile {CONTAINER_WORKDIR}/sshd.pid",
                    f"AuthorizedKeysFile {CONTAINER_WORKDIR}/authorized_keys",
                    "UsePAM no",
                    "PasswordAuthentication no",
                    "KbdInteractiveAuthentication no",
                    "PermitRootLogin no",
                    "StrictModes no",
                    "AllowTcpForwarding yes",
                    "X11Forwarding no",
                    "PrintMotd no",
                    "Subsystem sftp internal-sftp",
                    "",
                ]
            )
        )
        sshd_config.chmod(0o644)
        # Touch the pid file location so sshd can write it in read-only images.
        pid_file.touch()
        pid_file.chmod(0o644)

    def _bind_flags(self, style: str) -> List[str]:
        """Build volume-bind flags for the chosen runtime style."""
        home = self.env.platform.get_home_mount_path()
        binds = [
            (str(self.workdir), CONTAINER_WORKDIR),
            (home, CONTAINER_HOST_HOME),
            (os.getcwd(), CONTAINER_WORKSPACE),
        ]
        for mount in self.extra_mounts:
            if ":" in mount:
                host_path, container_path = mount.split(":", 1)
                binds.append((host_path, container_path))

        flags: List[str] = []
        flag = "--bind" if style == "apptainer" else "-v"
        for host_path, container_path in binds:
            flags.extend([flag, f"{host_path}:{container_path}"])
        return flags

    def _sif_path(self) -> Path:
        """Resolve (pulling if necessary) the SIF file for the image."""
        sif_name = (
            self.image_name.replace("/", "-").replace(":", "-") + ".si"
        )
        sif_path = self.container_manager.sif_dir / sif_name
        if not sif_path.exists():
            if not self.container_manager.pull_image(self.image_name):
                raise RemoteError(f"Failed to pull image {self.image_name}")
        return sif_path

    def _sshd_argv(self) -> List[str]:
        """The sshd invocation to run inside the container (foreground)."""
        return [
            "/usr/sbin/sshd",
            "-D",
            "-e",
            "-f",
            f"{CONTAINER_WORKDIR}/sshd_config",
        ]

    def build_serve_command(self) -> List[str]:
        """Build the full runtime command that launches sshd in the container."""
        if self.runtime in (ContainerRuntime.APPTAINER, ContainerRuntime.SINGULARITY):
            runtime_bin = (
                "apptainer"
                if self.runtime == ContainerRuntime.APPTAINER
                else "singularity"
            )
            binary = shutil.which(runtime_bin)
            if not binary:
                raise RemoteError(f"{runtime_bin} not found in PATH")
            cmd = [binary, "exec"]
            cmd.extend(self._bind_flags("apptainer"))
            cmd.append(str(self._sif_path()))
            cmd.extend(self._sshd_argv())
            return cmd

        if self.runtime in (ContainerRuntime.DOCKER, ContainerRuntime.PODMAN):
            runtime_bin = "docker" if self.runtime == ContainerRuntime.DOCKER else "podman"
            binary = shutil.which(runtime_bin)
            if not binary:
                raise RemoteError(f"{runtime_bin} not found in PATH")
            container_name = f"{self.env.name}-remote"
            # Best-effort cleanup of a stale container from a prior session.
            subprocess.run(
                [binary, "rm", "-f", container_name],
                capture_output=True,
                check=False,
            )
            image = self.container_manager._normalize_image_name(self.image_name)
            cmd = [
                binary,
                "run",
                "--rm",
                "--name",
                container_name,
                "--network",
                "host",
            ]
            cmd.extend(self._bind_flags("docker"))
            cmd.append(image)
            cmd.extend(self._sshd_argv())
            return cmd

        raise RemoteError(f"Unsupported runtime for remote serve: {self.runtime}")

    def connection_payload(self) -> Dict:
        """The data a laptop needs to connect back."""
        return {
            "v": TOKEN_VERSION,
            "name": self.env.name,
            "login_node": self.login_node,
            "compute_node": self.compute_node,
            "port": self.port,
            "user": self.user,
            "bind": self.bind_address,
            "workspace": self.workspace,
        }

    def token(self) -> str:
        return encode_token(self.connection_payload())

    def print_instructions(self) -> None:
        """Print copy-pasteable connection instructions for the laptop side."""
        payload = self.connection_payload()
        token = self.token()
        login = payload["login_node"] or "<LOGIN_NODE>"

        print("")
        print("=" * 70)
        print("venvoy remote environment is starting")
        print("=" * 70)
        print(f"  environment : {payload['name']}")
        print(f"  runtime     : {self.runtime.value}")
        print(f"  compute node: {payload['compute_node']}")
        print(f"  login node  : {login}")
        print(f"  ssh user    : {payload['user']}")
        print(f"  port        : {payload['port']} (bound to {payload['bind']})")
        print("")
        print("On your LOCAL machine (where Cursor is installed), run:")
        print("")
        print(f"    venvoy connect {token}")
        print("")
        if not payload["login_node"]:
            print(
                "NOTE: the login node hostname is unknown to this job. Either set "
                "VENVOY_LOGIN_NODE before launching, or pass it on the laptop:"
            )
            print(f"    venvoy connect {token} --login-node <LOGIN_NODE>")
            print("")
        print("Keep this job running while you work. Press Ctrl-C to stop it.")
        print("=" * 70)
        print("", flush=True)

    def serve(self) -> int:
        """Prepare and run the sshd in the foreground (blocking)."""
        print("Running preflight checks...", flush=True)
        self.preflight()
        self.prepare()
        command = self.build_serve_command()
        self.print_instructions()
        try:
            result = subprocess.run(command, check=False)
            return result.returncode
        except KeyboardInterrupt:
            print("\nStopping venvoy remote environment...")
            return 0
        finally:
            self._cleanup()

    def _cleanup(self) -> None:
        """Remove the ephemeral working directory (contains host keys)."""
        shutil.rmtree(self.workdir, ignore_errors=True)


class RemoteClient:
    """
    Runs on the user's laptop.

    Writes an SSH config entry with a ProxyJump through the login node and
    launches Cursor Remote-SSH into the container.
    """

    def __init__(
        self,
        payload: Dict,
        login_node: Optional[str] = None,
        alias: Optional[str] = None,
        workspace: Optional[str] = None,
    ):
        self.payload = payload
        self.login_node = login_node or payload.get("login_node")
        self.alias = alias or f"venvoy-{payload.get('name', 'env')}"
        self.workspace = workspace or payload.get("workspace", CONTAINER_WORKSPACE)
        self.ssh_config = Path.home() / ".ssh" / "config"

    def _proxy_jump(self) -> str:
        """Build the ProxyJump chain for the SSH config."""
        user = self.payload["user"]
        compute = self.payload["compute_node"]
        # Loopback bind requires a second hop onto the compute node itself.
        if self.payload.get("bind", "127.0.0.1") == "127.0.0.1":
            return f"{user}@{self.login_node},{user}@{compute}"
        return f"{user}@{self.login_node}"

    def _host_name(self) -> str:
        """Final target host from the perspective of the last jump."""
        if self.payload.get("bind", "127.0.0.1") == "127.0.0.1":
            return "127.0.0.1"
        return self.payload["compute_node"]

    def build_ssh_block(self) -> str:
        """Render the managed SSH config block for this connection."""
        lines = [
            SSH_BLOCK_START.format(alias=self.alias),
            f"Host {self.alias}",
            f"    HostName {self._host_name()}",
            f"    Port {self.payload['port']}",
            f"    User {self.payload['user']}",
            f"    ProxyJump {self._proxy_jump()}",
            "    StrictHostKeyChecking no",
            "    UserKnownHostsFile /dev/null",
            "    LogLevel ERROR",
            SSH_BLOCK_END.format(alias=self.alias),
        ]
        return "\n".join(lines)

    def write_ssh_config(self) -> None:
        """Insert or replace the managed block in ~/.ssh/config."""
        if not self.login_node:
            raise RemoteError(
                "Login node hostname is required. Re-run with "
                "--login-node <LOGIN_NODE> (the host you SSH into to reach the "
                "cluster)."
            )

        self.ssh_config.parent.mkdir(parents=True, exist_ok=True)
        block = self.build_ssh_block()

        existing = ""
        if self.ssh_config.exists():
            existing = self.ssh_config.read_text()

        start = SSH_BLOCK_START.format(alias=self.alias)
        end = SSH_BLOCK_END.format(alias=self.alias)
        if start in existing and end in existing:
            before = existing.split(start)[0].rstrip("\n")
            after = existing.split(end, 1)[1].lstrip("\n")
            parts = [p for p in (before, block, after) if p]
            new_content = "\n\n".join(parts) + "\n"
        else:
            prefix = existing.rstrip("\n")
            new_content = (f"{prefix}\n\n{block}\n" if prefix else f"{block}\n")

        self.ssh_config.write_text(new_content)
        try:
            self.ssh_config.chmod(stat.S_IRUSR | stat.S_IWUSR)
        except OSError:
            pass

    def launch_editor(self, editor: str = "cursor") -> bool:
        """Open the remote container folder in Cursor (or VSCode)."""
        binary = shutil.which(editor)
        if not binary:
            return False
        uri = f"vscode-remote://ssh-remote+{self.alias}{self.workspace}"
        try:
            subprocess.run([binary, "--folder-uri", uri], check=True)
            return True
        except (subprocess.CalledProcessError, OSError):
            return False
