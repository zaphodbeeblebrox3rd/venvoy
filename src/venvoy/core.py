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

from .docker_manager import DockerManager
from .platform_detector import PlatformDetector


class VenvoyEnvironment:
    """Manages portable Python environments"""
    
    def __init__(self, name: str = "venvoy-env", python_version: str = "3.11"):
        self.name = name
        self.python_version = python_version
        self.platform = PlatformDetector()
        self.docker_manager = DockerManager()
        self.config_dir = Path.home() / ".venvoy"
        self.env_dir = self.config_dir / "environments" / name
        self.config_file = self.env_dir / "config.yaml"
        
        # Create venvoy-projects directory for auto-saved environments
        self.projects_dir = Path.home() / "venvoy-projects" / name
        
        # Ensure directories exist
        self.config_dir.mkdir(exist_ok=True)
        (self.config_dir / "environments").mkdir(exist_ok=True)
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
        image_name = f"zaphodbeeblebrox3rd/venvoy:python{self.python_version}"
        print(f"📦 Setting up Python {self.python_version} environment...")
        self._ensure_image_available(image_name)
        
        # Check for existing environment exports and offer to restore
        selected_export = self.select_environment_export()
        
        if selected_export:
            # Restore from selected export
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
            'python_version': self.python_version,
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
    
    def _ensure_image_available(self, image_name: str):
        """Ensure the venvoy image is available locally"""
        try:
            # Check if image exists locally
            result = subprocess.run([
                'docker', 'image', 'inspect', image_name
            ], capture_output=True, check=True)
            
        except subprocess.CalledProcessError:
            # Image doesn't exist, pull it
            print(f"⬇️  Downloading environment (one-time setup)...")
            try:
                subprocess.run([
                    'docker', 'pull', image_name
                ], check=True)
                print(f"✅ Environment ready")
            except subprocess.CalledProcessError as e:
                raise RuntimeError(f"Failed to download environment: {e}")
    
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
    echo 'export PS1="(🤖 venvoy) \\u@\\h:\\w\\$ "' >> ~/.bashrc && \\
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
            subprocess.run([
                'docker', 'build',
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
                        subprocess.run([
                            'docker', 'run', '--rm',
                            '-v', f"{req_file}:/workspace/{req_filename}:ro",
                            '-v', f"{vendor_dir}:/workspace/vendor",
                            image_tag,
                            'bash', '-c', f'source /opt/conda/bin/activate venvoy && uv pip download -r /workspace/{req_filename} --dest /workspace/vendor --no-deps'
                        ], check=True)
                        print(f"✅ Downloaded wheels using uv (ultra-fast) inside container")
                    except subprocess.CalledProcessError:
                        # Fallback to pip if uv fails (inside container)
                        try:
                            subprocess.run([
                                'docker', 'run', '--rm',
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
            result = subprocess.run([
                'docker', 'run', '--rm',
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
    
    def setup_buildx(self):
        """Setup Docker BuildX for multi-arch builds"""
        self.docker_manager.setup_buildx()
    
    def build_multiarch(self, tag: Optional[str] = None) -> str:
        """Build multi-architecture image"""
        if tag is None:
            tag = f"venvoy/{self.name}:{self.python_version}-multiarch"
        
        dockerfile_path = self.env_dir / "Dockerfile"
        return self.docker_manager.build_multiarch_image(
            dockerfile_path=dockerfile_path,
            tag=tag,
            context_path=self.env_dir
        )
    
    def push_image(self, tag: str):
        """Push image to registry"""
        self.docker_manager.push_image(tag)
    
    def run(self, command: Optional[str] = None, additional_mounts: List[str] = None):
        """Run the environment container with auto-save monitoring"""
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
            if not editor_available or command is not None:
                self.docker_manager.run_container(
                    image=image_name,
                    name=f"{self.name}-runtime",
                    command=command,
                    volumes=volumes,
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
                result = subprocess.run([
                    'docker', 'exec', container_name,
                    'test', '-f', '/tmp/venvoy_package_changed'
                ], capture_output=True)
                
                if result.returncode == 0:
                    # Signal file exists - packages changed
                    print("📦 Package change detected!")
                    
                    # Auto-save environment
                    self.auto_save_environment()
                    
                    # Remove signal file
                    subprocess.run([
                        'docker', 'exec', container_name,
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
                        containers = self.docker_manager.list_containers(all_containers=True)
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
            container = self.docker_manager.run_container(
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
                self.docker_manager.run_container(
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
            self.docker_manager.run_container(
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
            container = self.docker_manager.run_container(
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
                self.docker_manager.run_container(
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
            self.docker_manager.run_container(
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