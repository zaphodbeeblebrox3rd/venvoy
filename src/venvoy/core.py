"""
Core venvoy environment management

IMPORTANT: This module manages Docker containers. The key principle is:
- Host operations: Docker management, file system operations, editor launching
- Container operations: Package installation, dependency resolution, Python execution

All package management (mamba, uv, pip) happens INSIDE containers, not on the host.
"""

import json
import subprocess
import tarfile
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
import yaml
import os
import shutil

from .container_manager import ContainerManager
from .platform_detector import PlatformDetector


class VenvoyEnvironment:
    """Manages portable Python and R environments"""
    
    def __init__(self, name: str = "venvoy-env", python_version: str = "3.11", runtime: str = "python", r_version: str = "4.4"):
        print(f"🔧 VenvoyEnvironment.__init__ called with name: {name}")
        self.name = name
        self.runtime = runtime  # "python", "r", or "mixed"
        self.python_version = python_version
        self.r_version = r_version
        self.platform = PlatformDetector()
        self.container_manager = ContainerManager()
        self.config_dir = Path.home() / ".venvoy"
        self.env_dir = self.config_dir / "environments" / name
        self.config_file = self.env_dir / "config.yaml"
        print(f"🔧 VenvoyEnvironment.__init__ completed")
        
        # Create venvoy-projects directory for auto-saved environments
        self.projects_dir = self.config_dir / "projects" / name
        
        # Ensure directories exist
        self.config_dir.mkdir(exist_ok=True)
        (self.config_dir / "environments").mkdir(exist_ok=True)
        (self.config_dir / "projects").mkdir(exist_ok=True)
        self.projects_dir.mkdir(parents=True, exist_ok=True)
    
    def initialize(self, force: bool = False, editor_type: str = "none", editor_available: bool = False):
        """Initialize a new venvoy environment"""
        if self.env_dir.exists() and not force:
            raise RuntimeError(
                f"Environment '{self.name}' already exists at {self.env_dir}. "
                f"This directory contains your environment configuration, Dockerfile, and requirements. "
                f"Use --force to reinitialize and overwrite the existing environment."
            )
        
        print(f"🚀 Initializing venvoy environment: {self.name}")
        
        # Create environment directory
        self.env_dir.mkdir(parents=True, exist_ok=True)
        self.projects_dir.mkdir(parents=True, exist_ok=True)
        
        # Pull the pre-built image if needed
        if self.runtime == "python":
            image_name = f"zaphodbeeblebrox3rd/venvoy:python{self.python_version}"
            print(f"📦 Setting up Python {self.python_version} environment...")
        elif self.runtime == "r":
            image_name = f"zaphodbeeblebrox3rd/venvoy:r{self.r_version}"
            print(f"📊 Setting up R {self.r_version} environment...")
        else:
            raise ValueError(f"Unsupported runtime: {self.runtime}")
        
        self._ensure_image_available(image_name)
        
        # Log runtime information for debugging
        runtime_info = self.container_manager.get_runtime_info()
        print(f"🔧 Using {runtime_info['runtime']} {runtime_info['version']}")
        if runtime_info['is_hpc']:
            print(f"🏢 HPC environment detected - using {runtime_info['runtime']} for best compatibility")
        
        # Check for existing environment exports but don't prompt during init
        exports = self.list_environment_exports()
        selected_export = None
        
        if exports:
            # Use the most recent export automatically
            selected_export = exports[0]['file']  # First one is most recent
            print(f"🔄 Found {len(exports)} previous exports, using most recent: {selected_export.name}")
            self.restore_from_environment_export(selected_export)
        else:
            # Create new environment
            print("🆕 Creating new environment...")
            
            # Create requirements files
            (self.env_dir / "requirements.txt").touch()
            (self.env_dir / "requirements-dev.txt").touch()
        
        # Create configuration
        config = {
            'name': self.name,
            'runtime': self.runtime,
            'python_version': self.python_version,
            'r_version': self.r_version,
            'created': datetime.now().isoformat(),
            'platform': self.platform.detect(),
            'image_name': image_name,
            'packages': [],
            'dev_packages': [],
            'editor_type': editor_type,
            'editor_available': editor_available,
            # Keep backward compatibility
            'vscode_available': editor_available and editor_type == "vscode",
            'restored_from': selected_export.name if selected_export else None,
        }
        
        with open(self.config_file, 'w') as f:
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
            print(f"🆕 New environment created")
    
    def _find_docker_command(self) -> str:
        """Find the Docker command with proper PATH handling"""
        # Common Docker installation paths
        common_paths = [
            '/usr/local/bin/docker',
            '/usr/bin/docker',
            '/opt/homebrew/bin/docker',
            shutil.which('docker')
        ]
        
        for docker_path in common_paths:
            if docker_path and Path(docker_path).exists():
                return docker_path
        
        raise RuntimeError("Docker not found. Please install Docker and ensure it's in your PATH.")

    def _run_docker_command(self, args: List[str], **kwargs) -> subprocess.CompletedProcess:
        """Run a Docker command with proper PATH handling"""
        docker_cmd = self._find_docker_command()
        full_command = [docker_cmd] + args
        
        # Ensure we have a proper environment with PATH
        env = os.environ.copy()
        if '/usr/local/bin' not in env.get('PATH', ''):
            env['PATH'] = f"/usr/local/bin:{env.get('PATH', '')}"
        
        return subprocess.run(full_command, env=env, **kwargs)

    def _ensure_image_available(self, image_name: str):
        """Ensure the venvoy image is available locally"""
        runtime_info = self.container_manager.get_runtime_info()
        host_runtime = os.environ.get('VENVOY_HOST_RUNTIME')
        
        # Check if we're running inside a container and the runtime isn't available
        # In this case, assume the bootstrap script on the host has handled image availability
        if host_runtime:
            runtime_available = False
            if runtime_info['runtime'] == 'docker':
                runtime_available = shutil.which('docker') is not None
            elif runtime_info['runtime'] == 'podman':
                runtime_available = shutil.which('podman') is not None
            elif runtime_info['runtime'] in ['apptainer', 'singularity']:
                runtime_available = shutil.which(runtime_info['runtime']) is not None
            
            if not runtime_available:
                # Running inside container without runtime available - assume host handles it
                print(f"✅ Environment availability handled by host runtime")
                return
        
        if runtime_info['runtime'] in ['apptainer', 'singularity']:
            # For Apptainer/Singularity, check if SIF file exists
            # Sanitize image name for SIF file (replace / and : with -)
            sif_name = image_name.replace('/', '-').replace(':', '-') + '.sif'
            sif_file = self.container_manager.sif_dir / sif_name
            if not sif_file.exists():
                print(f"⬇️  Downloading environment (one-time setup)...")
                if self.container_manager.pull_image(image_name):
                    print(f"✅ Environment ready")
                else:
                    raise RuntimeError(f"Failed to download environment")
            else:
                print(f"✅ Environment already available")
        else:
            # For Docker/Podman, use traditional image inspection
            try:
                if runtime_info['runtime'] == 'docker':
                    result = self._run_docker_command([
                        'image', 'inspect', image_name
                    ], capture_output=True, check=True)
                elif runtime_info['runtime'] == 'podman':
                    result = subprocess.run([
                        'podman', 'image', 'inspect', image_name
                    ], capture_output=True, check=True)
                    
            except (subprocess.CalledProcessError, FileNotFoundError):
                # Image doesn't exist or runtime not available, pull it
                print(f"⬇️  Downloading environment (one-time setup)...")
                if self.container_manager.pull_image(image_name):
                    print(f"✅ Environment ready")
                else:
                    raise RuntimeError(f"Failed to download environment")
    
    def _create_dockerfile(self):
        """Create Dockerfile for the environment"""
        dockerfile_content = f"""# venvoy environment: {self.name}
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
    && rm -rf /var/lib/apt/lists/*

# Install miniconda
RUN wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh -O /tmp/miniconda.sh && \\
    bash /tmp/miniconda.sh -b -p /opt/conda && \\
    rm /tmp/miniconda.sh

# Add conda to PATH
ENV PATH="/opt/conda/bin:$PATH"

# Initialize conda
RUN conda init bash

# Install mamba for faster dependency resolution
RUN conda install -n base -c conda-forge mamba -y

# Create environment using mamba (much faster than conda)
RUN mamba create -n venvoy python={self.python_version} -c conda-forge -y

# Install uv for ultra-fast Python package management
RUN pip install --no-cache-dir uv

# Activate environment by default
ENV CONDA_DEFAULT_ENV=venvoy
ENV CONDA_PREFIX=/opt/conda/envs/venvoy
ENV PATH="/opt/conda/envs/venvoy/bin:$PATH"

# Set working directory
WORKDIR /workspace

# Copy requirements if they exist
COPY requirements*.txt ./
COPY vendor/ ./vendor/

# Copy package monitor script
COPY package_monitor.py /usr/local/bin/package_monitor.py
RUN chmod +x /usr/local/bin/package_monitor.py

# Install common AI/ML packages using mamba for better dependency resolution
RUN mamba install -n venvoy -c conda-forge \\
    numpy \\
    pandas \\
    matplotlib \\
    seaborn \\
    jupyter \\
    ipython \\
    requests \\
    python-dotenv \\
    -y

# Install Python packages (prefer uv for pure Python packages, pip as fallback)
# Note: We're in a conda environment, so no --system flag needed
RUN if [ -s requirements.txt ]; then \\
        (uv pip install -r requirements.txt || pip install -r requirements.txt); \\
    fi
RUN if [ -s requirements-dev.txt ]; then \\
        (uv pip install -r requirements-dev.txt || pip install -r requirements-dev.txt); \\
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
RUN echo 'conda activate venvoy' >> ~/.bashrc && \\
    echo 'export PS1="(🤖 venvoy) \\u@\\h:\\w$ "' >> ~/.bashrc && \\
    echo 'echo "🚀 Welcome to your AI-ready venvoy environment!"' >> ~/.bashrc && \\
    echo 'echo "🐍 Python $(python --version) with AI/ML packages"' >> ~/.bashrc && \\
    echo 'echo "📦 Package managers: mamba (fast conda), uv (ultra-fast pip), pip"' >> ~/.bashrc && \\
    echo 'echo "📊 Pre-installed: numpy, pandas, matplotlib, jupyter, and more"' >> ~/.bashrc && \\
    echo 'echo "🔍 Auto-saving environment.yml on package changes"' >> ~/.bashrc && \\
    echo 'echo "📂 Workspace: $(pwd)"' >> ~/.bashrc && \\
    echo 'echo "💡 Home directory mounted at: /home/venvoy/host-home"' >> ~/.bashrc && \\
    echo 'python3 /usr/local/bin/package_monitor.py --daemon 2>/dev/null &' >> ~/.bashrc

# Default command
CMD ["/bin/bash"]
"""
        
        dockerfile_path = self.env_dir / "Dockerfile"
        with open(dockerfile_path, 'w') as f:
            f.write(dockerfile_content)
    
    def _create_docker_compose(self):
        """Create docker-compose.yml for easy environment management"""
        home_path = self.platform.get_home_mount_path()
        
        compose_content = {
            'version': '3.8',
            'services': {
                self.name: {
                    'build': {
                        'context': '.',
                        'args': {
                            'USER_ID': '${USER_ID:-1000}',
                            'GROUP_ID': '${GROUP_ID:-1000}'
                        }
                    },
                    'container_name': self.name,
                    'volumes': [
                        f"{home_path}:/home/venvoy/host-home",
                        f"{Path.cwd()}:/workspace"
                    ],
                    'working_dir': '/workspace',
                    'stdin_open': True,
                    'tty': True,
                    'environment': [
                        'TERM=xterm-256color'
                    ]
                }
            }
        }
        
        compose_path = self.env_dir / "docker-compose.yml"
        with open(compose_path, 'w') as f:
            yaml.safe_dump(compose_content, f, default_flow_style=False)
    
    def build_and_launch(self):
        """Build the Docker image and launch the container"""
        # Build the image
        image_tag = f"venvoy/{self.name}:{self.python_version}"
        
        try:
            self._run_docker_command([
                'build',
                '-t', image_tag,
                str(self.env_dir)
            ], check=True, cwd=self.env_dir)
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Failed to build Docker image: {e}")
        
        # Update config with image tag
        self._update_config({'image_tag': image_tag})
    
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
                        self._run_docker_command([
                            'run', '--rm',
                            '-v', f"{req_file}:/workspace/{req_filename}:ro",
                            '-v', f"{vendor_dir}:/workspace/vendor",
                            image_tag,
                            'bash', '-c', f'source /opt/conda/bin/activate venvoy && uv pip download -r /workspace/{req_filename} --dest /workspace/vendor --no-deps'
                        ], check=True)
                        print(f"✅ Downloaded wheels using uv (ultra-fast) inside container")
                    except subprocess.CalledProcessError:
                        # Fallback to pip if uv fails (inside container)
                        try:
                            self._run_docker_command([
                                'run', '--rm',
                                '-v', f"{req_file}:/workspace/{req_filename}:ro",
                                '-v', f"{vendor_dir}:/workspace/vendor",
                                image_tag,
                                'bash', '-c', f'source /opt/conda/bin/activate venvoy && pip download -r /workspace/{req_filename} -d /workspace/vendor --no-deps'
                            ], check=True)
                            print(f"✅ Downloaded wheels using pip (fallback) inside container")
                        except subprocess.CalledProcessError as e:
                            print(f"Warning: Failed to download wheels inside container: {e}")
                except subprocess.CalledProcessError as e:
                    print(f"Warning: Failed to download some wheels: {e}")
    
    def create_snapshot(self):
        """Create a snapshot of the current environment state"""
        snapshot = {
            'name': self.name,
            'python_version': self.python_version,
            'created': datetime.now().isoformat(),
            'platform': self.platform.detect(),
            'packages': self._get_installed_packages(),
        }
        
        snapshot_file = self.env_dir / f"snapshot-{datetime.now().strftime('%Y%m%d-%H%M%S')}.json"
        with open(snapshot_file, 'w') as f:
            json.dump(snapshot, f, indent=2)
        
        return snapshot_file
    
    def _get_installed_packages(self) -> List[Dict]:
        """Get list of installed packages from the environment"""
        try:
            # Run pip freeze inside the container to get actual installed packages
            result = self._run_docker_command([
                'run', '--rm',
                f"venvoy/{self.name}:{self.python_version}",
                'bash', '-c', 'source /opt/conda/bin/activate venvoy && pip freeze'
            ], capture_output=True, text=True, check=True)
            
            packages = []
            for line in result.stdout.strip().split('\n'):
                if line and '==' in line:
                    name, version = line.split('==', 1)
                    packages.append({'name': name, 'version': version})
            
            return packages
        except subprocess.CalledProcessError:
            return []
    
    def _get_installed_r_packages(self, image_name: str) -> List[Dict]:
        """Get list of installed R packages from the container"""
        try:
            # Get R packages using installed.packages()
            result = subprocess.run([
                'docker', 'run', '--rm', image_name,
                'bash', '-c', '''
                R --slave -e "pkgs <- installed.packages(); cat(paste(pkgs[,1], pkgs[,3], sep='=='), sep='\\n')"
                '''
            ], capture_output=True, text=True, check=True)
            
            packages = []
            for line in result.stdout.strip().split('\n'):
                if line and '==' in line:
                    name, version = line.split('==', 1)
                    # Filter out base R packages (they come with R itself)
                    base_packages = {'base', 'compiler', 'datasets', 'graphics', 'grDevices', 
                                   'grid', 'methods', 'parallel', 'splines', 'stats', 'stats4', 
                                   'tcltk', 'tools', 'utils', 'Matrix', 'lattice', 'nlme', 
                                   'mgcv', 'rpart', 'survival', 'MASS', 'class', 'nnet', 
                                   'spatial', 'boot', 'cluster', 'codetools', 'foreign', 
                                   'KernSmooth', 'rpart', 'class', 'nnet', 'spatial'}
                    if name not in base_packages:
                        packages.append({'name': name, 'version': version})
            
            return packages
        except subprocess.CalledProcessError:
            return []
    
    def setup_buildx(self):
        """Setup Docker BuildX for multi-arch builds"""
        # Only available for Docker runtime
        runtime_info = self.container_manager.get_runtime_info()
        if runtime_info['runtime'] == 'docker':
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
            dockerfile_path=dockerfile_path,
            tag=tag,
            context_path=self.env_dir
        )
    
    def push_image(self, tag: str):
        """Push image to registry"""
        # This would need to be implemented in container_manager
        runtime_info = self.container_manager.get_runtime_info()
        if runtime_info['runtime'] == 'docker':
            print("🔧 Image pushing available for Docker runtime")
        else:
            print(f"⚠️  Image pushing not yet implemented for {runtime_info['runtime']} runtime")
    
    def run(self, command: Optional[str] = None, additional_mounts: List[str] = None):
        """Run the environment container with auto-save monitoring"""
        print(f"🔧 run method called with command: {command}")
        # Load configuration to get the image name
        if not self.config_file.exists():
            raise RuntimeError(f"Environment '{self.name}' not found. Run 'venvoy init' first.")
        
        with open(self.config_file, 'r') as f:
            config = yaml.safe_load(f)
        
        image_name = config.get('image_name', f"zaphodbeeblebrox3rd/venvoy:python{self.python_version}")
        
        # Ensure image is available
        self._ensure_image_available(image_name)
        
        # Check editor configuration
        editor_type, editor_available = self._get_editor_config()
        
        # Prepare volume mounts
        home_path = self.platform.get_home_mount_path()
        volumes = {
            home_path: {'bind': '/home/venvoy/host-home', 'mode': 'rw'},
            str(Path.cwd()): {'bind': '/workspace', 'mode': 'rw'}
        }
        
        # Start monitoring thread for auto-save
        import threading
        monitor_thread = threading.Thread(
            target=self._monitor_package_changes, 
            args=(f"{self.name}-runtime",),
            daemon=True
        )
        monitor_thread.start()
        
        # Add additional mounts
        if additional_mounts:
            for mount in additional_mounts:
                if ':' in mount:
                    host_path, container_path = mount.split(':', 1)
                    volumes[host_path] = {'bind': container_path, 'mode': 'rw'}
        
        # Determine the command to run
        if command is None:
            if editor_available:
                if editor_type == "cursor":
                    # Try to launch Cursor and connect to container
                    self._launch_with_cursor(image_name, volumes)
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
                    volume_mounts[host_path] = mount_info['bind']
                
                self.container_manager.run_container(
                    image=image_name,
                    name=f"{self.name}-runtime",
                    command=command,
                    volumes=volume_mounts,
                    detach=False
                )
                
                # Auto-save environment when container exits
                print("💾 Container stopped - saving final environment state...")
                self.auto_save_environment()
            elif editor_available:
                # Launch with editor
                if editor_type == "cursor":
                    # Try to launch Cursor and connect to container
                    self._launch_with_cursor(image_name, volumes)
                elif editor_type == "vscode":
                    # Try to launch VSCode and connect to container
                    self._launch_with_vscode(image_name, volumes)
                else:
                    # Launch interactive shell
                    command = self._get_interactive_shell_command()
                    # Convert volumes format for container manager
                    volume_mounts = {}
                    for host_path, mount_info in volumes.items():
                        volume_mounts[host_path] = mount_info['bind']
                    
                    self.container_manager.run_container(
                        image=image_name,
                        name=f"{self.name}-runtime",
                        command=command,
                        volumes=volume_mounts,
                        detach=False
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
                    volume_mounts[host_path] = mount_info['bind']
                
                self.container_manager.run_container(
                    image=image_name,
                    name=f"{self.name}-runtime",
                    command=command,
                    volumes=volume_mounts,
                    detach=False
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
        
        export_data = {
            'name': self.name,
            'python_version': self.python_version,
            'created': datetime.now().isoformat(),
            'platform': self.platform.detect(),
            'packages': self._get_installed_packages(),
            'base_image': self.platform.get_base_image(self.python_version),
        }
        
        output_file = Path(output_path)
        with open(output_file, 'w') as f:
            yaml.safe_dump(export_data, f, default_flow_style=False)
        
        return str(output_file)
    
    def export_dockerfile(self, output_path: Optional[str] = None) -> str:
        """Export environment as standalone Dockerfile"""
        if output_path is None:
            output_path = f"{self.name}-Dockerfile"
        
        dockerfile_path = self.env_dir / "Dockerfile"
        output_file = Path(output_path)
        
        # Copy Dockerfile with modifications for standalone use
        with open(dockerfile_path, 'r') as src, open(output_file, 'w') as dst:
            content = src.read()
            # Add header comment
            dst.write(f"# Exported venvoy environment: {self.name}\n")
            dst.write(f"# Export date: {datetime.now().isoformat()}\n\n")
            dst.write(content)
        
        return str(output_file)
    
    def export_tarball(self, output_path: Optional[str] = None) -> str:
        """Export environment as tarball for offline use"""
        if output_path is None:
            output_path = f"{self.name}-{self.python_version}.tar.gz"
        
        output_file = Path(output_path)
        
        with tarfile.open(output_file, 'w:gz') as tar:
            # Add environment directory
            tar.add(self.env_dir, arcname=self.name)
            
            # Add export metadata
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as tmp:
                export_info = {
                    'name': self.name,
                    'python_version': self.python_version,
                    'exported': datetime.now().isoformat(),
                    'platform': self.platform.detect(),
                    'usage': f"Extract and run: docker build -t {self.name} {self.name}/"
                }
                json.dump(export_info, tmp, indent=2)
                tmp.flush()
                tar.add(tmp.name, arcname=f"{self.name}/export-info.json")
        
        return str(output_file)
    
    def export_archive(self, output_path: Optional[str] = None, include_base: bool = False) -> str:
        """
        Export complete binary archive for long-term scientific reproducibility.
        
        This creates a comprehensive archive containing:
        - Complete Docker image with all binaries and libraries
        - Environment configuration and metadata
        - Package manifests and dependency trees
        - Platform and architecture information
        
        Args:
            output_path: Path for the archive file
            include_base: Whether to include the base Python image layers
            
        Returns:
            Path to the created archive file
        """
        if output_path is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_path = f"{self.name}-archive-{timestamp}.tar.gz"
        
        output_file = Path(output_path)
        print(f"📦 Creating comprehensive binary archive...")
        print(f"⚠️  This may take several minutes and create a large file (1-5GB)")
        
        # Load configuration to get image name
        if not self.config_file.exists():
            raise RuntimeError(f"Environment '{self.name}' not found. Run 'venvoy init' first.")
        
        with open(self.config_file, 'r') as f:
            config = yaml.safe_load(f)
        
        image_name = config.get('image_name', f"zaphodbeeblebrox3rd/venvoy:python{self.python_version}")
        
        # Ensure image is available
        self._ensure_image_available(image_name)
        
        # Create temporary directory for archive contents
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            archive_dir = temp_path / "venvoy-archive"
            archive_dir.mkdir()
            
            # 1. Export Docker image as tar
            print("🐳 Exporting Docker image...")
            image_tar = archive_dir / "docker-image.tar"
            try:
                result = subprocess.run([
                    'docker', 'save', '-o', str(image_tar), image_name
                ], check=True, capture_output=True, text=True)
                print(f"✅ Docker image exported ({image_tar.stat().st_size / 1024 / 1024:.1f} MB)")
            except subprocess.CalledProcessError as e:
                raise RuntimeError(f"Failed to export Docker image: {e.stderr}")
            
            # 2. Create comprehensive environment manifest
            print("📋 Creating environment manifest...")
            manifest = self._create_comprehensive_manifest(image_name)
            manifest_file = archive_dir / "environment-manifest.json"
            with open(manifest_file, 'w') as f:
                json.dump(manifest, f, indent=2, default=str)
            
            # 3. Export environment configuration
            config_dir = archive_dir / "config"
            config_dir.mkdir()
            if self.env_dir.exists():
                shutil.copytree(self.env_dir, config_dir / "environment", dirs_exist_ok=True)
            
            # 4. Create archive metadata
            archive_metadata = {
                'archive_version': '1.0',
                'created': datetime.now().isoformat(),
                'venvoy_version': '0.1.0',
                'archive_type': 'comprehensive_binary',
                'environment': {
                    'name': self.name,
                    'python_version': self.python_version,
                    'image_name': image_name,
                    'platform': self.platform.detect(),
                },
                'contents': {
                    'docker_image': 'docker-image.tar',
                    'manifest': 'environment-manifest.json',
                    'config': 'config/',
                    'restore_script': 'restore.sh'
                },
                'usage': {
                    'restore_command': 'bash restore.sh',
                    'requirements': ['docker', 'bash'],
                    'estimated_size_mb': image_tar.stat().st_size / 1024 / 1024
                }
            }
            
            metadata_file = archive_dir / "archive-metadata.json"
            with open(metadata_file, 'w') as f:
                json.dump(archive_metadata, f, indent=2, default=str)
            
            # 5. Create restore script
            restore_script = archive_dir / "restore.sh"
            self._create_restore_script(restore_script, archive_metadata)
            restore_script.chmod(0o755)
            
            # 6. Create README
            readme_file = archive_dir / "README.md"
            self._create_archive_readme(readme_file, archive_metadata)
            
            # 7. Create final compressed archive
            print("🗜️  Compressing archive...")
            with tarfile.open(output_file, 'w:gz') as tar:
                tar.add(archive_dir, arcname=f"{self.name}-archive")
            
            # Calculate final size
            final_size_mb = output_file.stat().st_size / 1024 / 1024
            print(f"✅ Archive created: {output_file} ({final_size_mb:.1f} MB)")
        
        return str(output_file)
    
    def export_wheelhouse(self, output_path: Optional[str] = None) -> str:
        """
        Export cross-architecture wheelhouse containing source distributions and multi-arch wheels.
        
        Supports both Python and R environments:
        - Python: Source distributions (sdists) + wheels for multiple architectures
        - R: Source packages + binary packages for multiple architectures
        
        This creates a package cache that:
        - Contains source distributions/packages (architecture-independent)
        - Contains wheels/binaries for multiple architectures (amd64, arm64)
        - Can be installed on any architecture without repository dependency
        - Is self-contained and doesn't require package availability
        
        Args:
            output_path: Path for the wheelhouse archive file
            
        Returns:
            Path to the created wheelhouse archive file
        """
        if output_path is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_path = f"{self.name}-wheelhouse-{timestamp}.tar.gz"
        
        output_file = Path(output_path)
        print(f"📦 Creating cross-architecture wheelhouse...")
        print(f"🌐 This will download source distributions and binaries for multiple architectures")
        print(f"⚠️  This may take several minutes and create a large file (500MB-2GB)")
        
        # Load configuration to get image name and runtime
        if not self.config_file.exists():
            raise RuntimeError(f"Environment '{self.name}' not found. Run 'venvoy init' first.")
        
        with open(self.config_file, 'r') as f:
            config = yaml.safe_load(f)
        
        runtime = config.get('runtime', self.runtime)
        image_name = config.get('image_name')
        if not image_name:
            if runtime == 'r':
                image_name = f"zaphodbeeblebrox3rd/venvoy:r{self.r_version}"
            else:
                image_name = f"zaphodbeeblebrox3rd/venvoy:python{self.python_version}"
        
        # Ensure image is available
        self._ensure_image_available(image_name)
        
        # Get installed packages based on runtime
        print("🔍 Gathering installed packages...")
        python_packages = []
        r_packages = []
        
        if runtime in ['python', 'mixed']:
            try:
                python_packages = self._get_installed_packages()
                if python_packages:
                    print(f"🐍 Found {len(python_packages)} Python packages")
            except Exception as e:
                print(f"⚠️  Warning: Could not get Python packages: {e}")
        
        if runtime in ['r', 'mixed']:
            try:
                r_packages = self._get_installed_r_packages(image_name)
                if r_packages:
                    print(f"📊 Found {len(r_packages)} R packages")
            except Exception as e:
                print(f"⚠️  Warning: Could not get R packages: {e}")
        
        if not python_packages and not r_packages:
            raise RuntimeError("No packages found in environment. Install some packages first.")
        
        total_packages = len(python_packages) + len(r_packages)
        print(f"📦 Total packages to export: {total_packages} ({len(python_packages)} Python, {len(r_packages)} R)")
        
        # Create temporary directory for wheelhouse contents
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            wheelhouse_dir = temp_path / "wheelhouse"
            wheelhouse_dir.mkdir()
            
            # Create subdirectories
            sdists_dir = wheelhouse_dir / "sdists"
            wheels_dir = wheelhouse_dir / "wheels"
            r_source_dir = wheelhouse_dir / "r-packages" / "source"
            r_binaries_dir = wheelhouse_dir / "r-packages" / "binaries"
            sdists_dir.mkdir(parents=True)
            wheels_dir.mkdir(parents=True)
            r_source_dir.mkdir(parents=True)
            r_binaries_dir.mkdir(parents=True)
            
            # Handle Python packages
            if python_packages:
                print("\n🐍 Processing Python packages...")
                # Create requirements file for downloading
                requirements_file = wheelhouse_dir / "requirements.txt"
                with open(requirements_file, 'w') as f:
                    for pkg in python_packages:
                        f.write(f"{pkg['name']}=={pkg['version']}\n")
                
                # Download source distributions (architecture-independent)
                print("📥 Downloading Python source distributions (architecture-independent)...")
                try:
                    self._run_docker_command([
                        'run', '--rm',
                        '-v', f"{sdists_dir}:/workspace/sdists",
                        '-v', f"{requirements_file}:/workspace/requirements.txt:ro",
                        image_name,
                        'bash', '-c', '''
                        source /opt/conda/bin/activate venvoy 2>/dev/null || true
                        pip download -r /workspace/requirements.txt -d /workspace/sdists --no-binary :all: --no-deps || true
                        '''
                    ], check=False)
                    print(f"✅ Python source distributions downloaded")
                except Exception as e:
                    print(f"⚠️  Warning: Some Python source distributions may not be available: {e}")
                
                # Download wheels for multiple architectures
                architectures = ['linux_x86_64', 'linux_aarch64', 'manylinux1_x86_64', 'manylinux2014_x86_64', 
                               'manylinux2014_aarch64', 'manylinux_2_17_x86_64', 'manylinux_2_17_aarch64']
                
                print("📥 Downloading Python wheels for multiple architectures...")
                for arch in architectures:
                    try:
                        self._run_docker_command([
                            'run', '--rm',
                            '-v', f"{wheels_dir}:/workspace/wheels",
                            '-v', f"{requirements_file}:/workspace/requirements.txt:ro",
                            image_name,
                            'bash', '-c', f'''
                            source /opt/conda/bin/activate venvoy 2>/dev/null || true
                            pip download -r /workspace/requirements.txt -d /workspace/wheels --only-binary :all: --platform {arch} --no-deps || true
                            '''
                        ], check=False)
                    except Exception:
                        pass  # Some architectures may not have wheels available
                
                # Also download any available wheels (will get current architecture)
                try:
                    self._run_docker_command([
                        'run', '--rm',
                        '-v', f"{wheels_dir}:/workspace/wheels",
                        '-v', f"{requirements_file}:/workspace/requirements.txt:ro",
                        image_name,
                        'bash', '-c', '''
                        source /opt/conda/bin/activate venvoy 2>/dev/null || true
                        pip download -r /workspace/requirements.txt -d /workspace/wheels --only-binary :all: --no-deps || true
                        '''
                    ], check=False)
                    print(f"✅ Python wheels downloaded")
                except Exception as e:
                    print(f"⚠️  Warning: Some Python wheels may not be available: {e}")
            
            # Handle R packages
            if r_packages:
                print("\n📊 Processing R packages...")
                # Create R package list file
                r_packages_file = wheelhouse_dir / "r-packages.txt"
                with open(r_packages_file, 'w') as f:
                    for pkg in r_packages:
                        f.write(f"{pkg['name']}\n")
                
                # Download R source packages (architecture-independent)
                print("📥 Downloading R source packages (architecture-independent)...")
                try:
                    pkg_names = [pkg['name'] for pkg in r_packages]
                    pkg_list_str = ', '.join([f'"{pkg}"' for pkg in pkg_names])
                    
                    self._run_docker_command([
                        'run', '--rm',
                        '-v', f"{r_source_dir}:/workspace/r-source",
                        image_name,
                        'bash', '-c', f'''
                        R --slave -e "
                        options(repos = c(CRAN = 'https://cran.rstudio.com/'));
                        download.packages(c({pkg_list_str}), destdir='/workspace/r-source', type='source', repos='https://cran.rstudio.com/');
                        " || true
                        '''
                    ], check=False)
                    print(f"✅ R source packages downloaded")
                except Exception as e:
                    print(f"⚠️  Warning: Some R source packages may not be available: {e}")
                
                # Download R binary packages for multiple architectures
                # Note: CRAN provides binaries mainly for x86_64, so we'll try both
                print("📥 Downloading R binary packages for multiple architectures...")
                
                # Try to download binaries for x86_64 (most common)
                try:
                    pkg_names = [pkg['name'] for pkg in r_packages]
                    pkg_list_str = ', '.join([f'"{pkg}"' for pkg in pkg_names])
                    
                    self._run_docker_command([
                        'run', '--rm',
                        '-v', f"{r_binaries_dir}:/workspace/r-binaries",
                        image_name,
                        'bash', '-c', f'''
                        R --slave -e "
                        options(repos = c(CRAN = 'https://cran.rstudio.com/'));
                        download.packages(c({pkg_list_str}), destdir='/workspace/r-binaries', type='binary', repos='https://cran.rstudio.com/');
                        " || true
                        '''
                    ], check=False)
                    print(f"✅ R binary packages downloaded")
                except Exception as e:
                    print(f"⚠️  Warning: Some R binary packages may not be available: {e}")
            
            # Create package manifest
            print("\n📋 Creating package manifest...")
            manifest = {
                'created': datetime.now().isoformat(),
                'venvoy_version': '0.1.0',
                'wheelhouse_version': '1.0',
                'environment': {
                    'name': self.name,
                    'runtime': runtime,
                    'python_version': self.python_version if runtime in ['python', 'mixed'] else None,
                    'r_version': self.r_version if runtime in ['r', 'mixed'] else None,
                    'platform': self.platform.detect(),
                },
                'packages': {
                    'python': python_packages,
                    'r': r_packages,
                },
                'package_count': {
                    'python': len(python_packages),
                    'r': len(r_packages),
                    'total': total_packages,
                },
            }
            
            manifest_file = wheelhouse_dir / "manifest.json"
            with open(manifest_file, 'w') as f:
                json.dump(manifest, f, indent=2, default=str)
            
            # Create restore script
            restore_script = wheelhouse_dir / "restore.sh"
            self._create_wheelhouse_restore_script(restore_script, manifest)
            restore_script.chmod(0o755)
            
            # Create README
            readme_file = wheelhouse_dir / "README.md"
            self._create_wheelhouse_readme(readme_file, manifest)
            
            # Count files
            sdist_count = len(list(sdists_dir.glob("*"))) if sdists_dir.exists() else 0
            wheel_count = len(list(wheels_dir.glob("*"))) if wheels_dir.exists() else 0
            r_source_count = len(list(r_source_dir.glob("*"))) if r_source_dir.exists() else 0
            r_binary_count = len(list(r_binaries_dir.glob("*"))) if r_binaries_dir.exists() else 0
            
            print(f"\n📊 Package cache contents:")
            if python_packages:
                print(f"   - Python source distributions: {sdist_count}")
                print(f"   - Python wheels: {wheel_count}")
            if r_packages:
                print(f"   - R source packages: {r_source_count}")
                print(f"   - R binary packages: {r_binary_count}")
            
            # Create final compressed archive
            print("\n🗜️  Compressing wheelhouse...")
            with tarfile.open(output_file, 'w:gz') as tar:
                tar.add(wheelhouse_dir, arcname=f"{self.name}-wheelhouse")
            
            # Calculate final size
            final_size_mb = output_file.stat().st_size / 1024 / 1024
            print(f"✅ Wheelhouse created: {output_file} ({final_size_mb:.1f} MB)")
        
        return str(output_file)
    
    def import_wheelhouse(self, wheelhouse_path: str, force: bool = False) -> str:
        """
        Import and restore environment from a wheelhouse archive.
        
        Args:
            wheelhouse_path: Path to the wheelhouse archive file
            force: Whether to overwrite existing environment
            
        Returns:
            Name of the restored environment
        """
        wheelhouse_file = Path(wheelhouse_path)
        if not wheelhouse_file.exists():
            raise FileNotFoundError(f"Wheelhouse file not found: {wheelhouse_path}")
        
        print(f"📦 Importing venvoy wheelhouse: {wheelhouse_file.name}")
        
        # Extract wheelhouse to temporary directory
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            print("📂 Extracting wheelhouse...")
            with tarfile.open(wheelhouse_file, 'r:gz') as tar:
                tar.extractall(temp_path)
            
            # Find wheelhouse directory (should be only subdirectory)
            wheelhouse_dirs = [d for d in temp_path.iterdir() if d.is_dir()]
            if not wheelhouse_dirs:
                raise RuntimeError("Invalid wheelhouse: no directories found")
            
            wheelhouse_dir = wheelhouse_dirs[0]
            
            # Read manifest
            manifest_file = wheelhouse_dir / "manifest.json"
            if not manifest_file.exists():
                raise RuntimeError("Invalid wheelhouse: missing manifest.json")
            
            with open(manifest_file, 'r') as f:
                manifest = json.load(f)
            
            env_info = manifest['environment']
            env_name = env_info['name']
            runtime = env_info.get('runtime', 'python')
            python_version = env_info.get('python_version')
            r_version = env_info.get('r_version')
            
            print(f"🔍 Wheelhouse contains environment: {env_name}")
            print(f"   Runtime: {runtime}")
            if python_version:
                print(f"   Python: {python_version}")
            if r_version:
                print(f"   R: {r_version}")
            print(f"   Packages: {manifest['package_count'].get('total', 0)} total")
            print(f"📅 Created: {manifest['created']}")
            
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
            
            # Copy Python packages to vendor directory
            vendor_dir = target_env_dir / "vendor"
            vendor_dir.mkdir(parents=True, exist_ok=True)
            
            if (wheelhouse_dir / "sdists").exists():
                print("📦 Copying Python source distributions...")
                for sdist in (wheelhouse_dir / "sdists").glob("*"):
                    if sdist.is_file():
                        shutil.copy2(sdist, vendor_dir)
            
            if (wheelhouse_dir / "wheels").exists():
                print("📦 Copying Python wheels...")
                for wheel in (wheelhouse_dir / "wheels").glob("*"):
                    if wheel.is_file():
                        shutil.copy2(wheel, vendor_dir)
            
            # Copy R packages
            r_packages_dir = target_env_dir / "r-packages"
            if (wheelhouse_dir / "r-packages").exists():
                r_packages_dir.mkdir(parents=True, exist_ok=True)
                
                if (wheelhouse_dir / "r-packages" / "source").exists():
                    print("📦 Copying R source packages...")
                    r_source_dir = r_packages_dir / "source"
                    r_source_dir.mkdir(parents=True, exist_ok=True)
                    for pkg in (wheelhouse_dir / "r-packages" / "source").glob("*"):
                        if pkg.is_file():
                            shutil.copy2(pkg, r_source_dir)
                
                if (wheelhouse_dir / "r-packages" / "binaries").exists():
                    print("📦 Copying R binary packages...")
                    r_binaries_dir = r_packages_dir / "binaries"
                    r_binaries_dir.mkdir(parents=True, exist_ok=True)
                    for pkg in (wheelhouse_dir / "r-packages" / "binaries").glob("*"):
                        if pkg.is_file():
                            shutil.copy2(pkg, r_binaries_dir)
            
            # Create requirements.txt from manifest (Python)
            python_packages = manifest['packages'].get('python', [])
            if python_packages:
                print("📝 Creating requirements.txt...")
                requirements_file = target_env_dir / "requirements.txt"
                with open(requirements_file, 'w') as f:
                    for pkg in python_packages:
                        f.write(f"{pkg['name']}=={pkg['version']}\n")
            
            # Create r-packages.txt from manifest (R)
            r_packages = manifest['packages'].get('r', [])
            if r_packages:
                print("📝 Creating r-packages.txt...")
                r_packages_file = target_env_dir / "r-packages.txt"
                with open(r_packages_file, 'w') as f:
                    for pkg in r_packages:
                        f.write(f"{pkg['name']}\n")
            
            # Create config.yaml
            config = {
                'name': env_name,
                'runtime': runtime,
                'python_version': python_version,
                'r_version': r_version,
                'created': manifest['created'],
                'imported_from': str(wheelhouse_file),
                'imported_at': datetime.now().isoformat(),
            }
            
            config_file = target_env_dir / "config.yaml"
            with open(config_file, 'w') as f:
                yaml.safe_dump(config, f, default_flow_style=False)
            
            print(f"\n✅ Wheelhouse imported successfully!")
            print(f"🚀 To build and use the environment:")
            print(f"   venvoy init --name {env_name} --force")
            print(f"\n💡 Packages will be installed from local cache (no repository access needed)")
            
            return env_name
    
    def _create_wheelhouse_restore_script(self, script_path: Path, manifest: Dict):
        """Create restore script for the wheelhouse"""
        env_info = manifest['environment']
        runtime = env_info.get('runtime', 'python')
        python_version = env_info.get('python_version')
        r_version = env_info.get('r_version')
        
        python_packages = manifest['packages'].get('python', [])
        r_packages = manifest['packages'].get('r', [])
        
        # Create Python requirements list
        python_packages_list = '\n'.join([f"{pkg['name']}=={pkg['version']}" for pkg in python_packages]) if python_packages else ""
        
        # Create R packages list
        r_packages_list = ', '.join([f'"{pkg["name"]}"' for pkg in r_packages]) if r_packages else ""
        
        # Determine init command based on runtime
        if runtime == 'r':
            init_cmd = f"venvoy init --runtime r --r-version {r_version} --name {env_info['name']}"
            version_info = f"📊 R: {r_version}"
        elif runtime == 'mixed':
            init_cmd = f"venvoy init --runtime mixed --python-version {python_version} --r-version {r_version} --name {env_info['name']}"
            version_info = f"🐍 Python: {python_version}, 📊 R: {r_version}"
        else:
            init_cmd = f"venvoy init --name {env_info['name']} --python-version {python_version}"
            version_info = f"🐍 Python: {python_version}"
        
        script_content = f'''#!/bin/bash
# venvoy Wheelhouse Restore Script
# Generated: {manifest['created']}
# Environment: {env_info['name']}

set -e

echo "🔄 Restoring venvoy environment from wheelhouse..."
echo "📦 Environment: {env_info['name']}"
echo "{version_info}"
echo "📅 Archived: {manifest['created']}"

# Check prerequisites
if ! command -v venvoy &> /dev/null; then
    echo "❌ venvoy CLI is required but not installed"
    echo "   Please install venvoy:"
    echo "   curl -fsSL https://raw.githubusercontent.com/zaphodbeeblebrox3rd/venvoy/main/install.sh | bash"
    exit 1
fi

# Initialize environment if it doesn't exist
if ! venvoy list 2>/dev/null | grep -q "{env_info['name']}"; then
    echo "🔧 Creating environment..."
    {init_cmd}
fi

# Get the environment directory
ENV_DIR="$HOME/.venvoy/environments/{env_info['name']}"
VENDOR_DIR="$ENV_DIR/vendor"
R_PACKAGES_DIR="$ENV_DIR/r-packages"

# Create vendor directories
mkdir -p "$VENDOR_DIR"
mkdir -p "$R_PACKAGES_DIR/source"
mkdir -p "$R_PACKAGES_DIR/binaries"

# Copy Python packages to vendor directory
if [ -d "sdists" ]; then
    echo "📦 Copying Python source distributions..."
    cp -r sdists/* "$VENDOR_DIR/" 2>/dev/null || true
fi
if [ -d "wheels" ]; then
    echo "📦 Copying Python wheels..."
    cp -r wheels/* "$VENDOR_DIR/" 2>/dev/null || true
fi

# Copy R packages
if [ -d "r-packages/source" ]; then
    echo "📦 Copying R source packages..."
    cp -r r-packages/source/* "$R_PACKAGES_DIR/source/" 2>/dev/null || true
fi
if [ -d "r-packages/binaries" ]; then
    echo "📦 Copying R binary packages..."
    cp -r r-packages/binaries/* "$R_PACKAGES_DIR/binaries/" 2>/dev/null || true
fi

# Create requirements.txt from manifest (Python)
'''
        
        if python_packages:
            script_content += f'''if [ ! -z "{python_packages_list}" ]; then
    echo "📝 Creating requirements.txt..."
    REQUIREMENTS_FILE="$ENV_DIR/requirements.txt"
    cat > "$REQUIREMENTS_FILE" <<PYEOF
{python_packages_list}
PYEOF
fi
'''
        
        if r_packages:
            script_content += f'''
# Create R packages list
if [ ! -z "{r_packages_list}" ]; then
    echo "📝 Creating r-packages.txt..."
    R_PACKAGES_FILE="$ENV_DIR/r-packages.txt"
    cat > "$R_PACKAGES_FILE" <<REOF
{chr(10).join([pkg['name'] for pkg in r_packages])}
REOF
fi
'''
        
        script_content += f'''
echo ""
echo "✅ Wheelhouse restored successfully!"
echo ""
echo "🚀 To rebuild environment with packages:"
echo "   venvoy init --name {env_info['name']} --force"
echo ""
if [ ! -z "{python_packages_list}" ]; then
    echo "💡 Python packages will be installed from local vendor directory (no PyPI needed)"
fi
if [ ! -z "{r_packages_list}" ]; then
    echo "💡 R packages will be installed from local r-packages directory (no CRAN needed)"
fi
'''
        
        with open(script_path, 'w') as f:
            f.write(script_content)
    
    def _create_wheelhouse_readme(self, readme_path: Path, manifest: Dict):
        """Create README for the wheelhouse"""
        env_info = manifest['environment']
        runtime = env_info.get('runtime', 'python')
        pkg_counts = manifest.get('package_count', {})
        
        # Build version info
        version_parts = []
        if env_info.get('python_version'):
            version_parts.append(f"Python {env_info['python_version']}")
        if env_info.get('r_version'):
            version_parts.append(f"R {env_info['r_version']}")
        version_info = ", ".join(version_parts) if version_parts else "Unknown"
        
        # Build contents section
        contents_list = []
        if pkg_counts.get('python', 0) > 0:
            contents_list.append("- **Python Source Distributions (sdists/)**: Architecture-independent source packages")
            contents_list.append("- **Python Wheels (wheels/)**: Pre-built packages for multiple architectures")
        if pkg_counts.get('r', 0) > 0:
            contents_list.append("- **R Source Packages (r-packages/source/)**: Architecture-independent R source packages")
            contents_list.append("- **R Binary Packages (r-packages/binaries/)**: Pre-built R packages for multiple architectures")
        contents_list.append("- **Manifest (manifest.json)**: Package specifications and metadata")
        contents_list.append("- **Restore Script (restore.sh)**: Automated restoration script")
        contents_section = "\n".join(contents_list)
        
        # Build restore instructions
        restore_instructions = []
        if pkg_counts.get('python', 0) > 0:
            restore_instructions.append("```bash")
            restore_instructions.append("# Copy Python packages")
            restore_instructions.append("mkdir -p ~/.venvoy/environments/{}/vendor".format(env_info['name']))
            restore_instructions.append("cp -r sdists/* ~/.venvoy/environments/{}/vendor/".format(env_info['name']))
            restore_instructions.append("cp -r wheels/* ~/.venvoy/environments/{}/vendor/".format(env_info['name']))
            restore_instructions.append("```")
        if pkg_counts.get('r', 0) > 0:
            restore_instructions.append("```bash")
            restore_instructions.append("# Copy R packages")
            restore_instructions.append("mkdir -p ~/.venvoy/environments/{}/r-packages/{{source,binaries}}".format(env_info['name']))
            restore_instructions.append("cp -r r-packages/source/* ~/.venvoy/environments/{}/r-packages/source/".format(env_info['name']))
            restore_instructions.append("cp -r r-packages/binaries/* ~/.venvoy/environments/{}/r-packages/binaries/".format(env_info['name']))
            restore_instructions.append("```")
        
        restore_section = "\n".join(restore_instructions)
        
        # Build architecture compatibility section
        arch_section = """When you restore on a different architecture:
1. **Python packages**: Pip will use wheels for the target architecture if available, otherwise build from source
2. **R packages**: R will use binary packages for the target architecture if available, otherwise build from source
3. All packages are self-contained - no repository access needed"""
        
        readme_content = f'''# venvoy Cross-Architecture Wheelhouse

## Wheelhouse Information

- **Environment Name**: {env_info['name']}
- **Runtime**: {runtime.title()}
- **Versions**: {version_info}
- **Created**: {manifest['created']}
- **Package Count**: {pkg_counts.get('total', 0)} total ({pkg_counts.get('python', 0)} Python, {pkg_counts.get('r', 0)} R)

## Purpose

This wheelhouse contains a **cross-architecture package cache** that allows you to:
- ✅ Install packages on **any architecture** (amd64, arm64)
- ✅ Work **offline** without repository dependency (PyPI/CRAN)
- ✅ Protect against **package abandonment** (packages removed from repositories)
- ✅ Ensure **reproducible installations** across different systems

## Contents

{contents_section}

## Restoration

### Quick Restore
```bash
bash restore.sh
venvoy init --name {env_info['name']} --force
```

### Manual Restore
```bash
# 1. Extract wheelhouse
tar -xzf {env_info['name']}-wheelhouse-*.tar.gz

# 2. Copy packages to environment directories
{restore_section}

# 3. Rebuild environment
venvoy init --name {env_info['name']} --force
```

## Cross-Architecture Compatibility

This wheelhouse works on:
- **linux/amd64** (Intel/AMD x86_64)
- **linux/arm64** (Apple Silicon, ARM servers)

{arch_section}

## Advantages Over Binary Archives

- ✅ **Cross-architecture**: Works on amd64 and arm64
- ✅ **Smaller size**: Only packages, not full Docker images
- ✅ **Flexible**: Can rebuild for target architecture
- ✅ **Self-contained**: No dependency on repository availability

## Advantages Over YAML Exports

- ✅ **Offline**: No need for PyPI/CRAN access
- ✅ **Package protection**: Works even if packages are removed from repositories
- ✅ **Faster**: Pre-downloaded packages, no network needed

## R Package Notes

R packages are distributed differently than Python:
- **Source packages** (`.tar.gz`) are architecture-independent and can be built on any platform
- **Binary packages** are architecture-specific (`.tar.gz` on Linux, `.tgz` on macOS)
- CRAN provides binaries mainly for x86_64 Linux, so ARM systems often need to build from source
- This wheelhouse includes both source and binaries for maximum compatibility

---

Generated by venvoy - Scientific Python and R Environment Management
https://github.com/zaphodbeeblebrox3rd/venvoy
'''
        
        with open(readme_path, 'w') as f:
            f.write(readme_content)
    
    def _create_comprehensive_manifest(self, image_name: str) -> Dict:
        manifest = {
            'created': datetime.now().isoformat(),
            'image_name': image_name,
            'platform': self.platform.detect(),
            'python_version': self.python_version,
            'packages': {
                'conda': [],
                'pip': [],
                'system': []
            },
            'system_info': {},
            'dependency_tree': {}
        }
        
        try:
            # Get detailed package information from container
            print("🔍 Analyzing package dependencies...")
            
            # Get conda packages with detailed info
            conda_result = subprocess.run([
                'docker', 'run', '--rm', image_name,
                'bash', '-c', 'source /opt/conda/bin/activate venvoy && conda list --json'
            ], capture_output=True, text=True, check=True)
            
            conda_packages = json.loads(conda_result.stdout)
            manifest['packages']['conda'] = conda_packages
            
            # Get pip packages with detailed info
            pip_result = subprocess.run([
                'docker', 'run', '--rm', image_name,
                'bash', '-c', 'source /opt/conda/bin/activate venvoy && pip list --format=json'
            ], capture_output=True, text=True, check=True)
            
            pip_packages = json.loads(pip_result.stdout)
            manifest['packages']['pip'] = pip_packages
            
            # Get system packages (Debian/Ubuntu)
            system_result = subprocess.run([
                'docker', 'run', '--rm', image_name,
                'bash', '-c', 'dpkg-query -W -f="${Package}\\t${Version}\\t${Architecture}\\n"'
            ], capture_output=True, text=True, check=True)
            
            system_packages = []
            for line in system_result.stdout.strip().split('\n'):
                if line:
                    parts = line.split('\t')
                    if len(parts) >= 3:
                        system_packages.append({
                            'name': parts[0],
                            'version': parts[1],
                            'architecture': parts[2]
                        })
            manifest['packages']['system'] = system_packages
            
            # Get Python and system information
            info_result = subprocess.run([
                'docker', 'run', '--rm', image_name,
                'bash', '-c', '''
                source /opt/conda/bin/activate venvoy
                echo "PYTHON_VERSION=$(python --version)"
                echo "PYTHON_PATH=$(which python)"
                echo "CONDA_VERSION=$(conda --version)"
                echo "OS_INFO=$(cat /etc/os-release | grep PRETTY_NAME)"
                echo "ARCHITECTURE=$(uname -m)"
                echo "KERNEL=$(uname -r)"
                '''
            ], capture_output=True, text=True, check=True)
            
            system_info = {}
            for line in info_result.stdout.strip().split('\n'):
                if '=' in line:
                    key, value = line.split('=', 1)
                    system_info[key] = value
            manifest['system_info'] = system_info
            
            # Get dependency tree for critical packages
            print("🌳 Building dependency tree...")
            dep_result = subprocess.run([
                'docker', 'run', '--rm', image_name,
                'bash', '-c', 'source /opt/conda/bin/activate venvoy && pip show --verbose numpy pandas matplotlib jupyter || true'
            ], capture_output=True, text=True, check=True)
            
            # Parse dependency information (simplified)
            manifest['dependency_tree']['pip_show_output'] = dep_result.stdout
            
        except subprocess.CalledProcessError as e:
            print(f"⚠️  Warning: Could not gather complete manifest: {e}")
            manifest['warning'] = f"Incomplete manifest due to: {e}"
        except json.JSONDecodeError as e:
            print(f"⚠️  Warning: Could not parse package JSON: {e}")
            manifest['warning'] = f"Package parsing error: {e}"
        
        return manifest
    
    def _create_restore_script(self, script_path: Path, metadata: Dict):
        """Create restore script for the archive"""
        script_content = f'''#!/bin/bash
# venvoy Archive Restore Script
# Generated: {metadata['created']}
# Environment: {metadata['environment']['name']}

set -e

echo "🔄 Restoring venvoy environment from archive..."
echo "📦 Environment: {metadata['environment']['name']}"
echo "🐍 Python: {metadata['environment']['python_version']}"
echo "📅 Archived: {metadata['created']}"

# Check prerequisites
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is required but not installed"
    echo "   Please install Docker: https://docs.docker.com/get-docker/"
    exit 1
fi

# Check if Docker is running
if ! docker info &> /dev/null; then
    echo "❌ Docker is not running"
    echo "   Please start Docker and try again"
    exit 1
fi

# Load Docker image
echo "🐳 Loading Docker image..."
if [ -f "docker-image.tar" ]; then
    docker load -i docker-image.tar
    echo "✅ Docker image loaded"
else
    echo "❌ docker-image.tar not found"
    exit 1
fi

# Create venvoy directory structure
echo "📁 Setting up venvoy directories..."
mkdir -p "$HOME/.venvoy/environments"
mkdir -p "$HOME/.venvoy/projects"

# Copy environment configuration
if [ -d "config/environment" ]; then
    cp -r "config/environment" "$HOME/.venvoy/environments/{metadata['environment']['name']}"
    echo "✅ Environment configuration restored"
fi

# Install venvoy CLI if not present
if ! command -v venvoy &> /dev/null; then
    echo "⚠️  venvoy CLI not found"
    echo "   Installing venvoy CLI..."
    
    # Try to install venvoy
    if command -v pip &> /dev/null; then
        pip install git+https://github.com/zaphodbeeblebrox3rd/venvoy.git
    else
        echo "❌ pip not found. Please install venvoy manually:"
        echo "   curl -fsSL https://raw.githubusercontent.com/zaphodbeeblebrox3rd/venvoy/main/install.sh | bash"
        exit 1
    fi
fi

echo ""
echo "✅ Archive restored successfully!"
echo ""
echo "🚀 To use your restored environment:"
echo "   venvoy run --name {metadata['environment']['name']}"
echo ""
echo "📋 To view environment details:"
echo "   venvoy history --name {metadata['environment']['name']}"
echo ""
echo "🔍 Archive contents:"
echo "   - Docker image: {metadata['environment']['image_name']}"
echo "   - Configuration: ~/.venvoy/environments/{metadata['environment']['name']}"
echo "   - Manifest: environment-manifest.json"
echo ""
'''
        
        with open(script_path, 'w') as f:
            f.write(script_content)
    
    def _create_archive_readme(self, readme_path: Path, metadata: Dict):
        """Create README for the archive"""
        readme_content = f'''# venvoy Environment Archive

## Archive Information

- **Environment Name**: {metadata['environment']['name']}
- **Python Version**: {metadata['environment']['python_version']}
- **Created**: {metadata['created']}
- **Archive Type**: Comprehensive Binary Archive
- **Size**: ~{metadata['usage']['estimated_size_mb']:.1f} MB

## Purpose

This archive contains a complete, self-contained Python environment for **scientific reproducibility**. Unlike standard requirements.txt exports, this archive includes:

- ✅ Complete Docker image with all binaries and libraries
- ✅ System packages and dependencies
- ✅ Exact package versions with full dependency trees
- ✅ Platform and architecture information
- ✅ Environment configuration and metadata

## Use Cases

- **Long-term Archival**: Store environments for years without dependency on external repositories
- **Regulatory Compliance**: Meet requirements for reproducible research documentation
- **Peer Review**: Share exact computational environments with reviewers
- **Cross-institutional Collaboration**: Ensure identical results across different computing environments
- **Package Abandonment Protection**: Continue using environments even if packages are removed from PyPI

## Contents

```
{metadata['environment']['name']}-archive/
├── docker-image.tar          # Complete Docker image
├── environment-manifest.json # Comprehensive package manifest
├── config/                   # Environment configuration
├── restore.sh               # Restoration script
├── archive-metadata.json    # Archive metadata
└── README.md               # This file
```

## Restoration

### Quick Restore
```bash
bash restore.sh
```

### Manual Restore
```bash
# 1. Load Docker image
docker load -i docker-image.tar

# 2. Install venvoy (if not already installed)
curl -fsSL https://raw.githubusercontent.com/zaphodbeeblebrox3rd/venvoy/main/install.sh | bash

# 3. Copy configuration
mkdir -p ~/.venvoy/environments
cp -r config/environment ~/.venvoy/environments/{metadata['environment']['name']}

# 4. Run environment
venvoy run --name {metadata['environment']['name']}
```

## Requirements

- Docker (any recent version)
- Bash shell
- ~{metadata['usage']['estimated_size_mb']:.0f} MB free disk space

## Verification

After restoration, verify the environment:

```bash
# Check environment status
venvoy history --name {metadata['environment']['name']}

# Run environment
venvoy run --name {metadata['environment']['name']}

# Inside the environment, verify packages
python -c "import numpy, pandas, matplotlib; print('✅ Core packages working')"
```

## Scientific Reproducibility

This archive ensures bit-for-bit reproducible results by capturing:

1. **Exact Binary Versions**: All compiled libraries and dependencies
2. **System Dependencies**: Operating system packages and configurations  
3. **Architecture Details**: Platform-specific optimizations and builds
4. **Complete Dependency Tree**: All transitive dependencies with exact versions
5. **Environment State**: Configuration files and settings

## Archive Metadata

- **venvoy Version**: {metadata.get('venvoy_version', 'Unknown')}
- **Archive Version**: {metadata.get('archive_version', '1.0')}
- **Platform**: {metadata['environment']['platform']}
- **Docker Image**: {metadata['environment']['image_name']}

---

Generated by venvoy - Scientific Python Environment Management
https://github.com/zaphodbeeblebrox3rd/venvoy
'''
        
        with open(readme_path, 'w') as f:
            f.write(readme_content)
    
    def import_archive(self, archive_path: str, force: bool = False) -> str:
        """
        Import and restore environment from a comprehensive binary archive.
        
        Args:
            archive_path: Path to the venvoy archive file
            force: Whether to overwrite existing environment
            
        Returns:
            Name of the restored environment
        """
        archive_file = Path(archive_path)
        if not archive_file.exists():
            raise FileNotFoundError(f"Archive file not found: {archive_path}")
        
        print(f"📦 Importing venvoy archive: {archive_file.name}")
        
        # Extract archive to temporary directory
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            print("📂 Extracting archive...")
            with tarfile.open(archive_file, 'r:gz') as tar:
                tar.extractall(temp_path)
            
            # Find archive directory (should be only subdirectory)
            archive_dirs = [d for d in temp_path.iterdir() if d.is_dir()]
            if not archive_dirs:
                raise RuntimeError("Invalid archive: no directories found")
            
            archive_dir = archive_dirs[0]
            
            # Read archive metadata
            metadata_file = archive_dir / "archive-metadata.json"
            if not metadata_file.exists():
                raise RuntimeError("Invalid archive: missing metadata")
            
            with open(metadata_file, 'r') as f:
                metadata = json.load(f)
            
            env_name = metadata['environment']['name']
            python_version = metadata['environment']['python_version']
            
            print(f"🔍 Archive contains environment: {env_name} (Python {python_version})")
            print(f"📅 Created: {metadata['created']}")
            
            # Check if environment already exists
            target_env_dir = self.config_dir / "environments" / env_name
            if target_env_dir.exists() and not force:
                raise RuntimeError(
                    f"Environment '{env_name}' already exists. Use --force to overwrite."
                )
            
            # Load Docker image
            docker_image_file = archive_dir / "docker-image.tar"
            if docker_image_file.exists():
                print("🐳 Loading Docker image...")
                try:
                    subprocess.run([
                        'docker', 'load', '-i', str(docker_image_file)
                    ], check=True, capture_output=True)
                    print("✅ Docker image loaded")
                except subprocess.CalledProcessError as e:
                    raise RuntimeError(f"Failed to load Docker image: {e}")
            else:
                print("⚠️  No Docker image found in archive")
            
            # Restore environment configuration
            config_dir = archive_dir / "config" / "environment"
            if config_dir.exists():
                print("📁 Restoring environment configuration...")
                if target_env_dir.exists():
                    shutil.rmtree(target_env_dir)
                shutil.copytree(config_dir, target_env_dir)
                print("✅ Configuration restored")
            
            # Create projects directory
            projects_dir = self.config_dir / "projects" / env_name
            projects_dir.mkdir(parents=True, exist_ok=True)
            
            print(f"✅ Environment '{env_name}' imported successfully!")
            print(f"🚀 Run with: venvoy run --name {env_name}")
            
            return env_name
    
    def auto_save_environment(self):
        """Auto-save environment.yml to venvoy-projects directory with timestamp"""
        try:
            # Get current packages from container
            packages = self._get_installed_packages()
            
            # Create conda-style environment.yml
            env_data = {
                'name': self.name,
                'channels': ['conda-forge', 'defaults'],
                'dependencies': [],
                'exported': datetime.now().isoformat(),
                'venvoy_version': '0.1.0'
            }
            
            # Separate conda and pip packages
            conda_packages = []
            pip_packages = []
            
            for pkg in packages:
                # Try to determine if it's available via conda-forge
                # For simplicity, we'll put common scientific packages in conda section
                scientific_packages = {
                    'numpy', 'pandas', 'matplotlib', 'scipy', 'scikit-learn',
                    'jupyter', 'ipython', 'seaborn', 'plotly', 'bokeh',
                    'tensorflow', 'pytorch', 'torch', 'transformers'
                }
                
                if pkg['name'].lower() in scientific_packages:
                    conda_packages.append(f"{pkg['name']}={pkg['version']}")
                else:
                    pip_packages.append(f"{pkg['name']}=={pkg['version']}")
            
            # Add conda packages
            env_data['dependencies'].extend(conda_packages)
            
            # Add pip section if there are pip packages
            if pip_packages:
                env_data['dependencies'].append({
                    'pip': pip_packages
                })
            
            # Create timestamped filename
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            env_file = self.projects_dir / f"environment_{timestamp}.yml"
            
            # Save timestamped environment file
            with open(env_file, 'w') as f:
                yaml.safe_dump(env_data, f, default_flow_style=False, sort_keys=False)
            
            # Also maintain current environment.yml as latest
            current_env_file = self.projects_dir / "environment.yml"
            with open(current_env_file, 'w') as f:
                yaml.safe_dump(env_data, f, default_flow_style=False, sort_keys=False)
            
            # Update timestamp file
            timestamp_file = self.projects_dir / ".last_updated"
            with open(timestamp_file, 'w') as f:
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
                with open(env_file, 'r') as f:
                    env_data = yaml.safe_load(f)
                
                # Extract timestamp from filename
                filename = env_file.name
                if filename.startswith('environment_') and filename.endswith('.yml'):
                    timestamp_str = filename[12:-4]  # Remove 'environment_' and '.yml'
                    
                    try:
                        # Parse timestamp
                        timestamp = datetime.strptime(timestamp_str, '%Y%m%d_%H%M%S')
                        
                        # Count packages
                        package_count = 0
                        pip_count = 0
                        
                        for dep in env_data.get('dependencies', []):
                            if isinstance(dep, dict) and 'pip' in dep:
                                pip_count = len(dep['pip'])
                            elif isinstance(dep, str):
                                package_count += 1
                        
                        exports.append({
                            'file': env_file,
                            'timestamp': timestamp,
                            'timestamp_str': timestamp_str,
                            'formatted_time': timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                            'conda_packages': package_count,
                            'pip_packages': pip_count,
                            'total_packages': package_count + pip_count,
                            'exported_date': env_data.get('exported', 'Unknown'),
                            'venvoy_version': env_data.get('venvoy_version', 'Unknown')
                        })
                        
                    except ValueError:
                        # Skip files with invalid timestamp format
                        continue
                        
            except (yaml.YAMLError, FileNotFoundError):
                continue
        
        # Sort by timestamp (newest first)
        exports.sort(key=lambda x: x['timestamp'], reverse=True)
        return exports
    
    def select_environment_export(self) -> Optional[Path]:
        """Present user with a list of environment exports to choose from"""
        exports = self.list_environment_exports()
        
        if not exports:
            return None
        
        print(f"\n📋 Found {len(exports)} previous environment exports for '{self.name}':")
        print("=" * 80)
        
        for i, export in enumerate(exports, 1):
            print(f"{i:2d}. {export['formatted_time']} - "
                  f"{export['total_packages']} packages "
                  f"({export['conda_packages']} conda, {export['pip_packages']} pip)")
        
        print(f"{len(exports) + 1:2d}. Create new environment (skip restore)")
        print("=" * 80)
        
        while True:
            try:
                choice = input(f"\nSelect environment to restore (1-{len(exports) + 1}): ").strip()
                
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
                    return selected['file']
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
            
            # Copy the export file to requirements files
            with open(export_file, 'r') as f:
                env_data = yaml.safe_load(f)
            
            # Extract conda and pip dependencies
            conda_deps = []
            pip_deps = []
            
            for dep in env_data.get('dependencies', []):
                if isinstance(dep, dict) and 'pip' in dep:
                    pip_deps.extend(dep['pip'])
                elif isinstance(dep, str):
                    conda_deps.append(dep)
            
            # Write to requirements files
            if conda_deps:
                conda_req_file = self.env_dir / "conda-requirements.txt"
                with open(conda_req_file, 'w') as f:
                    for dep in conda_deps:
                        # Convert conda format (name=version) to pip format (name==version)
                        if '=' in dep and not dep.startswith('='):
                            dep = dep.replace('=', '==', 1)
                        f.write(f"{dep}\n")
            
            if pip_deps:
                pip_req_file = self.env_dir / "requirements.txt"
                with open(pip_req_file, 'w') as f:
                    for dep in pip_deps:
                        f.write(f"{dep}\n")
            
            print(f"✅ Environment configuration restored")
            print(f"📦 {len(conda_deps)} conda packages, {len(pip_deps)} pip packages")
            
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
                result = self._run_docker_command([
                    'exec', container_name,
                    'test', '-f', '/tmp/venvoy_package_changed'
                ], capture_output=True)
                
                if result.returncode == 0:
                    # Signal file exists - packages changed
                    print("📦 Package change detected!")
                    
                    # Auto-save environment
                    self.auto_save_environment()
                    
                    # Remove signal file
                    self._run_docker_command([
                        'exec', container_name,
                        'rm', '-f', '/tmp/venvoy_package_changed'
                    ], capture_output=True)
                
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
                        with open(config_file, 'r') as f:
                            config = yaml.safe_load(f)
                        
                        # Check if container exists
                        containers = self.container_manager.list_containers(all_containers=True)
                        status = "stopped"
                        for container in containers:
                            if container['name'] == config['name']:
                                status = container['status']
                                break
                        
                        environments.append({
                            'name': config['name'],
                            'python_version': config['python_version'],
                            'created': config['created'],
                            'status': status
                        })
                    except (yaml.YAMLError, KeyError):
                        continue
        
        return environments
    
    def _get_editor_config(self) -> tuple[str, bool]:
        """Get editor configuration from config"""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    config = yaml.safe_load(f)
                
                # Check new format first
                if 'editor_type' in config and 'editor_available' in config:
                    return config['editor_type'], config['editor_available']
                
                # Backward compatibility with old vscode_available format
                if config.get('vscode_available', False):
                    return "vscode", True
                    
            except (yaml.YAMLError, KeyError):
                pass
        
        return "none", False  # Default to no editor
    
    def _get_vscode_availability(self) -> bool:
        """Get VSCode availability from config (backward compatibility)"""
        editor_type, editor_available = self._get_editor_config()
        return editor_available and editor_type == "vscode"
    
    def _get_interactive_shell_command(self) -> str:
        """Get the appropriate interactive shell command"""
        # Return a command that activates conda and starts an interactive shell
        return '/bin/bash -c "source /opt/conda/bin/activate venvoy && echo \\"🚀 Welcome to your AI-ready venvoy environment!\\" && echo \\"🐍 Python $(python --version)\\" && echo \\"📦 Conda environment: $CONDA_DEFAULT_ENV\\" && echo \\"⚡ Package managers: mamba (fast), uv (ultra-fast), pip (standard)\\" && echo \\"🤖 AI packages: numpy, pandas, matplotlib, jupyter, and more\\" && echo \\"💡 Your home directory is mounted at /home/venvoy/host-home\\" && echo \\"📂 Current workspace: $(pwd)\\" && echo && exec /bin/bash"'
    
    def _launch_with_cursor(self, image_tag: str, volumes: Dict):
        """Launch container and connect Cursor"""
        import subprocess
        import time
        
        # First, start the container in detached mode
        try:
            container = self.container_manager.run_container(
                image=image_tag,
                name=f"{self.name}-runtime",
                command="sleep infinity",  # Keep container running
                volumes=volumes,
                detach=True
            )
            
            print("🚀 Container started successfully!")
            print("🧠 Launching Cursor with AI assistance...")
            
            # Give container a moment to start
            time.sleep(2)
            
            # Launch Cursor with remote containers extension
            cursor_command = [
                'cursor',
                '--folder-uri',
                f'vscode-remote://attached-container+{container.name}/workspace'
            ]
            
            try:
                subprocess.run(cursor_command, check=True)
                print("✅ Cursor connected to container with AI features enabled!")
                print("🤖 Ready for AI-assisted coding!")
                print(f"💡 When you're done, stop the container with: docker stop {container.name}")
            except subprocess.CalledProcessError:
                print("⚠️  Failed to launch Cursor. Falling back to interactive shell.")
                # Stop the detached container and run interactively instead
                container.stop()
                command = self._get_interactive_shell_command()
                self.container_manager.run_container(
                    image=image_tag,
                    name=f"{self.name}-runtime",
                    command=command,
                    volumes=volumes,
                    detach=False
                )
                
        except Exception as e:
            print(f"Failed to launch with Cursor: {e}")
            print("🐚 Falling back to interactive shell...")
            command = self._get_interactive_shell_command()
            self.container_manager.run_container(
                image=image_tag,
                name=f"{self.name}-runtime",
                command=command,
                volumes=volumes,
                detach=False
            )
    
    def _launch_with_vscode(self, image_tag: str, volumes: Dict):
        """Launch container and connect VSCode"""
        import subprocess
        import time
        
        # First, start the container in detached mode
        try:
            container = self.container_manager.run_container(
                image=image_tag,
                name=f"{self.name}-runtime",
                command="sleep infinity",  # Keep container running
                volumes=volumes,
                detach=True
            )
            
            print("🚀 Container started successfully!")
            print("🔧 Launching VSCode and connecting to container...")
            
            # Give container a moment to start
            time.sleep(2)
            
            # Launch VSCode with remote containers extension
            vscode_command = [
                'code',
                '--folder-uri',
                f'vscode-remote://attached-container+{container.name}/workspace'
            ]
            
            try:
                subprocess.run(vscode_command, check=True)
                print("✅ VSCode connected to container!")
                print("💡 When you're done, stop the container with: docker stop {container.name}")
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
                    detach=False
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
                detach=False
            )
    
    def _update_config(self, updates: Dict[str, Any]):
        """Update environment configuration"""
        if self.config_file.exists():
            with open(self.config_file, 'r') as f:
                config = yaml.safe_load(f)
        else:
            config = {}
        
        config.update(updates)
        
        with open(self.config_file, 'w') as f:
            yaml.safe_dump(config, f, default_flow_style=False) 