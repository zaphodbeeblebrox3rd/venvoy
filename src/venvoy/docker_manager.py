"""
Docker management utilities for venvoy
"""

import subprocess
import sys
import shutil
from pathlib import Path
from typing import Dict, List, Optional
import docker
from docker.errors import DockerException
import requests

from .platform_detector import PlatformDetector


class DockerManager:
    """Manages Docker installation and operations"""
    
    def __init__(self):
        self.platform = PlatformDetector()
        self.client = None
        self._init_client()
    
    def _init_client(self):
        """Initialize Docker client"""
        try:
            self.client = docker.from_env()
            # Test connection
            self.client.ping()
        except DockerException:
            self.client = None
    
    def is_docker_installed(self) -> bool:
        """Check if Docker is installed and running"""
        return self.client is not None
    
    def ensure_docker_installed(self):
        """Ensure Docker is installed, install if necessary"""
        if self.is_docker_installed():
            return
        
        print("Docker not found. Installing Docker...")
        self._install_docker()
        
        # Reinitialize client after installation
        self._init_client()
        
        if not self.is_docker_installed():
            raise RuntimeError("Failed to install or start Docker")
    
    def _install_docker(self):
        """Install Docker based on the platform"""
        system = self.platform.system
        
        if system == 'windows':
            self._install_docker_windows()
        elif system == 'darwin':
            self._install_docker_macos()
        elif system == 'linux':
            self._install_docker_linux()
        else:
            raise RuntimeError(f"Unsupported platform: {system}")
    
    def _install_docker_windows(self):
        """Install Docker Desktop on Windows"""
        print("Please install Docker Desktop from https://www.docker.com/products/docker-desktop")
        print("After installation, restart your system and run venvoy again.")
        sys.exit(1)
    
    def _install_docker_macos(self):
        """Install Docker Desktop on macOS"""
        # Try to install via Homebrew first
        if shutil.which('brew'):
            try:
                subprocess.run(['brew', 'install', '--cask', 'docker'], check=True)
                print("Docker Desktop installed via Homebrew")
                print("Please start Docker Desktop and run venvoy again.")
                return
            except subprocess.CalledProcessError:
                pass
        
        print("Please install Docker Desktop from https://www.docker.com/products/docker-desktop")
        print("After installation, start Docker Desktop and run venvoy again.")
        sys.exit(1)
    
    def _install_docker_linux(self):
        """Install Docker on Linux"""
        try:
            # Install Docker using the official script
            subprocess.run([
                'curl', '-fsSL', 'https://get.docker.com', '-o', 'get-docker.sh'
            ], check=True)
            subprocess.run(['sh', 'get-docker.sh'], check=True)
            
            # Add user to docker group
            subprocess.run(['sudo', 'usermod', '-aG', 'docker', '$USER'], check=True)
            
            # Start Docker service
            subprocess.run(['sudo', 'systemctl', 'start', 'docker'], check=True)
            subprocess.run(['sudo', 'systemctl', 'enable', 'docker'], check=True)
            
            print("Docker installed successfully!")
            print("Please log out and log back in for group changes to take effect.")
            
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Failed to install Docker: {e}")
    
    def ensure_editor_installed(self) -> tuple[str, bool]:
        """Ensure an AI-powered editor is installed, returns (editor_type, available)"""
        vscode_available = self.platform._check_vscode_available()
        cursor_available = self.platform._check_cursor_available()
        
        if cursor_available and vscode_available:
            return self._prompt_editor_choice()
        elif cursor_available:
            return ("cursor", True)
        elif vscode_available:
            return ("vscode", True)
        else:
            return self._prompt_editor_installation()
    
    def _prompt_editor_choice(self) -> tuple[str, bool]:
        """Prompt user to choose between available editors"""
        print("\n🎉 Great! You have both AI-powered editors available:")
        print("1. 🧠 Cursor - The AI-first code editor")
        print("2. 🔧 VSCode - Popular editor with AI extensions")
        
        while True:
            choice = input("\nWhich editor would you prefer? (1 for Cursor, 2 for VSCode): ").strip()
            if choice == '1':
                print("🧠 Excellent choice! Cursor provides cutting-edge AI assistance.")
                return ("cursor", True)
            elif choice == '2':
                print("🔧 Great! VSCode with AI extensions is very powerful.")
                return ("vscode", True)
            else:
                print("Please enter '1' for Cursor or '2' for VSCode.")
    
    def _prompt_editor_installation(self) -> tuple[str, bool]:
        """Prompt user about editor installation"""
        print("\n🤖 No AI-powered editors found on your system.")
        print("For the best AI-enhanced development experience, we recommend:")
        print("1. 🧠 Cursor - The AI-first code editor (Recommended)")
        print("2. 🔧 VSCode - With AI extensions")
        print("3. 🐚 Skip - Use interactive shell instead")
        
        while True:
            choice = input("\nWhat would you like to install? (1/2/3): ").strip()
            if choice == '1':
                success = self._install_cursor()
                if success and self.platform._check_cursor_available():
                    print("✅ Cursor installed successfully!")
                    return ("cursor", True)
                else:
                    print("⚠️  Cursor installation may require manual completion.")
                    print("💡 Don't worry - venvoy will work with an interactive shell instead.")
                    return ("none", False)
            elif choice == '2':
                success = self._install_vscode()
                if success and self.platform._check_vscode_available():
                    print("✅ VSCode installed successfully!")
                    return ("vscode", True)
                else:
                    print("⚠️  VSCode installation may require manual completion.")
                    print("💡 Don't worry - venvoy will work with an interactive shell instead.")
                    return ("none", False)
            elif choice == '3':
                print("📝 No problem! Venvoy will use an enhanced interactive shell with AI-ready environment.")
                return ("none", False)
            else:
                print("Please enter '1' for Cursor, '2' for VSCode, or '3' to skip.")
    
    def _install_cursor(self) -> bool:
        """Install Cursor based on platform"""
        system = self.platform.system
        
        try:
            if system == 'windows':
                print("🔄 Downloading Cursor for Windows...")
                # Use winget if available, otherwise provide download link
                if shutil.which('winget'):
                    try:
                        subprocess.run(['winget', 'install', 'Cursor.Cursor'], check=True)
                        return True
                    except subprocess.CalledProcessError:
                        pass
                
                print("Please download and install Cursor from:")
                print("https://cursor.sh/")
                input("Press Enter after installation is complete...")
                return True
                    
            elif system == 'darwin':
                if shutil.which('brew'):
                    print("🔄 Installing Cursor via Homebrew...")
                    try:
                        subprocess.run(['brew', 'install', '--cask', 'cursor'], check=True)
                        return True
                    except subprocess.CalledProcessError:
                        pass
                
                print("Please download and install Cursor from:")
                print("https://cursor.sh/")
                input("Press Enter after installation is complete...")
                return True
                    
            elif system == 'linux':
                print("🔄 Installing Cursor for Linux...")
                print("Please download and install Cursor from:")
                print("https://cursor.sh/")
                input("Press Enter after installation is complete...")
                return True
                    
        except Exception as e:
            print(f"⚠️  Automatic installation failed: {e}")
            print("Please download and install Cursor from: https://cursor.sh/")
            return False
        
        return False
    
    def _install_vscode(self) -> bool:
        """Install VSCode based on platform"""
        system = self.platform.system
        
        try:
            if system == 'windows':
                print("🔄 Downloading VSCode for Windows...")
                # Use winget if available, otherwise provide download link
                if shutil.which('winget'):
                    try:
                        subprocess.run(['winget', 'install', 'Microsoft.VisualStudioCode'], check=True)
                        return True
                    except subprocess.CalledProcessError:
                        pass
                
                print("Please download and install VSCode from:")
                print("https://code.visualstudio.com/download")
                input("Press Enter after installation is complete...")
                return True
                    
            elif system == 'darwin':
                if shutil.which('brew'):
                    print("🔄 Installing VSCode via Homebrew...")
                    try:
                        subprocess.run(['brew', 'install', '--cask', 'visual-studio-code'], check=True)
                        return True
                    except subprocess.CalledProcessError:
                        pass
                
                print("Please download and install VSCode from:")
                print("https://code.visualstudio.com/download")
                input("Press Enter after installation is complete...")
                return True
                    
            elif system == 'linux':
                # Try different package managers
                if shutil.which('snap'):
                    print("🔄 Installing VSCode via snap...")
                    try:
                        subprocess.run(['sudo', 'snap', 'install', 'code', '--classic'], check=True)
                        return True
                    except subprocess.CalledProcessError:
                        pass
                elif shutil.which('apt'):
                    print("🔄 Installing VSCode via apt...")
                    try:
                        # Add Microsoft GPG key and repository
                        subprocess.run(['wget', '-qO-', 'https://packages.microsoft.com/keys/microsoft.asc'], 
                                     stdout=subprocess.PIPE, check=True)
                        subprocess.run(['sudo', 'apt', 'update'], check=True)
                        subprocess.run(['sudo', 'apt', 'install', 'code'], check=True)
                        return True
                    except subprocess.CalledProcessError:
                        pass
                
                print("Please install VSCode using your package manager or from:")
                print("https://code.visualstudio.com/download")
                input("Press Enter after installation is complete...")
                return True
                    
        except Exception as e:
            print(f"⚠️  Automatic installation failed: {e}")
            self._suggest_vscode_installation()
            return False
        
        return False
    
    def _suggest_vscode_installation(self):
        """Suggest VSCode installation based on platform"""
        system = self.platform.system
        
        if system == 'windows':
            print("Install VSCode from: https://code.visualstudio.com/download")
        elif system == 'darwin':
            if shutil.which('brew'):
                print("Run: brew install --cask visual-studio-code")
            else:
                print("Install VSCode from: https://code.visualstudio.com/download")
        elif system == 'linux':
            print("Install VSCode using your package manager or from:")
            print("https://code.visualstudio.com/download")
    
    def setup_buildx(self):
        """Setup Docker BuildX for multi-architecture builds"""
        if not self.client:
            raise RuntimeError("Docker client not available")
        
        try:
            # Create a new builder instance
            subprocess.run([
                'docker', 'buildx', 'create', 
                '--name', 'venvoy-builder',
                '--use'
            ], check=True, capture_output=True)
        except subprocess.CalledProcessError:
            # Builder might already exist, try to use it
            try:
                subprocess.run([
                    'docker', 'buildx', 'use', 'venvoy-builder'
                ], check=True, capture_output=True)
            except subprocess.CalledProcessError:
                # Fall back to default builder
                pass
        
        # Bootstrap the builder
        try:
            subprocess.run([
                'docker', 'buildx', 'inspect', '--bootstrap'
            ], check=True, capture_output=True)
        except subprocess.CalledProcessError as e:
            print(f"Warning: Failed to bootstrap buildx: {e}")
    
    def build_multiarch_image(
        self, 
        dockerfile_path: Path, 
        tag: str, 
        context_path: Path,
        platforms: List[str] = None
    ) -> str:
        """Build multi-architecture image using BuildX"""
        if platforms is None:
            platforms = ['linux/amd64', 'linux/arm64']
        
        platform_str = ','.join(platforms)
        
        cmd = [
            'docker', 'buildx', 'build',
            '--platform', platform_str,
            '--tag', tag,
            '--file', str(dockerfile_path),
            str(context_path)
        ]
        
        try:
            subprocess.run(cmd, check=True)
            return tag
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Failed to build multi-arch image: {e}")
    
    def push_image(self, tag: str):
        """Push image to registry"""
        try:
            subprocess.run(['docker', 'buildx', 'build', '--push', '--tag', tag], check=True)
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Failed to push image: {e}")
    
    def run_container(
        self, 
        image: str, 
        name: str,
        command: Optional[str] = None,
        volumes: Optional[Dict[str, Dict]] = None,
        ports: Optional[Dict] = None,
        environment: Optional[Dict] = None,
        detach: bool = False
    ):
        """Run a container with specified configuration"""
        if not self.client:
            raise RuntimeError("Docker client not available")
        
        try:
            container = self.client.containers.run(
                image=image,
                name=name,
                command=command,
                volumes=volumes,
                ports=ports,
                environment=environment,
                detach=detach,
                stdin_open=True,
                tty=True,
                remove=True
            )
            return container
        except DockerException as e:
            raise RuntimeError(f"Failed to run container: {e}")
    
    def stop_container(self, name: str):
        """Stop a running container"""
        if not self.client:
            return
        
        try:
            container = self.client.containers.get(name)
            container.stop()
        except DockerException:
            pass  # Container might not exist or already stopped
    
    def list_containers(self, all_containers: bool = False) -> List[Dict]:
        """List containers"""
        if not self.client:
            return []
        
        try:
            containers = self.client.containers.list(all=all_containers)
            return [
                {
                    'name': container.name,
                    'image': container.image.tags[0] if container.image.tags else 'unknown',
                    'status': container.status,
                    'created': container.attrs['Created']
                }
                for container in containers
            ]
        except DockerException:
            return [] 