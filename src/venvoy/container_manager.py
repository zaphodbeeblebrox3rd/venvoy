"""
Container runtime abstraction for venvoy
Supports Docker, Apptainer/Singularity, and Podman for HPC compatibility
"""

import subprocess
import sys
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from enum import Enum
import json
import os

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
        
    def _detect_best_runtime(self) -> ContainerRuntime:
        """Detect the best available container runtime for the environment"""
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
        if self._check_runtime_available(ContainerRuntime.DOCKER):
            return ContainerRuntime.DOCKER
        elif self._check_runtime_available(ContainerRuntime.APPTAINER):
            return ContainerRuntime.APPTAINER
        elif self._check_runtime_available(ContainerRuntime.SINGULARITY):
            return ContainerRuntime.SINGULARITY
        elif self._check_runtime_available(ContainerRuntime.PODMAN):
            return ContainerRuntime.PODMAN
            
        raise RuntimeError(
            "No supported container runtime found. "
            "Please install Docker, Apptainer, Singularity, or Podman."
        )
    
    def _is_hpc_environment(self) -> bool:
        """Detect if we're in an HPC environment"""
        # Check for common HPC environment variables
        hpc_indicators = [
            'SLURM_JOB_ID',
            'PBS_JOBID', 
            'LSB_JOBID',
            'SGE_JOB_ID',
            'HOSTNAME'  # Many HPC systems have specific hostname patterns
        ]
        
        for indicator in hpc_indicators:
            if indicator in os.environ:
                return True
        
        # Check hostname patterns
        hostname = os.environ.get('HOSTNAME', '')
        hpc_patterns = ['login', 'compute', 'node', 'hpc', 'cluster']
        if any(pattern in hostname.lower() for pattern in hpc_patterns):
            return True
            
        return False
    
    def _check_runtime_available(self, runtime: ContainerRuntime) -> bool:
        """Check if a specific runtime is available"""
        try:
            if runtime == ContainerRuntime.DOCKER:
                result = subprocess.run(['docker', '--version'], 
                                      capture_output=True, check=True)
            elif runtime == ContainerRuntime.APPTAINER:
                result = subprocess.run(['apptainer', '--version'], 
                                      capture_output=True, check=True)
            elif runtime == ContainerRuntime.SINGULARITY:
                result = subprocess.run(['singularity', '--version'], 
                                      capture_output=True, text=True, check=True)
            elif runtime == ContainerRuntime.PODMAN:
                result = subprocess.run(['podman', '--version'], 
                                      capture_output=True, check=True)
            else:
                return False
                
            return result.returncode == 0
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False
    
    def get_runtime_info(self) -> Dict[str, str]:
        """Get information about the current runtime"""
        try:
            if self.runtime == ContainerRuntime.DOCKER:
                result = subprocess.run(['docker', '--version'], 
                                      capture_output=True, text=True, check=True)
                version = result.stdout.strip()
            elif self.runtime == ContainerRuntime.APPTAINER:
                result = subprocess.run(['apptainer', '--version'], 
                                      capture_output=True, text=True, check=True)
                version = result.stdout.strip()
            elif self.runtime == ContainerRuntime.SINGULARITY:
                result = subprocess.run(['singularity', '--version'], 
                                      capture_output=True, text=True, check=True)
                version = result.stdout.strip()
            elif self.runtime == ContainerRuntime.PODMAN:
                result = subprocess.run(['podman', '--version'], 
                                      capture_output=True, text=True, check=True)
                version = result.stdout.strip()
            else:
                version = "Unknown"
                
            return {
                'runtime': self.runtime.value,
                'version': version,
                'is_hpc': self._is_hpc_environment()
            }
        except subprocess.CalledProcessError:
            return {
                'runtime': self.runtime.value,
                'version': 'Unknown',
                'is_hpc': self._is_hpc_environment()
            }
    
    def pull_image(self, image_name: str) -> bool:
        """Pull a container image"""
        try:
            if self.runtime == ContainerRuntime.DOCKER:
                subprocess.run(['docker', 'pull', image_name], check=True)
            elif self.runtime == ContainerRuntime.APPTAINER:
                subprocess.run(['apptainer', 'pull', f'{image_name}.sif', 
                              f'docker://{image_name}'], check=True)
            elif self.runtime == ContainerRuntime.SINGULARITY:
                subprocess.run(['singularity', 'pull', f'{image_name}.sif', 
                              f'docker://{image_name}'], check=True)
            elif self.runtime == ContainerRuntime.PODMAN:
                subprocess.run(['podman', 'pull', image_name], check=True)
            return True
        except subprocess.CalledProcessError as e:
            print(f"Failed to pull image {image_name}: {e}")
            return False
    
    def run_container(self, image: str, name: str, command: Optional[str] = None,
                     volumes: Optional[Dict[str, str]] = None,
                     ports: Optional[Dict[str, str]] = None,
                     environment: Optional[Dict[str, str]] = None,
                     detach: bool = False) -> bool:
        """Run a container with the specified parameters"""
        try:
            cmd = self._build_run_command(image, name, command, volumes, 
                                        ports, environment, detach)
            subprocess.run(cmd, check=True)
            return True
        except subprocess.CalledProcessError as e:
            print(f"Failed to run container: {e}")
            return False
    
    def _build_run_command(self, image: str, name: str, command: Optional[str] = None,
                          volumes: Optional[Dict[str, str]] = None,
                          ports: Optional[Dict[str, str]] = None,
                          environment: Optional[Dict[str, str]] = None,
                          detach: bool = False) -> List[str]:
        """Build the appropriate run command for the current runtime"""
        if self.runtime == ContainerRuntime.DOCKER:
            return self._build_docker_run_command(image, name, command, volumes, 
                                                ports, environment, detach)
        elif self.runtime == ContainerRuntime.APPTAINER:
            return self._build_apptainer_run_command(image, name, command, volumes, 
                                                   ports, environment, detach)
        elif self.runtime == ContainerRuntime.SINGULARITY:
            return self._build_singularity_run_command(image, name, command, volumes, 
                                                     ports, environment, detach)
        elif self.runtime == ContainerRuntime.PODMAN:
            return self._build_podman_run_command(image, name, command, volumes, 
                                                ports, environment, detach)
        else:
            raise RuntimeError(f"Unsupported runtime: {self.runtime}")
    
    def _build_docker_run_command(self, image: str, name: str, command: Optional[str] = None,
                                 volumes: Optional[Dict[str, str]] = None,
                                 ports: Optional[Dict[str, str]] = None,
                                 environment: Optional[Dict[str, str]] = None,
                                 detach: bool = False) -> List[str]:
        """Build Docker run command"""
        cmd = ['docker', 'run']
        
        if name:
            cmd.extend(['--name', name])
        
        if detach:
            cmd.append('-d')
        
        if volumes:
            for host_path, container_path in volumes.items():
                cmd.extend(['-v', f'{host_path}:{container_path}'])
        
        if ports:
            for host_port, container_port in ports.items():
                cmd.extend(['-p', f'{host_port}:{container_port}'])
        
        if environment:
            for key, value in environment.items():
                cmd.extend(['-e', f'{key}={value}'])
        
        cmd.append(image)
        
        if command:
            cmd.extend(['sh', '-c', command])
        
        return cmd
    
    def _build_apptainer_run_command(self, image: str, name: str, command: Optional[str] = None,
                                   volumes: Optional[Dict[str, str]] = None,
                                   ports: Optional[Dict[str, str]] = None,
                                   environment: Optional[Dict[str, str]] = None,
                                   detach: bool = False) -> List[str]:
        """Build Apptainer run command"""
        # Apptainer uses .sif files, so we need to check if the image exists
        image_path = f"{image}.sif"
        if not Path(image_path).exists():
            # Pull the image first
            self.pull_image(image)
        
        cmd = ['apptainer', 'run']
        
        if volumes:
            for host_path, container_path in volumes.items():
                cmd.extend(['--bind', f'{host_path}:{container_path}'])
        
        if environment:
            for key, value in environment.items():
                cmd.extend(['--env', f'{key}={value}'])
        
        cmd.append(image_path)
        
        if command:
            cmd.extend(['sh', '-c', command])
        
        return cmd
    
    def _build_singularity_run_command(self, image: str, name: str, command: Optional[str] = None,
                                     volumes: Optional[Dict[str, str]] = None,
                                     ports: Optional[Dict[str, str]] = None,
                                     environment: Optional[Dict[str, str]] = None,
                                     detach: bool = False) -> List[str]:
        """Build Singularity run command (similar to Apptainer)"""
        image_path = f"{image}.sif"
        if not Path(image_path).exists():
            self.pull_image(image)
        
        cmd = ['singularity', 'run']
        
        if volumes:
            for host_path, container_path in volumes.items():
                cmd.extend(['--bind', f'{host_path}:{container_path}'])
        
        if environment:
            for key, value in environment.items():
                cmd.extend(['--env', f'{key}={value}'])
        
        cmd.append(image_path)
        
        if command:
            cmd.extend(['sh', '-c', command])
        
        return cmd
    
    def _build_podman_run_command(self, image: str, name: str, command: Optional[str] = None,
                                volumes: Optional[Dict[str, str]] = None,
                                ports: Optional[Dict[str, str]] = None,
                                environment: Optional[Dict[str, str]] = None,
                                detach: bool = False) -> List[str]:
        """Build Podman run command (similar to Docker)"""
        cmd = ['podman', 'run']
        
        if name:
            cmd.extend(['--name', name])
        
        if detach:
            cmd.append('-d')
        
        if volumes:
            for host_path, container_path in volumes.items():
                cmd.extend(['-v', f'{host_path}:{container_path}'])
        
        if ports:
            for host_port, container_port in ports.items():
                cmd.extend(['-p', f'{host_port}:{container_port}'])
        
        if environment:
            for key, value in environment.items():
                cmd.extend(['-e', f'{key}={value}'])
        
        cmd.append(image)
        
        if command:
            cmd.extend(['sh', '-c', command])
        
        return cmd
    
    def stop_container(self, name: str) -> bool:
        """Stop a running container"""
        try:
            if self.runtime == ContainerRuntime.DOCKER:
                subprocess.run(['docker', 'stop', name], check=True)
            elif self.runtime == ContainerRuntime.PODMAN:
                subprocess.run(['podman', 'stop', name], check=True)
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
                cmd = ['docker', 'ps']
                if all_containers:
                    cmd.append('-a')
                result = subprocess.run(cmd, capture_output=True, text=True, check=True)
                return self._parse_docker_ps_output(result.stdout)
            elif self.runtime == ContainerRuntime.PODMAN:
                cmd = ['podman', 'ps']
                if all_containers:
                    cmd.append('-a')
                result = subprocess.run(cmd, capture_output=True, text=True, check=True)
                return self._parse_docker_ps_output(result.stdout)  # Same format as Docker
            else:
                # Apptainer/Singularity doesn't have persistent containers in the same way
                return []
        except subprocess.CalledProcessError:
            return []
    
    def _parse_docker_ps_output(self, output: str) -> List[Dict]:
        """Parse Docker/Podman ps output into structured data"""
        lines = output.strip().split('\n')
        if len(lines) < 2:
            return []
        
        headers = lines[0].split()
        containers = []
        
        for line in lines[1:]:
            if not line.strip():
                continue
            parts = line.split()
            if len(parts) >= len(headers):
                container = {}
                for i, header in enumerate(headers):
                    if i < len(parts):
                        container[header.lower()] = parts[i]
                containers.append(container)
        
        return containers
    
    def build_image(self, dockerfile_path: Path, tag: str, context_path: Path) -> bool:
        """Build a container image"""
        try:
            if self.runtime == ContainerRuntime.DOCKER:
                subprocess.run(['docker', 'build', '-t', tag, '-f', str(dockerfile_path), 
                              str(context_path)], check=True)
            elif self.runtime == ContainerRuntime.PODMAN:
                subprocess.run(['podman', 'build', '-t', tag, '-f', str(dockerfile_path), 
                              str(context_path)], check=True)
            elif self.runtime in [ContainerRuntime.APPTAINER, ContainerRuntime.SINGULARITY]:
                # Convert Dockerfile to Singularity definition file
                def_file = self._convert_dockerfile_to_singularity(dockerfile_path, context_path)
                build_cmd = 'apptainer' if self.runtime == ContainerRuntime.APPTAINER else 'singularity'
                subprocess.run([build_cmd, 'build', f'{tag}.sif', str(def_file)], check=True)
            return True
        except subprocess.CalledProcessError as e:
            print(f"Failed to build image: {e}")
            return False
    
    def _convert_dockerfile_to_singularity(self, dockerfile_path: Path, context_path: Path) -> Path:
        """Convert Dockerfile to Singularity definition file"""
        # This is a simplified conversion - in practice, you'd want a more robust converter
        def_file = context_path / "Singularity.def"
        
        with open(dockerfile_path, 'r') as f:
            dockerfile_content = f.read()
        
        # Basic conversion - this would need to be more sophisticated
        singularity_content = f"""Bootstrap: docker
From: {self._extract_base_image(dockerfile_content)}

%post
{dockerfile_content.replace('FROM', '# FROM').replace('RUN', '').replace('COPY', '# COPY')}

%environment
export PYTHONUNBUFFERED=1
export PYTHONDONTWRITEBYTECODE=1

%runscript
python "$@"
"""
        
        with open(def_file, 'w') as f:
            f.write(singularity_content)
        
        return def_file
    
    def _extract_base_image(self, dockerfile_content: str) -> str:
        """Extract base image from Dockerfile content"""
        for line in dockerfile_content.split('\n'):
            if line.strip().startswith('FROM'):
                return line.strip().split()[1]
        return "ubuntu:20.04"  # Default fallback 