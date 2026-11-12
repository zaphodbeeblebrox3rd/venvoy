"""
Core venvoy environment management

IMPORTANT: This module manages Docker containers. The key principle is:
- Host operations: Docker management, file system operations, editor launching
- Container operations: Package installation, dependency resolution, Python execution

All package management (mamba, uv, pip) happens INSIDE containers, not on the host.
"""

import json
import os
import shutil
import subprocess
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from .container_manager import ContainerManager, ContainerRuntime
from .platform_detector import PlatformDetector

# Rollback: set False to restore the previous three-branch run() path.
USE_UNIFIED_RUN = True


def _package_version() -> str:
    """Snapshot version from the package, not a copied literal."""
    from venvoy import __version__

    return __version__


class VenvoyEnvironment:
    """Manages portable Python and R environments"""

    def __init__(
        self,
        name: str = "venvoy-env",
        python_version: str = "3.11",
        runtime: str = "python",
        r_version: str = "4.4",
    ):
        self.name = name
        self.runtime = runtime  # "python", "r", or "mixed"
        self.python_version = python_version
        self.r_version = r_version
        self.platform = PlatformDetector()
        self.container_manager = ContainerManager()
        self.config_dir = Path.home() / ".venvoy"
        self.env_dir = self.config_dir / "environments" / name
        self.config_file = self.env_dir / "config.yaml"

        # Auto-saved snapshots live in ~/.venvoy/projects/<name>
        self.projects_dir = self.config_dir / "projects" / name

        # Ensure directories exist
        self.config_dir.mkdir(exist_ok=True)
        (self.config_dir / "environments").mkdir(exist_ok=True)
        (self.config_dir / "projects").mkdir(exist_ok=True)
        # Create ~/.venvoy/home directory for container mount
        venvoy_home_dir = self.config_dir / "home"
        venvoy_home_dir.mkdir(exist_ok=True)
        # Set permissions: 755 (rwxr-xr-x) - user can read/write/execute, group/others can read/execute
        venvoy_home_dir.chmod(0o755)
        self.projects_dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _ensure_host_home_writable(host_home_path: str):
        """
        Ensure the host home mount point is writable by current user.
        If the directory is owned by root or not writable, attempt to chown recursively.
        """
        try:
            p = Path(host_home_path)
            if not p.exists():
                p.mkdir(parents=True, exist_ok=True)
            st = p.stat()
            # Always attempt to align ownership to current user (recursive) to avoid root-owned leftovers
            try:
                os.chown(host_home_path, os.getuid(), os.getgid())
            except PermissionError:
                pass
            # Recursively fix child entries if root-owned
            if st.st_uid == 0 or not os.access(host_home_path, os.W_OK):
                for root, dirs, files in os.walk(host_home_path):
                    for d in dirs:
                        full = Path(root) / d
                        try:
                            os.chown(full, os.getuid(), os.getgid())
                        except PermissionError:
                            pass
                    for f in files:
                        full = Path(root) / f
                        try:
                            os.chown(full, os.getuid(), os.getgid())
                        except PermissionError:
                            pass
            p.chmod(0o755)
        except PermissionError:
            print(f"⚠️  Warning: Cannot change ownership/permissions for {host_home_path}")
        except Exception as e:
            print(f"⚠️  Warning: Unexpected error ensuring host-home writable: {e}")

    @staticmethod
    def _get_combined_image_tag(python_version: str, r_version: str) -> str:
        """
        Map Python and R version pairs to combined image tags.
        
        Valid combinations:
        - Python 3.13 / R 4.5
        - Python 3.12 / R 4.4
        - Python 3.11 / R 4.3
        - Python 3.11 / R 4.2
        - Python 3.10 / R 4.2
        
        Args:
            python_version: Python version string (e.g., "3.13")
            r_version: R version string (e.g., "4.5")
            
        Returns:
            Image tag string (e.g., "python3.13-r4.5")
            
        Raises:
            ValueError: If the combination is not valid
        """
        # Define valid version pairs
        valid_pairs = {
            ("3.13", "4.5"): "python3.13-r4.5",
            ("3.12", "4.4"): "python3.12-r4.4",
            ("3.11", "4.3"): "python3.11-r4.3",
            ("3.11", "4.2"): "python3.11-r4.2",
            ("3.10", "4.2"): "python3.10-r4.2",
        }
        
        pair = (python_version, r_version)
        if pair in valid_pairs:
            return valid_pairs[pair]
        
        # If exact match not found, try to find by Python version only
        # (for backward compatibility when only Python is specified)
        python_only_matches = {
            "3.13": "python3.13-r4.5",
            "3.12": "python3.12-r4.4",
            "3.11": "python3.11-r4.3",  # Default to 4.3 for 3.11
            "3.10": "python3.10-r4.2",
        }
        
        if python_version in python_only_matches:
            return python_only_matches[python_version]
        
        # If still not found, raise error with helpful message
        valid_combinations = "\n".join(
            f"  - Python {py} / R {r}" for (py, r) in valid_pairs.keys()
        )
        raise ValueError(
            f"Invalid Python/R version combination: Python {python_version} / R {r_version}\n"
            f"Valid combinations are:\n{valid_combinations}\n"
            f"Please specify a valid combination."
        )

    def initialize(
        self,
        force: bool = False,
        editor_type: str = "none",
        editor_available: bool = False,
    ):
        """Initialize a new venvoy environment"""
        if self.env_dir.exists() and not force:
            raise RuntimeError(
                f"Environment '{self.name}' already exists at {self.env_dir}. "
                "This directory contains your environment configuration, Dockerfile, and requirements. "
                "Use --force to reinitialize and overwrite the existing environment."
            )

        print(f"🚀 Initializing venvoy environment: {self.name}")

        # Create environment directory
        self.env_dir.mkdir(parents=True, exist_ok=True)
        self.projects_dir.mkdir(parents=True, exist_ok=True)

        # Get combined image tag based on Python/R version pair
        # All images now include both Python and R
        try:
            image_tag = self._get_combined_image_tag(self.python_version, self.r_version)
            image_name = f"zaphodbeeblebrox3rd/venvoy:{image_tag}"
            if self.runtime == "python":
                print(f"📦 Setting up Python {self.python_version} environment (with R {self.r_version})...")
            elif self.runtime == "r":
                print(f"📊 Setting up R {self.r_version} environment (with Python {self.python_version})...")
            else:
                print(f"🚀 Setting up Python {self.python_version} / R {self.r_version} environment...")
        except ValueError as e:
            raise ValueError(str(e))

        self._ensure_image_available(image_name)

        # Log runtime information for debugging
        runtime_info = self.container_manager.get_runtime_info()
        print(f"🔧 Using {runtime_info['runtime']} {runtime_info['version']}")
        if runtime_info["is_hpc"]:
            print(
                f"🏢 HPC environment detected - using {runtime_info['runtime']} for best compatibility"
            )

        # Check for existing environment exports but don't prompt during init
        exports = self.list_environment_exports()
        selected_export = None

        if exports:
            # Use the most recent export automatically
            selected_export = exports[0]["file"]  # First one is most recent
            print(
                f"🔄 Found {len(exports)} previous exports, using most recent: {selected_export.name}"
            )
            self.restore_from_environment_export(selected_export)
        else:
            # Create new environment
            print("🆕 Creating new environment...")

            # Create requirements files
            (self.env_dir / "requirements.txt").touch()
            (self.env_dir / "requirements-dev.txt").touch()

        # Create configuration
        config = {
            "name": self.name,
            "runtime": self.runtime,
            "python_version": self.python_version,
            "r_version": self.r_version,
            "created": datetime.now().isoformat(),
            "platform": self.platform.detect(),
            "image_name": image_name,
            "packages": [],
            "dev_packages": [],
            "editor_type": editor_type,
            "editor_available": editor_available,
            # Keep backward compatibility
            "vscode_available": editor_available and editor_type == "vscode",
            "restored_from": selected_export.name if selected_export else None,
        }

        with open(self.config_file, "w") as f:
            yaml.safe_dump(config, f, default_flow_style=False)

        # Copy package monitor script to environment directory
        monitor_script = Path(__file__).parent / "templates" / "package_monitor.py"
        target_script = self.env_dir / "package_monitor.py"
        if monitor_script.exists():
            import shutil

            shutil.copy2(monitor_script, target_script)

        print(f"✅ Environment '{self.name}' ready!")
        if selected_export:
            print(f"🔄 Restored from: {selected_export.name}")
        else:
            print("🆕 New environment created")

    def _find_docker_command(self) -> str:
        """Find the Docker command with proper PATH handling"""
        # Common Docker installation paths
        common_paths = [
            "/usr/local/bin/docker",
            "/usr/bin/docker",
            "/opt/homebrew/bin/docker",
            shutil.which("docker"),
        ]

        for docker_path in common_paths:
            if docker_path and Path(docker_path).exists():
                return docker_path

        raise RuntimeError(
            "Docker not found. Please install Docker and ensure it's in your PATH."
        )

    def _run_docker_command(
        self, args: List[str], **kwargs
    ) -> subprocess.CompletedProcess:
        """Run a Docker command with proper PATH handling"""
        docker_cmd = self._find_docker_command()
        full_command = [docker_cmd] + args

        # Ensure we have a proper environment with PATH
        env = os.environ.copy()
        if "/usr/local/bin" not in env.get("PATH", ""):
            env["PATH"] = f"/usr/local/bin:{env.get('PATH', '')}"

        return subprocess.run(full_command, env=env, **kwargs)

    def _ensure_image_available(self, image_name: str):
        """Ensure the venvoy image is available locally"""
        runtime_info = self.container_manager.get_runtime_info()
        host_runtime = os.environ.get("VENVOY_HOST_RUNTIME")

        # Check if we're running inside a container and the runtime isn't available
        # In this case, assume the bootstrap script on the host has handled image availability
        if host_runtime:
            runtime_available = False
            if runtime_info["runtime"] == "docker":
                runtime_available = shutil.which("docker") is not None
            elif runtime_info["runtime"] == "podman":
                runtime_available = shutil.which("podman") is not None
            elif runtime_info["runtime"] in ["apptainer", "singularity"]:
                runtime_available = shutil.which(runtime_info["runtime"]) is not None

            if not runtime_available:
                # Running inside container without runtime available - assume host handles it
                print("✅ Environment availability handled by host runtime")
                return

        if runtime_info["runtime"] in ["apptainer", "singularity"]:
            # For Apptainer/Singularity, check if SIF file exists
            # Sanitize image name for SIF file (replace / and : with -)
            sif_name = image_name.replace("/", "-").replace(":", "-") + ".si"
            sif_file = self.container_manager.sif_dir / sif_name
            if not sif_file.exists():
                print("⬇️  Downloading environment (one-time setup)...")
                if self.container_manager.pull_image(image_name):
                    print("✅ Environment ready")
                else:
                    raise RuntimeError("Failed to download environment")
            else:
                print("✅ Environment already available")
        else:
            # For Docker/Podman, use container manager's runtime-agnostic methods
            # Check if image exists using the detected runtime
            try:
                runtime = self.container_manager.runtime
                if runtime == ContainerRuntime.DOCKER:
                    docker_path = shutil.which("docker")
                    if not docker_path:
                        raise FileNotFoundError("docker not found")
                    # Normalize image name as safety measure (in case docker is actually Podman wrapper)
                    normalized_name = self.container_manager._normalize_image_name(image_name)
                    result = subprocess.run(
                        [docker_path, "image", "inspect", normalized_name],
                        capture_output=True,
                        check=True,
                    )
                    # Validate that image inspection returned valid JSON
                    # check=True will raise on failure, but we validate output
                    if result.stdout:
                        try:
                            json.loads(
                                result.stdout.decode()
                                if isinstance(result.stdout, bytes)
                                else result.stdout
                            )
                        except (json.JSONDecodeError, AttributeError):
                            # Not critical, but log if output is unexpected
                            pass
                elif runtime == ContainerRuntime.PODMAN:
                    podman_path = shutil.which("podman")
                    if not podman_path:
                        raise FileNotFoundError("podman not found")
                    # Use ContainerManager's normalization method for consistency
                    podman_image_name = self.container_manager._normalize_image_name(image_name)
                    result = subprocess.run(
                        [podman_path, "image", "inspect", podman_image_name],
                        capture_output=True,
                        check=True,
                    )
                    # Validate that image inspection returned valid JSON
                    # check=True will raise on failure, but we validate output
                    if result.stdout:
                        try:
                            json.loads(
                                result.stdout.decode()
                                if isinstance(result.stdout, bytes)
                                else result.stdout
                            )
                        except (json.JSONDecodeError, AttributeError):
                            # Not critical, but log if output is unexpected
                            pass
                else:
                    # For other runtimes, use container manager's pull_image which handles it
                    raise subprocess.CalledProcessError(1, "check")

            except (subprocess.CalledProcessError, FileNotFoundError):
                # Image doesn't exist or runtime not available, pull it
                print("⬇️  Downloading environment (one-time setup)...")
                if self.container_manager.pull_image(image_name):
                    print("✅ Environment ready")
                else:
                    raise RuntimeError("Failed to download environment")

    def _create_dockerfile(self):
        """Create Dockerfile for the environment"""
        dockerfile_content = """# venvoy environment: {self.name}
# Python version: {self.python_version}
# Generated on: {datetime.now().isoformat()}

FROM {self.platform.get_base_image(self.python_version)}

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PIP_NO_CACHE_DIR=1
ENV PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies
RUN apt-get update && apt-get install -y \\
    build-essential \\
    curl \\
    git \\
    wget \\
    vim \\
    && rm -rf /var/lib/apt/lists/* \\
    && apt-get clean

# Install uv for ultra-fast Python package management
RUN pip install --no-cache-dir uv

# Set working directory
WORKDIR /workspace

# Copy requirements if they exist
COPY requirements*.txt ./
COPY vendor/ ./vendor/

# Copy package monitor script
COPY package_monitor.py /usr/local/bin/package_monitor.py
RUN chmod +x /usr/local/bin/package_monitor.py

# Install common AI/ML packages using UV (system-wide installation)
RUN uv pip install --system \\
    numpy \\
    pandas \\
    matplotlib \\
    seaborn \\
    jupyter \\
    ipython \\
    requests \\
    python-dotenv

# Install Python packages (prefer uv, pip as fallback)
RUN if [ -s requirements.txt ]; then \\
        (uv pip install --system -r requirements.txt || pip install -r requirements.txt); \\
    fi
RUN if [ -s requirements-dev.txt ]; then \\
        (uv pip install --system -r requirements-dev.txt || pip install -r requirements-dev.txt); \\
    fi

# Install packages from vendor directory if available (using uv for speed)
RUN if [ -d vendor ] && [ "$(ls -A vendor)" ]; then \\
        (uv pip install --find-links vendor --no-index vendor/*.whl 2>/dev/null || \\
         pip install --find-links vendor --no-index $(ls vendor/*.whl 2>/dev/null | xargs -I {{}} basename {{}} .whl | cut -d'-' -f1 || true)); \\
    fi

# Create user with same UID as host user (for file permissions)
ARG USER_ID=1000
ARG GROUP_ID=1000
RUN groupadd -g $GROUP_ID venvoy && \\
    useradd -u $USER_ID -g $GROUP_ID -m -s /bin/bash venvoy

# Switch to user
USER venvoy

# Set up shell with better interactive experience
RUN echo 'export PS1="(🤖 venvoy) \\u@\\h:\\w$ "' >> ~/.bashrc && \\
    echo 'echo "🚀 Welcome to your AI-ready venvoy environment!"' >> ~/.bashrc && \\
    echo 'echo "🐍 Python $(python --version) with AI/ML packages"' >> ~/.bashrc && \\
    echo 'echo "📦 Package managers: uv (ultra-fast pip), pip"' >> ~/.bashrc && \\
    echo 'echo "📊 Pre-installed: numpy, pandas, matplotlib, jupyter, and more"' >> ~/.bashrc && \\
    echo 'echo "🔍 Auto-saving environment.yml on package changes"' >> ~/.bashrc && \\
    echo 'echo "📂 Workspace: $(pwd)"' >> ~/.bashrc && \\
    echo 'echo "💡 Home directory mounted at: /host-home"' >> ~/.bashrc && \\
    echo 'python3 /usr/local/bin/package_monitor.py --daemon 2>/dev/null &' >> ~/.bashrc

# Default command
CMD ["/bin/bash"]
"""

        dockerfile_path = self.env_dir / "Dockerfile"
        with open(dockerfile_path, "w") as f:
            f.write(dockerfile_content)

    def _create_docker_compose(self):
        """Create docker-compose.yml for easy environment management"""
        home_path = self.platform.get_home_mount_path()

        compose_content = {
            "version": "3.8",
            "services": {
                self.name: {
                    "build": {
                        "context": ".",
                        "args": {
                            "USER_ID": "${USER_ID:-1000}",
                            "GROUP_ID": "${GROUP_ID:-1000}",
                        },
                    },
                    "container_name": self.name,
                    "volumes": [f"{home_path}:/host-home", f"{Path.cwd()}:/workspace"],
                    "working_dir": "/workspace",
                    "stdin_open": True,
                    "tty": True,
                    "environment": ["TERM=xterm-256color"],
                }
            },
        }

        compose_path = self.env_dir / "docker-compose.yml"
        with open(compose_path, "w") as f:
            yaml.safe_dump(compose_content, f, default_flow_style=False)

    def build_and_launch(self):
        """Build the Docker image and launch the container"""
        # Build the image
        image_tag = f"venvoy/{self.name}:{self.python_version}"

        try:
            self._run_docker_command(
                ["build", "-t", image_tag, str(self.env_dir)],
                check=True,
                cwd=self.env_dir,
            )
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Failed to build Docker image: {e}")

        # Update config with image tag
        self._update_config({"image_tag": image_tag})

    def download_wheels(self, include_dev: bool = False):
        """Download wheels for all installed packages using container's package managers

        IMPORTANT: This runs uv/pip INSIDE the container, not on the host.
        This ensures we use the container's package managers and Python environment.
        """
        vendor_dir = self.env_dir / "vendor"
        vendor_dir.mkdir(exist_ok=True)

        # Get list of installed packages
        requirements_files = [self.env_dir / "requirements.txt"]
        if include_dev:
            requirements_files.append(self.env_dir / "requirements-dev.txt")

        image_tag = f"venvoy/{self.name}:{self.python_version}"

        for req_file in requirements_files:
            if req_file.exists() and req_file.stat().st_size > 0:
                try:
                    # Mount the requirements file and vendor directory into the container
                    # and run download commands inside the container
                    req_filename = req_file.name

                    # Try uv first for ultra-fast downloads (inside container)
                    try:
                        self._run_docker_command(
                            [
                                "run",
                                "--rm",
                                "-v",
                                f"{req_file}:/workspace/{req_filename}:ro",
                                "-v",
                                f"{vendor_dir}:/workspace/vendor",
                                image_tag,
                                "bash",
                                "-c",
                                f"uv pip download -r /workspace/{req_filename} --dest /workspace/vendor --no-deps",
                            ],
                            check=True,
                        )
                        print(
                            "✅ Downloaded wheels using uv (ultra-fast) inside container"
                        )
                    except subprocess.CalledProcessError:
                        # Fallback to pip if uv fails (inside container)
                        try:
                            self._run_docker_command(
                                [
                                    "run",
                                    "--rm",
                                    "-v",
                                    f"{req_file}:/workspace/{req_filename}:ro",
                                    "-v",
                                    f"{vendor_dir}:/workspace/vendor",
                                    image_tag,
                                    "bash",
                                    "-c",
                                    f"pip download -r /workspace/{req_filename} -d /workspace/vendor --no-deps",
                                ],
                                check=True,
                            )
                            print(
                                "✅ Downloaded wheels using pip (fallback) inside container"
                            )
                        except subprocess.CalledProcessError as e:
                            print(
                                f"Warning: Failed to download wheels inside container: {e}"
                            )
                except subprocess.CalledProcessError as e:
                    print(f"Warning: Failed to download some wheels: {e}")

    def create_snapshot(self):
        """Create a snapshot of the current environment state"""
        snapshot = {
            "name": self.name,
            "python_version": self.python_version,
            "created": datetime.now().isoformat(),
            "platform": self.platform.detect(),
            "packages": self._get_installed_packages(),
        }

        snapshot_file = (
            self.env_dir / f"snapshot-{datetime.now().strftime('%Y%m%d-%H%M%S')}.json"
        )
        with open(snapshot_file, "w") as f:
            json.dump(snapshot, f, indent=2)

        return snapshot_file

    def _get_installed_packages(self) -> List[Dict]:
        """Get list of installed packages from the environment"""
        try:
            # Run pip freeze inside the container to get actual installed packages
            result = self._run_docker_command(
                [
                    "run",
                    "--rm",
                    f"venvoy/{self.name}:{self.python_version}",
                    "bash",
                    "-c",
                    "pip freeze",
                ],
                capture_output=True,
                text=True,
                check=True,
            )

            packages = []
            for line in result.stdout.strip().split("\n"):
                if line and "==" in line:
                    name, version = line.split("==", 1)
                    packages.append({"name": name, "version": version})

            return packages
        except subprocess.CalledProcessError:
            return []

    def _get_installed_r_packages(self, image_name: str) -> List[Dict]:
        """Get list of installed R packages from the container"""
        try:
            # Get R packages using installed.packages()
            result = subprocess.run(
                [
                    "docker",
                    "run",
                    "--rm",
                    image_name,
                    "bash",
                    "-c",
                    """
                R --slave -e "pkgs <- installed.packages(); cat(paste(pkgs[,1], pkgs[,3], sep='=='), sep='\\n')"
                """,
                ],
                capture_output=True,
                text=True,
                check=True,
            )

            packages = []
            for line in result.stdout.strip().split("\n"):
                if line and "==" in line:
                    name, version = line.split("==", 1)
                    # Filter out base R packages (they come with R itself)
                    base_packages = {
                        "base",
                        "compiler",
                        "datasets",
                        "graphics",
                        "grDevices",
                        "grid",
                        "methods",
                        "parallel",
                        "splines",
                        "stats",
                        "stats4",
                        "tcltk",
                        "tools",
                        "utils",
                        "Matrix",
                        "lattice",
                        "nlme",
                        "mgcv",
                        "rpart",
                        "survival",
                        "MASS",
                        "class",
                        "nnet",
                        "spatial",
                        "boot",
                        "cluster",
                        "codetools",
                        "foreign",
                        "KernSmooth",
                        "rpart",
                        "class",
                        "nnet",
                        "spatial",
                    }
                    if name not in base_packages:
                        packages.append({"name": name, "version": version})

            return packages
        except subprocess.CalledProcessError:
            return []

    def setup_buildx(self):
        """Setup Docker BuildX for multi-arch builds"""
        # Only available for Docker runtime
        runtime_info = self.container_manager.get_runtime_info()
        if runtime_info["runtime"] == "docker":
            # This would need to be implemented in container_manager
            print("🔧 BuildX setup available for Docker runtime")
        else:
            print(f"⚠️  BuildX not available for {runtime_info['runtime']} runtime")

    def build_multiarch(self, tag: Optional[str] = None) -> str:
        """Build multi-architecture image"""
        if tag is None:
            tag = f"venvoy/{self.name}:{self.python_version}-multiarch"

        dockerfile_path = self.env_dir / "Dockerfile"
        return self.container_manager.build_image(
            dockerfile_path=dockerfile_path, tag=tag, context_path=self.env_dir
        )

    def push_image(self, tag: str):
        """Push image to registry"""
        # This would need to be implemented in container_manager
        runtime_info = self.container_manager.get_runtime_info()
        if runtime_info["runtime"] == "docker":
            print("🔧 Image pushing available for Docker runtime")
        else:
            print(
                f"⚠️  Image pushing not yet implemented for {runtime_info['runtime']} runtime"
            )

    def run(self, command: Optional[str] = None, additional_mounts: List[str] = None):
        """Run the environment container and snapshot packages when it exits."""
        if not USE_UNIFIED_RUN:
            return self._run_legacy(command, additional_mounts)

        if not self.config_file.exists():
            raise RuntimeError(
                f"Environment '{self.name}' not found. Run 'venvoy init' first."
            )

        with open(self.config_file, "r") as f:
            config = yaml.safe_load(f)

        image_name = config.get("image_name")
        if not image_name:
            image_tag = self._get_combined_image_tag(
                config.get("python_version", self.python_version),
                config.get("r_version", self.r_version),
            )
            image_name = f"zaphodbeeblebrox3rd/venvoy:{image_tag}"

        self._ensure_image_available(image_name)
        editor_type, editor_available = self._get_editor_config()

        home_path = self.platform.get_home_mount_path()
        self._ensure_host_home_writable(home_path)
        volumes = {
            home_path: {"bind": "/host-home", "mode": "rw"},
            str(Path.cwd()): {"bind": "/workspace", "mode": "rw"},
        }
        if additional_mounts:
            for mount in additional_mounts:
                if ":" in mount:
                    host_path, container_path = mount.split(":", 1)
                    volumes[host_path] = {"bind": container_path, "mode": "rw"}

        try:
            if command is None and editor_available and editor_type in ("devin", "vscode"):
                self._launch_editor(editor_type, image_name, volumes)
                return
            if command is None:
                command = self._get_interactive_shell_command()
            self._run_foreground(image_name, command, volumes)
            print("Container stopped - saving environment state...")
            self.auto_save_environment()
        except RuntimeError as e:
            print(f"Failed to run container: {e}")
            print("Make sure the environment is built. Run 'venvoy init' if needed.")

    def _bind_mounts(self, volumes: Dict) -> Dict[str, str]:
        mounts = {}
        for host_path, mount_info in volumes.items():
            if isinstance(mount_info, dict):
                mounts[host_path] = mount_info["bind"]
            else:
                mounts[host_path] = mount_info
        return mounts

    def _run_foreground(self, image_name: str, command: str, volumes: Dict) -> None:
        self.container_manager.run_container(
            image=image_name,
            name=f"{self.name}-runtime",
            command=command,
            volumes=self._bind_mounts(volumes),
            detach=False,
        )

    def _container_runtime_bin(self) -> Optional[str]:
        runtime = self.container_manager.runtime
        if runtime == ContainerRuntime.DOCKER:
            return shutil.which("docker")
        if runtime == ContainerRuntime.PODMAN:
            return shutil.which("podman")
        return None

    def _ensure_container_running(self, name: str) -> None:
        """Confirm a detached Docker or Podman container stayed up."""
        binary = self._container_runtime_bin()
        if not binary:
            return
        time.sleep(2)
        check = subprocess.run(
            [binary, "ps", "--filter", f"name={name}", "--format", "{{.Status}}"],
            capture_output=True,
            text=True,
        )
        status = check.stdout.strip() if check.returncode == 0 else ""
        if status and ("Up" in status or "running" in status.lower()):
            return
        check_all = subprocess.run(
            [binary, "ps", "-a", "--filter", f"name={name}", "--format", "{{.Status}}"],
            capture_output=True,
            text=True,
        )
        exited = check_all.stdout.strip() if check_all.returncode == 0 else ""
        if exited:
            raise RuntimeError(f"Container {name} is not running. Status: {exited}")
        raise RuntimeError(f"Container {name} not found")

    def _container_remote_uri(self, editor_type: str, container) -> str:
        """Build the vscode-remote URI used to attach an editor to the container.

        Devin Desktop's dev containers extension resolves the
        ``dev-container+<hex(JSON)>`` authority where the JSON carries the
        container id; VSCode uses ``attached-container+<name>``.
        """
        if editor_type == "devin":
            container_id = getattr(container, "id", None) or getattr(
                container, "name", f"{self.name}-runtime"
            )
            encoded = json.dumps({"containerId": container_id}).encode().hex()
            return f"vscode-remote://dev-container+{encoded}/host-home"
        name = getattr(container, "name", f"{self.name}-runtime")
        return f"vscode-remote://attached-container+{name}/host-home"

    def _launch_editor(self, editor_type: str, image_name: str, volumes: Dict) -> None:
        runtime_name = self.container_manager.runtime.value
        container_name = f"{self.name}-runtime"
        environment_vars = {
            "VENVOY_HOST_RUNTIME": runtime_name,
            "VENVOY_HOST_HOME": "/host-home",
        }
        if editor_type == "devin":
            # Devin Desktop's dev containers extension resolves the
            # dev-container+<hex(JSON {"containerId": ...})> authority.
            binary = shutil.which("devin-desktop") or "devin-desktop"
        else:
            binary = "code"
        try:
            container = self.container_manager.run_container(
                image=image_name,
                name=container_name,
                command="sleep infinity",
                volumes=volumes,
                environment=environment_vars,
                working_dir="/home/venvoy",
                detach=True,
            )
            if container is False:
                raise RuntimeError(f"Container {container_name} failed to start")
            self._ensure_container_running(container_name)
            print(f"Launching {editor_type}...")
            try:
                subprocess.run(
                    [
                        binary,
                        "--folder-uri",
                        self._container_remote_uri(editor_type, container),
                    ],
                    check=True,
                )
                print(
                    "When you are done, stop the container with: "
                    f"{runtime_name} stop {container_name}"
                )
            except subprocess.CalledProcessError:
                print(f"Failed to launch {editor_type}. Falling back to a shell.")
                if hasattr(container, "stop"):
                    container.stop()
                self._run_foreground(
                    image_name, self._get_interactive_shell_command(), volumes
                )
                self.auto_save_environment()
        except Exception as exc:
            print(f"Failed to launch with {editor_type}: {exc}")
            print("Falling back to a shell...")
            self._run_foreground(
                image_name, self._get_interactive_shell_command(), volumes
            )
            self.auto_save_environment()

    def _run_legacy(self, command: Optional[str] = None, additional_mounts: List[str] = None):
        """Previous run() path. Rollback: set USE_UNIFIED_RUN = False."""
        print(f"🔧 run method called with command: {command}")
        # Load configuration to get the image name
        if not self.config_file.exists():
            raise RuntimeError(
                f"Environment '{self.name}' not found. Run 'venvoy init' first."
            )

        with open(self.config_file, "r") as f:
            config = yaml.safe_load(f)

        image_name = config.get("image_name")
        if not image_name:
            # Construct combined image tag
            image_tag = self._get_combined_image_tag(
                config.get("python_version", self.python_version),
                config.get("r_version", self.r_version)
            )
            image_name = f"zaphodbeeblebrox3rd/venvoy:{image_tag}"

        # Ensure image is available
        self._ensure_image_available(image_name)

        # Check editor configuration
        editor_type, editor_available = self._get_editor_config()

        # Prepare volume mounts
        home_path = self.platform.get_home_mount_path()
        # Ensure host home mount is writable; if root-owned, fix ownership
        self._ensure_host_home_writable(home_path)
        volumes = {
            home_path: {"bind": "/host-home", "mode": "rw"},
            str(Path.cwd()): {"bind": "/workspace", "mode": "rw"},
        }

        # Start monitoring thread for auto-save
        import threading

        monitor_thread = threading.Thread(
            target=self._monitor_package_changes,
            args=(f"{self.name}-runtime",),
            daemon=True,
        )
        monitor_thread.start()

        # Add additional mounts
        if additional_mounts:
            for mount in additional_mounts:
                if ":" in mount:
                    host_path, container_path = mount.split(":", 1)
                    volumes[host_path] = {"bind": container_path, "mode": "rw"}

        # Determine the command to run
        if command is None:
            if editor_available:
                if editor_type == "devin":
                    # Try to launch Devin and connect to container
                    self._launch_with_devin(image_name, volumes)
                elif editor_type == "vscode":
                    # Try to launch VSCode and connect to container
                    self._launch_with_vscode(image_name, volumes)
                else:
                    # Launch interactive shell
                    command = self._get_interactive_shell_command()
            else:
                # Launch interactive shell
                command = self._get_interactive_shell_command()

        # Run container
        try:
            if command is not None:
                # Execute the provided command
                print(f"🔧 Executing command: {command}")
                # Convert volumes format for container manager
                volume_mounts = {}
                for host_path, mount_info in volumes.items():
                    volume_mounts[host_path] = mount_info["bind"]

                self.container_manager.run_container(
                    image=image_name,
                    name=f"{self.name}-runtime",
                    command=command,
                    volumes=volume_mounts,
                    detach=False,
                )

                # Auto-save environment when container exits
                print("💾 Container stopped - saving final environment state...")
                self.auto_save_environment()
            elif editor_available:
                # Launch with editor
                if editor_type == "devin":
                    # Try to launch Devin and connect to container
                    self._launch_with_devin(image_name, volumes)
                elif editor_type == "vscode":
                    # Try to launch VSCode and connect to container
                    self._launch_with_vscode(image_name, volumes)
                else:
                    # Launch interactive shell
                    command = self._get_interactive_shell_command()
                    # Convert volumes format for container manager
                    volume_mounts = {}
                    for host_path, mount_info in volumes.items():
                        volume_mounts[host_path] = mount_info["bind"]

                    self.container_manager.run_container(
                        image=image_name,
                        name=f"{self.name}-runtime",
                        command=command,
                        volumes=volume_mounts,
                        detach=False,
                    )

                    # Auto-save environment when container exits
                    print("💾 Container stopped - saving final environment state...")
                    self.auto_save_environment()
            else:
                # Launch interactive shell
                command = self._get_interactive_shell_command()
                # Convert volumes format for container manager
                volume_mounts = {}
                for host_path, mount_info in volumes.items():
                    volume_mounts[host_path] = mount_info["bind"]

                self.container_manager.run_container(
                    image=image_name,
                    name=f"{self.name}-runtime",
                    command=command,
                    volumes=volume_mounts,
                    detach=False,
                )

                # Auto-save environment when container exits
                print("💾 Container stopped - saving final environment state...")
                self.auto_save_environment()

        except RuntimeError as e:
            print(f"Failed to run container: {e}")
            print("Make sure the environment is built. Run 'venvoy init' if needed.")

    def export_yaml(self, output_path: Optional[str] = None) -> str:
        """Export environment as YAML file"""
        if output_path is None:
            output_path = f"{self.name}-environment.yaml"

        # Get Python packages
        python_packages = self._get_installed_packages()
        python_packages_list = [f"{pkg['name']}=={pkg['version']}" for pkg in python_packages]

        # Get R packages if R is available
        r_packages_list = []
        try:
            # Load config to get image name
            if self.config_file.exists():
                with open(self.config_file, "r") as f:
                    config = yaml.safe_load(f)
                image_name = config.get("image_name")
                if image_name:
                    r_packages = self._get_installed_r_packages(image_name)
                    r_packages_list = [f"{pkg['name']}=={pkg['version']}" for pkg in r_packages]
        except Exception:
            # R packages not available or R not installed
            pass

        export_data = {
            "name": self.name,
            "python_version": self.python_version,
            "r_version": self.r_version,
            "python_packages": python_packages_list,
            "r_packages": r_packages_list,
            "exported": datetime.now().isoformat(),
            "venvoy_version": _package_version(),
        }

        output_file = Path(output_path)
        with open(output_file, "w") as f:
            yaml.safe_dump(export_data, f, default_flow_style=False)

        return str(output_file)

    def import_yaml(self, yaml_path: str, force: bool = False) -> str:
        """
        Import and restore environment from a YAML export file.

        Args:
            yaml_path: Path to the YAML export file
            force: Whether to overwrite existing environment

        Returns:
            Name of the restored environment
        """
        yaml_file = Path(yaml_path)
        if not yaml_file.exists():
            raise FileNotFoundError(f"YAML file not found: {yaml_path}")

        print(f"📦 Importing venvoy environment from YAML: {yaml_file.name}")

        # Read YAML file
        with open(yaml_file, "r") as f:
            export_data = yaml.safe_load(f)

        if not export_data:
            raise RuntimeError("Invalid YAML file: empty or invalid format")

        env_name = export_data.get("name", "venvoy-env")
        python_version = export_data.get("python_version", "3.11")
        r_version = export_data.get("r_version", "4.4")
        python_packages = export_data.get("python_packages", [])
        r_packages = export_data.get("r_packages", [])

        # Handle backward compatibility with old format
        if not python_packages and "packages" in export_data:
            # Old format - convert list of dicts to list of strings
            packages = export_data.get("packages", [])
            python_packages = []
            for pkg in packages:
                if isinstance(pkg, dict):
                    pkg_name = pkg.get("name", "")
                    pkg_version = pkg.get("version", "")
                    if pkg_name:
                        if pkg_version:
                            python_packages.append(f"{pkg_name}=={pkg_version}")
                        else:
                            python_packages.append(pkg_name)

        print(f"🔍 YAML contains environment: {env_name}")
        print(f"   Python: {python_version}")
        print(f"   R: {r_version}")
        print(f"   Python packages: {len(python_packages)}")
        print(f"   R packages: {len(r_packages)}")

        # Check if environment already exists
        target_env_dir = self.config_dir / "environments" / env_name
        if target_env_dir.exists() and not force:
            raise RuntimeError(
                f"Environment '{env_name}' already exists. Use --force to overwrite."
            )

        # Create environment directory
        if target_env_dir.exists():
            shutil.rmtree(target_env_dir)
        target_env_dir.mkdir(parents=True)

        # Create requirements.txt from Python packages
        if python_packages:
            print("📝 Creating requirements.txt...")
            requirements_file = target_env_dir / "requirements.txt"
            with open(requirements_file, "w") as f:
                for pkg in python_packages:
                    f.write(f"{pkg}\n")

        # Create r-requirements.txt from R packages
        if r_packages:
            print("📝 Creating r-requirements.txt...")
            r_requirements_file = target_env_dir / "r-requirements.txt"
            with open(r_requirements_file, "w") as f:
                for pkg in r_packages:
                    f.write(f"{pkg}\n")

        # Create config.yaml
        config = {
            "name": env_name,
            "python_version": python_version,
            "r_version": r_version,
            "runtime": "mixed" if r_packages else "python",
            "created": export_data.get("created", datetime.now().isoformat()),
            "imported_from": str(yaml_file),
            "imported_at": datetime.now().isoformat(),
        }

        config_file = target_env_dir / "config.yaml"
        with open(config_file, "w") as f:
            yaml.safe_dump(config, f, default_flow_style=False)

        print("\n✅ YAML imported successfully!")
        print("🚀 To build and use the environment:")
        print(
            f"   venvoy init --name {env_name} --python-version {python_version} --force"
        )

        return env_name

    def auto_save_environment(self):
        """Auto-save environment.yml under ~/.venvoy/projects/<name>."""
        try:
            # Get current Python packages from container
            python_packages = self._get_installed_packages()
            python_packages_list = [f"{pkg['name']}=={pkg['version']}" for pkg in python_packages]

            # Get R packages if available
            r_packages_list = []
            try:
                if self.config_file.exists():
                    with open(self.config_file, "r") as f:
                        config = yaml.safe_load(f)
                    image_name = config.get("image_name")
                    if image_name:
                        r_packages = self._get_installed_r_packages(image_name)
                        r_packages_list = [f"{pkg['name']}=={pkg['version']}" for pkg in r_packages]
            except Exception:
                # R packages not available or R not installed
                pass

            # Create new simplified environment.yml format
            env_data = {
                "name": self.name,
                "python_version": self.python_version,
                "r_version": self.r_version,
                "python_packages": python_packages_list,
                "r_packages": r_packages_list,
                "exported": datetime.now().isoformat(),
                "venvoy_version": _package_version(),
            }

            # Create timestamped filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            env_file = self.projects_dir / f"environment_{timestamp}.yml"

            # Save timestamped environment file
            with open(env_file, "w") as f:
                yaml.safe_dump(env_data, f, default_flow_style=False, sort_keys=False)

            # Also maintain current environment.yml as latest
            current_env_file = self.projects_dir / "environment.yml"
            with open(current_env_file, "w") as f:
                yaml.safe_dump(env_data, f, default_flow_style=False, sort_keys=False)

            # Update timestamp file
            timestamp_file = self.projects_dir / ".last_updated"
            with open(timestamp_file, "w") as f:
                f.write(datetime.now().isoformat())

            print(f"📝 Auto-saved environment to: {env_file}")

        except Exception as e:
            print(f"Warning: Failed to auto-save environment: {e}")

    def list_environment_exports(self) -> List[Dict[str, Any]]:
        """List all timestamped environment exports for this environment"""
        exports = []

        if not self.projects_dir.exists():
            return exports

        # Find all environment_*.yml files
        for env_file in self.projects_dir.glob("environment_*.yml"):
            try:
                with open(env_file, "r") as f:
                    env_data = yaml.safe_load(f)

                # Extract timestamp from filename
                filename = env_file.name
                if filename.startswith("environment_") and filename.endswith(".yml"):
                    timestamp_str = filename[12:-4]  # Remove 'environment_' and '.yml'

                    try:
                        # Parse timestamp
                        timestamp = datetime.strptime(timestamp_str, "%Y%m%d_%H%M%S")

                        # Count packages (new format: python_packages and r_packages)
                        python_count = len(env_data.get("python_packages", []))
                        r_count = len(env_data.get("r_packages", []))
                        total_count = python_count + r_count

                        exports.append(
                            {
                                "file": env_file,
                                "timestamp": timestamp,
                                "timestamp_str": timestamp_str,
                                "formatted_time": timestamp.strftime(
                                    "%Y-%m-%d %H:%M:%S"
                                ),
                                "python_packages": python_count,
                                "r_packages": r_count,
                                "total_packages": total_count,
                                "exported_date": env_data.get("exported", "Unknown"),
                                "venvoy_version": env_data.get(
                                    "venvoy_version", "Unknown"
                                ),
                            }
                        )

                    except ValueError:
                        # Skip files with invalid timestamp format
                        continue

            except (yaml.YAMLError, FileNotFoundError):
                continue

        # Sort by timestamp (newest first)
        exports.sort(key=lambda x: x["timestamp"], reverse=True)
        return exports

    def select_environment_export(self) -> Optional[Path]:
        """Present user with a list of environment exports to choose from"""
        exports = self.list_environment_exports()

        if not exports:
            return None

        print(
            f"\n📋 Found {len(exports)} previous environment exports for '{self.name}':"
        )
        print("=" * 80)

        for i, export in enumerate(exports, 1):
            print(
                f"{i:2d}. {export['formatted_time']} - "
                f"{export['total_packages']} packages "
                f"({export['python_packages']} Python, {export['r_packages']} R)"
            )

        print(f"{len(exports) + 1:2d}. Create new environment (skip restore)")
        print("=" * 80)

        while True:
            try:
                choice = input(
                    f"\nSelect environment to restore (1-{len(exports) + 1}): "
                ).strip()

                if not choice:
                    continue

                choice_num = int(choice)

                if choice_num == len(exports) + 1:
                    # User chose to create new environment
                    return None
                elif 1 <= choice_num <= len(exports):
                    selected = exports[choice_num - 1]
                    print(f"\n✅ Selected: {selected['formatted_time']}")
                    print(f"📦 Packages: {selected['total_packages']} total")
                    return selected["file"]
                else:
                    print(f"❌ Please enter a number between 1 and {len(exports) + 1}")

            except ValueError:
                print("❌ Please enter a valid number")
            except KeyboardInterrupt:
                print("\n🚫 Cancelled")
                return None

    def restore_from_environment_export(self, export_file: Path):
        """Restore environment from a specific export file"""
        try:
            print(f"🔄 Restoring environment from: {export_file.name}")

            # Read the export file
            with open(export_file, "r") as f:
                env_data = yaml.safe_load(f)

            # Extract Python and R packages (new format)
            python_deps = env_data.get("python_packages", [])
            r_deps = env_data.get("r_packages", [])

            # Handle backward compatibility with old format (dependencies structure)
            if not python_deps and "dependencies" in env_data:
                # Old format - convert to new format
                for dep in env_data.get("dependencies", []):
                    if isinstance(dep, dict) and "pip" in dep:
                        python_deps.extend(dep["pip"])
                    elif isinstance(dep, str):
                        # Convert conda format (name=version) to pip format (name==version)
                        if "=" in dep and not dep.startswith("="):
                            dep = dep.replace("=", "==", 1)
                        python_deps.append(dep)

            # Write Python packages to requirements.txt
            if python_deps:
                pip_req_file = self.env_dir / "requirements.txt"
                with open(pip_req_file, "w") as f:
                    for dep in python_deps:
                        f.write(f"{dep}\n")

            # Write R packages to r-requirements.txt
            if r_deps:
                r_req_file = self.env_dir / "r-requirements.txt"
                with open(r_req_file, "w") as f:
                    for dep in r_deps:
                        f.write(f"{dep}\n")

            print("✅ Environment configuration restored")
            print(f"📦 {len(python_deps)} Python packages, {len(r_deps)} R packages")

        except Exception as e:
            print(f"❌ Failed to restore environment: {e}")
            raise

    def _monitor_package_changes(self, container_name: str):
        """Monitor for package changes and auto-save environment.yml"""
        import time

        print("🔍 Starting package change monitor...")

        while True:
            try:
                # Check if signal file exists in container
                result = self._run_docker_command(
                    [
                        "exec",
                        container_name,
                        "test",
                        "-",
                        "/tmp/venvoy_package_changed",
                    ],
                    capture_output=True,
                )

                if result.returncode == 0:
                    # Signal file exists - packages changed
                    print("📦 Package change detected!")

                    # Auto-save environment
                    self.auto_save_environment()

                    # Remove signal file
                    self._run_docker_command(
                        [
                            "exec",
                            container_name,
                            "rm",
                            "-",
                            "/tmp/venvoy_package_changed",
                        ],
                        capture_output=True,
                    )

                time.sleep(2)  # Check every 2 seconds

            except subprocess.CalledProcessError:
                # Container might have stopped
                break
            except Exception as e:
                print(f"Monitor error: {e}")
                time.sleep(5)

    def list_environments(self) -> List[Dict[str, Any]]:
        """List all venvoy environments"""
        environments = []
        env_base_dir = self.config_dir / "environments"

        if not env_base_dir.exists():
            return environments

        for env_dir in env_base_dir.iterdir():
            if env_dir.is_dir():
                config_file = env_dir / "config.yaml"
                if config_file.exists():
                    try:
                        with open(config_file, "r") as f:
                            config = yaml.safe_load(f)

                        # Check if container exists
                        containers = self.container_manager.list_containers(
                            all_containers=True
                        )
                        status = "stopped"
                        for container in containers:
                            # Container names follow pattern: venvoy-{name}-{pid}
                            container_name = container.get("name", "")
                            if container_name.startswith(f"venvoy-{config['name']}-"):
                                # Extract status - it might be "Up" or "Exited" or similar
                                container_status = container.get("status", "").lower()
                                if (
                                    "up" in container_status
                                    or "running" in container_status
                                ):
                                    status = "running"
                                else:
                                    status = "stopped"
                                break

                        env_info = {
                            "name": config["name"],
                            "created": config["created"],
                            "status": status,
                        }
                        # Add runtime-specific version info
                        if config.get("runtime") == "r":
                            env_info["runtime"] = "r"
                            env_info["r_version"] = config.get("r_version", "unknown")
                        else:
                            env_info["runtime"] = "python"
                            env_info["python_version"] = config.get(
                                "python_version", "unknown"
                            )
                        environments.append(env_info)
                    except (yaml.YAMLError, KeyError):
                        continue

        return environments

    def _get_editor_config(self) -> tuple[str, bool]:
        """Get editor configuration from config"""
        if self.config_file.exists():
            try:
                with open(self.config_file, "r") as f:
                    config = yaml.safe_load(f)

                # Check new format first
                if "editor_type" in config and "editor_available" in config:
                    editor_type = config["editor_type"]
                    # Migrate configs written before the Cursor -> Devin switch
                    if editor_type == "cursor":
                        editor_type = "devin"
                    return editor_type, config["editor_available"]

                # Backward compatibility with old vscode_available format
                if config.get("vscode_available", False):
                    return "vscode", True

            except (yaml.YAMLError, KeyError):
                pass

        return "none", False  # Default to no editor

    def _get_vscode_availability(self) -> bool:
        """Get VSCode availability from config (backward compatibility)"""
        editor_type, editor_available = self._get_editor_config()
        return editor_available and editor_type == "vscode"

    def _get_interactive_shell_command(self) -> str:
        """Interactive shell inside the environment."""
        return '/bin/bash -c "echo \\"🚀 Welcome to your AI-ready venvoy environment!\\" && echo \\"🐍 Python $(python --version)\\" && echo \\"⚡ Package managers: uv (ultra-fast), pip (standard)\\" && echo \\"🤖 AI packages: numpy, pandas, matplotlib, jupyter, and more\\" && echo \\"💡 Your home directory is mounted at /host-home\\" && echo \\"📂 Current workspace: $(pwd)\\" && echo && exec /bin/bash"'

    def _launch_with_devin(self, image_tag: str, volumes: Dict):
        """Launch container and connect Devin Desktop"""
        import subprocess
        import time

        # Set up environment variables and working directory (matching install.sh behavior)
        import os
        environment_vars = {
            "VENVOY_HOST_RUNTIME": str(self.container_manager.runtime.value) if hasattr(self.container_manager.runtime, 'value') else str(self.container_manager.runtime),
            "VENVOY_HOST_HOME": "/host-home",
        }
        
        # First, start the container in detached mode
        # Note: volumes are passed as nested dicts - ContainerManager handles conversion internally
        try:
            container = self.container_manager.run_container(
                image=image_tag,
                name=f"{self.name}-runtime",
                command="sleep infinity",  # Keep container running
                volumes=volumes,  # Pass nested format - ContainerManager handles conversion
                environment=environment_vars,
                working_dir="/home/venvoy",
                detach=True,
            )

            print("🚀 Container started successfully!")
            
            # Verify container is actually running before proceeding
            import subprocess
            runtime = self.container_manager.runtime
            if runtime == ContainerRuntime.PODMAN:
                podman_path = shutil.which("podman")
                if podman_path:
                    # Wait a moment for container to fully start
                    time.sleep(2)
                    # Check if container is running
                    check_cmd = [podman_path, "ps", "--filter", f"name={container.name}", "--format", "{{.Status}}"]
                    check_result = subprocess.run(check_cmd, capture_output=True, text=True)
                    if check_result.returncode == 0 and check_result.stdout.strip():
                        status = check_result.stdout.strip()
                        if "Up" not in status and "running" not in status.lower():
                            raise RuntimeError(f"Container {container.name} is not running. Status: {status}")
                    else:
                        # Container not found in ps output - might have exited
                        # Check all containers including stopped ones
                        check_cmd_all = [podman_path, "ps", "-a", "--filter", f"name={container.name}", "--format", "{{.Status}}"]
                        check_result_all = subprocess.run(check_cmd_all, capture_output=True, text=True)
                        if check_result_all.returncode == 0 and check_result_all.stdout.strip():
                            status = check_result_all.stdout.strip()
                            raise RuntimeError(f"Container {container.name} exited. Status: {status}")
                        else:
                            raise RuntimeError(f"Container {container.name} not found")
            elif runtime == ContainerRuntime.DOCKER:
                docker_path = shutil.which("docker")
                if docker_path:
                    # Wait a moment for container to fully start
                    time.sleep(2)
                    # Check if container is running
                    check_cmd = [docker_path, "ps", "--filter", f"name={container.name}", "--format", "{{.Status}}"]
                    check_result = subprocess.run(check_cmd, capture_output=True, text=True)
                    if check_result.returncode == 0 and check_result.stdout.strip():
                        status = check_result.stdout.strip()
                        if "Up" not in status and "running" not in status.lower():
                            raise RuntimeError(f"Container {container.name} is not running. Status: {status}")
                    else:
                        # Container not found in ps output - might have exited
                        check_cmd_all = [docker_path, "ps", "-a", "--filter", f"name={container.name}", "--format", "{{.Status}}"]
                        check_result_all = subprocess.run(check_cmd_all, capture_output=True, text=True)
                        if check_result_all.returncode == 0 and check_result_all.stdout.strip():
                            status = check_result_all.stdout.strip()
                            raise RuntimeError(f"Container {container.name} exited. Status: {status}")
                        else:
                            raise RuntimeError(f"Container {container.name} not found")
            
            print("🧠 Launching Devin with AI assistance...")

            # Launch Devin Desktop with its dev containers extension
            devin_binary = shutil.which("devin-desktop") or "devin-desktop"
            devin_command = [
                devin_binary,
                "--folder-uri",
                self._container_remote_uri("devin", container),
            ]

            try:
                subprocess.run(devin_command, check=True)
                print("✅ Devin connected to container with AI features enabled!")
                print("🤖 Ready for AI-assisted coding!")
                print(
                    f"💡 When you're done, stop the container with: docker stop {container.name}"
                )
            except subprocess.CalledProcessError:
                print("⚠️  Failed to launch Devin. Falling back to interactive shell.")
                # Stop the detached container and run interactively instead
                container.stop()
                command = self._get_interactive_shell_command()
                self.container_manager.run_container(
                    image=image_tag,
                    name=f"{self.name}-runtime",
                    command=command,
                    volumes=volumes,
                    detach=False,
                )

        except Exception as e:
            print(f"Failed to launch with Devin: {e}")
            print("🐚 Falling back to interactive shell...")
            command = self._get_interactive_shell_command()
            self.container_manager.run_container(
                image=image_tag,
                name=f"{self.name}-runtime",
                command=command,
                volumes=volumes,
                detach=False,
            )

    def _launch_with_vscode(self, image_tag: str, volumes: Dict):
        """Launch container and connect VSCode"""
        import subprocess
        import time

        # Set up environment variables and working directory (matching install.sh behavior)
        import os
        environment_vars = {
            "VENVOY_HOST_RUNTIME": str(self.container_manager.runtime.value) if hasattr(self.container_manager.runtime, 'value') else str(self.container_manager.runtime),
            "VENVOY_HOST_HOME": "/host-home",
        }

        # First, start the container in detached mode
        # Note: volumes are passed as nested dicts - ContainerManager handles conversion internally
        try:
            container = self.container_manager.run_container(
                image=image_tag,
                name=f"{self.name}-runtime",
                command="sleep infinity",  # Keep container running
                volumes=volumes,  # Pass nested format - ContainerManager handles conversion
                environment=environment_vars,
                working_dir="/home/venvoy",
                detach=True,
            )

            print("🚀 Container started successfully!")
            print("🔧 Launching VSCode and connecting to container...")

            # Give container a moment to start
            time.sleep(2)

            # Launch VSCode with remote containers extension
            vscode_command = [
                "code",
                "--folder-uri",
                f"vscode-remote://attached-container+{container.name}/host-home",
            ]

            try:
                subprocess.run(vscode_command, check=True)
                print("✅ VSCode connected to container!")
                print(
                    "💡 When you're done, stop the container with: docker stop {container.name}"
                )
            except subprocess.CalledProcessError:
                print("⚠️  Failed to launch VSCode. Falling back to interactive shell.")
                # Stop the detached container and run interactively instead
                container.stop()
                command = self._get_interactive_shell_command()
                self.container_manager.run_container(
                    image=image_tag,
                    name=f"{self.name}-runtime",
                    command=command,
                    volumes=volumes,
                    detach=False,
                )

        except Exception as e:
            print(f"Failed to launch with VSCode: {e}")
            print("🐚 Falling back to interactive shell...")
            command = self._get_interactive_shell_command()
            self.container_manager.run_container(
                image=image_tag,
                name=f"{self.name}-runtime",
                command=command,
                volumes=volumes,
                detach=False,
            )

    def _update_config(self, updates: Dict[str, Any]):
        """Update environment configuration"""
        if self.config_file.exists():
            with open(self.config_file, "r") as f:
                config = yaml.safe_load(f)
        else:
            config = {}

        config.update(updates)

        with open(self.config_file, "w") as f:
            yaml.safe_dump(config, f, default_flow_style=False)
