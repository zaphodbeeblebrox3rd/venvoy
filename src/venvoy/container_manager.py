"""
Container runtime abstraction for venvoy
Supports Docker, Apptainer/Singularity, and Podman for HPC compatibility
"""

import os
import shutil
import subprocess
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional

from .platform_detector import PlatformDetector


class ContainerRuntime(Enum):
    """Supported container runtimes"""

    DOCKER = "docker"
    APPTAINER = "apptainer"
    SINGULARITY = "singularity"
    PODMAN = "podman"


class ContainerManager:
    """Abstracts container operations across different runtimes"""

    def __init__(self):
        self.platform = PlatformDetector()
        self.runtime = self._detect_best_runtime()
        self.client = None
        # Create SIF storage directory in ~/.venvoy
        # If running inside a container, use /tmp (SIF files are typically temporary)
        # and we're unlikely to create Apptainer/Singularity containers from inside a venvoy container
        if self._is_inside_container():
            self.sif_dir = Path("/tmp") / ".venvoy" / "si"
        else:
            # Running on host, use normal home directory
            self.sif_dir = Path.home() / ".venvoy" / "si"

        try:
            self.sif_dir.mkdir(parents=True, exist_ok=True)
        except (PermissionError, OSError):
            # If we can't create the directory, use /tmp as fallback
            # This should rarely happen, but provides a safety net
            self.sif_dir = Path("/tmp") / ".venvoy" / "si"
            self.sif_dir.mkdir(parents=True, exist_ok=True)

    def _detect_best_runtime(self) -> ContainerRuntime:
        """Detect the best available container runtime for the environment"""
        # First, check if we're running inside a container and have host runtime info
        host_runtime = os.environ.get("VENVOY_HOST_RUNTIME")
        if host_runtime:
            # Map host runtime string to ContainerRuntime enum
            runtime_map = {
                "docker": ContainerRuntime.DOCKER,
                "apptainer": ContainerRuntime.APPTAINER,
                "singularity": ContainerRuntime.SINGULARITY,
                "podman": ContainerRuntime.PODMAN,
            }
            if host_runtime in runtime_map:
                return runtime_map[host_runtime]

        is_hpc = self._is_hpc_environment()

        # Check for HPC-specific runtimes first (in HPC environments)
        if is_hpc:
            if self._check_runtime_available(ContainerRuntime.APPTAINER):
                return ContainerRuntime.APPTAINER
            elif self._check_runtime_available(ContainerRuntime.SINGULARITY):
                return ContainerRuntime.SINGULARITY
            elif self._check_runtime_available(ContainerRuntime.PODMAN):
                return ContainerRuntime.PODMAN

        # Check for all runtimes in order of preference
        # Prefer Apptainer > Singularity > Docker > Podman
        if self._check_runtime_available(ContainerRuntime.APPTAINER):
            return ContainerRuntime.APPTAINER
        elif self._check_runtime_available(ContainerRuntime.SINGULARITY):
            return ContainerRuntime.SINGULARITY
        elif self._check_runtime_available(ContainerRuntime.DOCKER):
            return ContainerRuntime.DOCKER
        elif self._check_runtime_available(ContainerRuntime.PODMAN):
            return ContainerRuntime.PODMAN

        # If no runtime is available (e.g., running inside a container),
        # try to detect the runtime from environment variables
        runtime_from_env = self._detect_runtime_from_environment()
        if runtime_from_env:
            return runtime_from_env

        raise RuntimeError(
            "No supported container runtime found. "
            "Please install Docker, Apptainer, Singularity, or Podman."
        )

    def _is_hpc_environment(self) -> bool:
        """Detect if we're in an HPC environment"""
        # Check for common HPC environment variables
        hpc_indicators = [
            "SLURM_JOB_ID",
            "PBS_JOBID",
            "LSB_JOBID",
            "SGE_JOB_ID",
            "HOSTNAME",  # Many HPC systems have specific hostname patterns
        ]

        for indicator in hpc_indicators:
            if indicator in os.environ:
                return True

        # Check hostname patterns
        hostname = os.environ.get("HOSTNAME", "")
        hpc_patterns = ["login", "compute", "node", "hpc", "cluster"]
        if any(pattern in hostname.lower() for pattern in hpc_patterns):
            return True

        return False

    def _is_inside_container(self) -> bool:
        """Detect if we're running inside a container"""
        # Check for container-specific environment variables
        if any(
            key in os.environ
            for key in [
                "SINGULARITY_NAME",
                "SINGULARITY_CONTAINER",
                "APPTAINER_NAME",
                "APPTAINER_CONTAINER",
                "DOCKER_CONTAINER",
                "PODMAN_CONTAINER",
            ]
        ):
            return True

        # Check for container-specific files
        if os.path.exists("/.dockerenv"):
            return True

        # Check cgroup for container indicators
        if os.path.exists("/proc/1/cgroup"):
            try:
                with open("/proc/1/cgroup", "r") as f:
                    cgroup_content = f.read()
                    if any(
                        indicator in cgroup_content
                        for indicator in ["docker", "containerd", "crio", "podman"]
                    ):
                        return True
            except (IOError, OSError):
                pass

        # Check if we're in a venvoy container (workspace mount is a strong indicator)
        if os.path.exists("/workspace") and os.path.exists("/home/venvoy"):
            return True

        return False

    def _detect_runtime_from_environment(self) -> Optional[ContainerRuntime]:
        """Detect container runtime from environment variables when running inside a container"""
        # Check for common environment variables that indicate the runtime
        if "SINGULARITY_NAME" in os.environ or "SINGULARITY_CONTAINER" in os.environ:
            return ContainerRuntime.SINGULARITY
        elif "APPTAINER_NAME" in os.environ or "APPTAINER_CONTAINER" in os.environ:
            return ContainerRuntime.APPTAINER
        elif (
            "DOCKER_CONTAINER" in os.environ
            or "container" in os.environ.get("HOSTNAME", "").lower()
        ):
            return ContainerRuntime.DOCKER
        elif "PODMAN_CONTAINER" in os.environ:
            return ContainerRuntime.PODMAN

        # Check if we're in a container by looking for container-specific files
        if os.path.exists("/.dockerenv"):
            return ContainerRuntime.DOCKER
        elif (
            os.path.exists("/proc/1/cgroup")
            and "docker" in open("/proc/1/cgroup").read()
        ):
            return ContainerRuntime.DOCKER
        elif (
            os.path.exists("/proc/1/cgroup")
            and "containerd" in open("/proc/1/cgroup").read()
        ):
            return ContainerRuntime.DOCKER

        return None

    def _check_runtime_available(self, runtime: ContainerRuntime) -> bool:
        """Check if a specific runtime is available and accessible"""
        try:
            if runtime == ContainerRuntime.DOCKER:
                # Check if docker command exists
                docker_path = shutil.which("docker")
                if not docker_path:
                    return False
                # Check if docker command works
                result = subprocess.run(
                    [docker_path, "--version"], capture_output=True, check=True
                )
                # Also check if Docker daemon is accessible
                daemon_check = subprocess.run(
                    [docker_path, "info"], capture_output=True, check=True
                )
                return result.returncode == 0 and daemon_check.returncode == 0
            elif runtime == ContainerRuntime.APPTAINER:
                apptainer_path = shutil.which("apptainer")
                if not apptainer_path:
                    return False
                result = subprocess.run(
                    [apptainer_path, "--version"], capture_output=True, check=True
                )
                return result.returncode == 0
            elif runtime == ContainerRuntime.SINGULARITY:
                singularity_path = shutil.which("singularity")
                if not singularity_path:
                    return False
                result = subprocess.run(
                    [singularity_path, "--version"],
                    capture_output=True,
                    text=True,
                    check=True,
                )
                return result.returncode == 0
            elif runtime == ContainerRuntime.PODMAN:
                podman_path = shutil.which("podman")
                if not podman_path:
                    return False
                result = subprocess.run(
                    [podman_path, "--version"], capture_output=True, check=True
                )
                return result.returncode == 0
            else:
                return False
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False

    def get_runtime_info(self) -> Dict[str, str]:
        """Get information about the current runtime"""
        # Check if we're using host runtime info
        host_runtime = os.environ.get("VENVOY_HOST_RUNTIME")
        if host_runtime:
            # We're running inside a container with host runtime info
            return {
                "runtime": self.runtime.value,
                "version": f"Host: {host_runtime}",
                "is_hpc": self._is_hpc_environment(),
            }

        try:
            if self.runtime == ContainerRuntime.DOCKER:
                result = subprocess.run(
                    ["docker", "--version"], capture_output=True, text=True, check=True
                )
                version = result.stdout.strip()
            elif self.runtime == ContainerRuntime.APPTAINER:
                result = subprocess.run(
                    ["apptainer", "--version"],
                    capture_output=True,
                    text=True,
                    check=True,
                )
                version = result.stdout.strip()
            elif self.runtime == ContainerRuntime.SINGULARITY:
                result = subprocess.run(
                    ["singularity", "--version"],
                    capture_output=True,
                    text=True,
                    check=True,
                )
                version = result.stdout.strip()
            elif self.runtime == ContainerRuntime.PODMAN:
                result = subprocess.run(
                    ["podman", "--version"], capture_output=True, text=True, check=True
                )
                version = result.stdout.strip()
            else:
                version = "Unknown"

            return {
                "runtime": self.runtime.value,
                "version": version,
                "is_hpc": self._is_hpc_environment(),
            }
        except subprocess.CalledProcessError:
            return {
                "runtime": self.runtime.value,
                "version": "Unknown",
                "is_hpc": self._is_hpc_environment(),
            }

    def pull_image(self, image_name: str) -> bool:
        """Pull a container image"""
        try:
            if self.runtime == ContainerRuntime.DOCKER:
                docker_path = shutil.which("docker")
                if not docker_path:
                    raise FileNotFoundError("docker not found in PATH")
                subprocess.run([docker_path, "pull", image_name], check=True)
            elif self.runtime == ContainerRuntime.APPTAINER:
                apptainer_path = shutil.which("apptainer")
                if not apptainer_path:
                    raise FileNotFoundError("apptainer not found in PATH")
                # Sanitize image name for SIF file (replace / and : with -)
                sif_name = image_name.replace("/", "-").replace(":", "-") + ".si"
                sif_path = self.sif_dir / sif_name
                subprocess.run(
                    [apptainer_path, "pull", str(sif_path), f"docker://{image_name}"],
                    check=True,
                )
            elif self.runtime == ContainerRuntime.SINGULARITY:
                singularity_path = shutil.which("singularity")
                if not singularity_path:
                    raise FileNotFoundError("singularity not found in PATH")
                # Sanitize image name for SIF file (replace / and : with -)
                sif_name = image_name.replace("/", "-").replace(":", "-") + ".si"
                sif_path = self.sif_dir / sif_name
                subprocess.run(
                    [singularity_path, "pull", str(sif_path), f"docker://{image_name}"],
                    check=True,
                )
            elif self.runtime == ContainerRuntime.PODMAN:
                podman_path = shutil.which("podman")
                if not podman_path:
                    raise FileNotFoundError("podman not found in PATH")
                # Podman requires fully qualified image names (docker.io/ prefix)
                if not image_name.startswith("docker.io/") and "/" in image_name:
                    podman_image_name = f"docker.io/{image_name}"
                else:
                    podman_image_name = image_name
                subprocess.run([podman_path, "pull", podman_image_name], check=True)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            print(f"Failed to pull image {image_name}: {e}")
            return False

    def run_container(
        self,
        image: str,
        name: str,
        command: Optional[str] = None,
        volumes: Optional[Dict[str, str]] = None,
        ports: Optional[Dict[str, str]] = None,
        environment: Optional[Dict[str, str]] = None,
        detach: bool = False,
    ):
        """Run a container with the specified parameters"""
        try:
            if self.runtime == ContainerRuntime.DOCKER:
                # For Docker, we need to return a container object
                # Import docker module here to avoid import issues
                try:
                    import docker

                    client = docker.from_env()
                    container = client.containers.run(
                        image=image,
                        name=name,
                        command=command,
                        volumes=volumes,
                        ports=ports,
                        environment=environment,
                        detach=detach,
                        stdin_open=True,
                        tty=True,
                        remove=True,
                    )
                    return container
                except ImportError:
                    # Fallback to subprocess if docker module not available
                    cmd = self._build_run_command(
                        image, name, command, volumes, ports, environment, detach
                    )
                    subprocess.run(cmd, check=True)
                    # Return a mock container object for compatibility

                    class MockContainer:
                        def __init__(self, name):
                            self.name = name

                    return MockContainer(name)
            else:
                # For other runtimes, use subprocess
                cmd = self._build_run_command(
                    image, name, command, volumes, ports, environment, detach
                )
                # Run with proper output handling
                result = subprocess.run(cmd, check=True, capture_output=True)
                # Validate that the container started successfully
                # check=True will raise on failure, but we validate output for debugging
                if result.stderr:
                    error_output = (
                        result.stderr.decode()
                        if isinstance(result.stderr, bytes)
                        else result.stderr
                    )
                    # Log warnings but don't fail if check=True passed
                    if "warning" in error_output.lower():
                        print(f"⚠️  Warning starting container: {error_output}")
                # Return a mock container object for compatibility

                class MockContainer:
                    def __init__(self, name):
                        self.name = name

                return MockContainer(name)
        except subprocess.CalledProcessError as e:
            print(f"Failed to run container: {e}")
            return False

    def _build_run_command(
        self,
        image: str,
        name: str,
        command: Optional[str] = None,
        volumes: Optional[Dict[str, str]] = None,
        ports: Optional[Dict[str, str]] = None,
        environment: Optional[Dict[str, str]] = None,
        detach: bool = False,
    ) -> List[str]:
        """Build the appropriate run command for the current runtime"""
        if self.runtime == ContainerRuntime.DOCKER:
            return self._build_docker_run_command(
                image, name, command, volumes, ports, environment, detach
            )
        elif self.runtime == ContainerRuntime.APPTAINER:
            return self._build_apptainer_run_command(
                image, name, command, volumes, ports, environment, detach
            )
        elif self.runtime == ContainerRuntime.SINGULARITY:
            return self._build_singularity_run_command(
                image, name, command, volumes, ports, environment, detach
            )
        elif self.runtime == ContainerRuntime.PODMAN:
            return self._build_podman_run_command(
                image, name, command, volumes, ports, environment, detach
            )
        else:
            raise RuntimeError(f"Unsupported runtime: {self.runtime}")

    def _build_docker_run_command(
        self,
        image: str,
        name: str,
        command: Optional[str] = None,
        volumes: Optional[Dict[str, str]] = None,
        ports: Optional[Dict[str, str]] = None,
        environment: Optional[Dict[str, str]] = None,
        detach: bool = False,
    ) -> List[str]:
        """Build Docker run command"""
        cmd = ["docker", "run"]

        if name:
            cmd.extend(["--name", name])

        if detach:
            cmd.append("-d")

        if volumes:
            for host_path, container_path in volumes.items():
                cmd.extend(["-v", f"{host_path}:{container_path}"])

        if ports:
            for host_port, container_port in ports.items():
                cmd.extend(["-p", f"{host_port}:{container_port}"])

        if environment:
            for key, value in environment.items():
                cmd.extend(["-e", f"{key}={value}"])

        cmd.append(image)

        if command:
            cmd.extend(["sh", "-c", command])

        return cmd

    def _build_apptainer_run_command(
        self,
        image: str,
        name: str,
        command: Optional[str] = None,
        volumes: Optional[Dict[str, str]] = None,
        ports: Optional[Dict[str, str]] = None,
        environment: Optional[Dict[str, str]] = None,
        detach: bool = False,
    ) -> List[str]:
        """Build Apptainer run command"""
        # Apptainer uses .sif files, so we need to check if the image exists
        # Sanitize image name for SIF file (replace / and : with -)
        sif_name = image.replace("/", "-").replace(":", "-") + ".si"
        image_path = self.sif_dir / sif_name
        if not image_path.exists():
            # Pull the image first
            self.pull_image(image)

        cmd = ["apptainer", "run"]

        if volumes:
            for host_path, container_path in volumes.items():
                cmd.extend(["--bind", f"{host_path}:{container_path}"])

        if environment:
            for key, value in environment.items():
                cmd.extend(["--env", f"{key}={value}"])

        cmd.append(str(image_path))

        if command:
            cmd.extend(["sh", "-c", command])

        return cmd

    def _build_singularity_run_command(
        self,
        image: str,
        name: str,
        command: Optional[str] = None,
        volumes: Optional[Dict[str, str]] = None,
        ports: Optional[Dict[str, str]] = None,
        environment: Optional[Dict[str, str]] = None,
        detach: bool = False,
    ) -> List[str]:
        """Build Singularity run command (similar to Apptainer)"""
        # Use docker:// reference for Singularity
        docker_image = f"docker://{image}"

        cmd = ["singularity", "exec"]

        if volumes:
            for host_path, container_path in volumes.items():
                cmd.extend(["--bind", f"{host_path}:{container_path}"])

        if environment:
            for key, value in environment.items():
                cmd.extend(["--env", f"{key}={value}"])

        cmd.append(docker_image)

        if command:
            cmd.extend(["/bin/bash", "-c", command])
        else:
            # Use the container's entrypoint
            cmd.append("/usr/local/bin/venvoy-entrypoint")

        return cmd

    def _build_podman_run_command(
        self,
        image: str,
        name: str,
        command: Optional[str] = None,
        volumes: Optional[Dict[str, str]] = None,
        ports: Optional[Dict[str, str]] = None,
        environment: Optional[Dict[str, str]] = None,
        detach: bool = False,
    ) -> List[str]:
        """Build Podman run command (similar to Docker)"""
        cmd = ["podman", "run"]

        if name:
            cmd.extend(["--name", name])

        if detach:
            cmd.append("-d")

        if volumes:
            for host_path, container_path in volumes.items():
                cmd.extend(["-v", f"{host_path}:{container_path}"])

        if ports:
            for host_port, container_port in ports.items():
                cmd.extend(["-p", f"{host_port}:{container_port}"])

        if environment:
            for key, value in environment.items():
                cmd.extend(["-e", f"{key}={value}"])

        cmd.append(image)

        if command:
            cmd.extend(["sh", "-c", command])

        return cmd

    def stop_container(self, name: str) -> bool:
        """Stop a running container"""
        try:
            if self.runtime == ContainerRuntime.DOCKER:
                subprocess.run(["docker", "stop", name], check=True)
            elif self.runtime == ContainerRuntime.PODMAN:
                subprocess.run(["podman", "stop", name], check=True)
            # Apptainer/Singularity containers are typically not long-running
            # so stopping is less relevant
            return True
        except subprocess.CalledProcessError as e:
            print(f"Failed to stop container {name}: {e}")
            return False

    def list_containers(self, all_containers: bool = False) -> List[Dict]:
        """List containers"""
        try:
            if self.runtime == ContainerRuntime.DOCKER:
                docker_path = shutil.which("docker")
                if not docker_path:
                    raise FileNotFoundError("docker not found in PATH")
                cmd = [
                    docker_path,
                    "ps",
                    "--format",
                    "{{.ID}}|{{.Image}}|{{.Command}}|{{.Created}}|{{.Status}}|{{.Ports}}|{{.Names}}",
                ]
                if all_containers:
                    cmd.insert(2, "-a")
                result = subprocess.run(cmd, capture_output=True, text=True, check=True)
                return self._parse_docker_ps_output(result.stdout)
            elif self.runtime == ContainerRuntime.PODMAN:
                podman_path = shutil.which("podman")
                if not podman_path:
                    raise FileNotFoundError("podman not found in PATH")
                cmd = [
                    podman_path,
                    "ps",
                    "--format",
                    "{{.ID}}|{{.Image}}|{{.Command}}|{{.Created}}|{{.Status}}|{{.Ports}}|{{.Names}}",
                ]
                if all_containers:
                    cmd.insert(2, "-a")
                result = subprocess.run(cmd, capture_output=True, text=True, check=True)
                return self._parse_docker_ps_output(
                    result.stdout
                )  # Same format as Docker
            else:
                # Apptainer/Singularity doesn't have persistent containers in the same way
                return []
        except (subprocess.CalledProcessError, FileNotFoundError):
            return []

    def _parse_docker_ps_output(self, output: str) -> List[Dict]:
        """Parse Docker/Podman ps output into structured data (pipe-delimited format)"""
        lines = output.strip().split("\n")
        if not lines or not lines[0].strip():
            return []

        containers = []
        for line in lines:
            if not line.strip():
                continue
            # Format: ID|IMAGE|COMMAND|CREATED|STATUS|PORTS|NAMES
            parts = line.split("|")
            if len(parts) >= 7:
                container = {
                    "id": parts[0].strip(),
                    "image": parts[1].strip(),
                    "command": parts[2].strip(),
                    "created": parts[3].strip(),
                    "status": parts[4].strip(),
                    "ports": parts[5].strip(),
                    "name": parts[6].strip(),
                }
                containers.append(container)

        return containers

    def build_image(self, dockerfile_path: Path, tag: str, context_path: Path) -> bool:
        """Build a container image"""
        try:
            if self.runtime == ContainerRuntime.DOCKER:
                subprocess.run(
                    [
                        "docker",
                        "build",
                        "-t",
                        tag,
                        "-",
                        str(dockerfile_path),
                        str(context_path),
                    ],
                    check=True,
                )
            elif self.runtime == ContainerRuntime.PODMAN:
                subprocess.run(
                    [
                        "podman",
                        "build",
                        "-t",
                        tag,
                        "-",
                        str(dockerfile_path),
                        str(context_path),
                    ],
                    check=True,
                )
            elif self.runtime in [
                ContainerRuntime.APPTAINER,
                ContainerRuntime.SINGULARITY,
            ]:
                # Convert Dockerfile to Singularity definition file
                def_file = self._convert_dockerfile_to_singularity(
                    dockerfile_path, context_path
                )
                build_cmd = (
                    "apptainer"
                    if self.runtime == ContainerRuntime.APPTAINER
                    else "singularity"
                )
                subprocess.run(
                    [build_cmd, "build", f"{tag}.sif", str(def_file)], check=True
                )
            return True
        except subprocess.CalledProcessError as e:
            print(f"Failed to build image: {e}")
            return False

    def _convert_dockerfile_to_singularity(
        self, dockerfile_path: Path, context_path: Path
    ) -> Path:
        """Convert Dockerfile to Singularity definition file"""
        # This is a simplified conversion - in practice, you'd want a more robust converter
        def_file = context_path / "Singularity.de"

        with open(dockerfile_path, "r") as f:
            dockerfile_content = f.read()  # noqa: F841

        # Basic conversion - this would need to be more sophisticated
        singularity_content = """Bootstrap: docker
From: {self._extract_base_image(dockerfile_content)}

%post
{dockerfile_content.replace('FROM', '# FROM').replace('RUN', '').replace('COPY', '# COPY')}

%environment
export PYTHONUNBUFFERED=1
export PYTHONDONTWRITEBYTECODE=1

%runscript
python "$@"
"""

        with open(def_file, "w") as f:
            f.write(singularity_content)

        return def_file

    def _extract_base_image(self, dockerfile_content: str) -> str:
        """Extract base image from Dockerfile content"""
        for line in dockerfile_content.split("\n"):
            if line.strip().startswith("FROM"):
                return line.strip().split()[1]
        return "ubuntu:20.04"  # Default fallback
