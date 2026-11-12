"""
Platform detection utilities for venvoy
"""

import os
import platform
import sys
from pathlib import Path
from typing import Any, Dict

# Rollback: set this to a Windows profile name if $USER does not match the
# directory under /mnt/c/Users. Empty uses $USER, then $USERNAME.
WSL_WINDOWS_USER = ""


class PlatformDetector:
    """Detects platform information and capabilities"""

    def __init__(self):
        self.system = platform.system().lower()
        self.machine = platform.machine().lower()
        self.architecture = self._normalize_architecture()
        self.is_wsl = self._detect_wsl()

    def _wsl_windows_user(self) -> str:
        """Windows profile name used to build /mnt/c/Users paths from WSL."""
        if WSL_WINDOWS_USER:
            return WSL_WINDOWS_USER
        return os.environ.get("USER") or os.environ.get("USERNAME") or "user"

    def _wsl_editor_candidates(self, user_relative: str, program_files_relative: str) -> list:
        """Windows editor binaries, addressed from a WSL mount."""
        user = self._wsl_windows_user()
        return [
            Path(f"/mnt/c/Users/{user}") / user_relative,
            Path("/mnt/c/Program Files") / program_files_relative,
            Path("/mnt/c/Program Files (x86)") / program_files_relative,
        ]

    def _detect_wsl(self) -> bool:
        """Detect if running in WSL (Windows Subsystem for Linux)"""
        # Check for WSL-specific indicators
        if self.system == "linux":
            # Check for WSL-specific files
            wsl_indicators = ["/proc/version", "/proc/sys/kernel/osrelease"]
            for indicator in wsl_indicators:
                if os.path.exists(indicator):
                    try:
                        with open(indicator, "r") as f:
                            content = f.read().lower()
                            if "microsoft" in content or "wsl" in content:
                                return True
                    except Exception:
                        pass
        return False

    def _normalize_architecture(self) -> str:
        """Normalize architecture names to Docker platform format"""
        arch_map = {
            "x86_64": "amd64",
            "amd64": "amd64",
            "i386": "386",
            "i686": "386",
            "aarch64": "arm64",
            "arm64": "arm64",
        }
        return arch_map.get(self.machine, self.machine)

    def detect(self) -> Dict[str, Any]:
        """Detect comprehensive platform information"""
        return {
            "system": self.system,
            "machine": self.machine,
            "architecture": self.architecture,
            "platform": f"{self.system}/{self.architecture}",
            "python_version": f"{sys.version_info.major}.{sys.version_info.minor}",
            "python_executable": sys.executable,
            "home_directory": str(Path.home()),
            "docker_supported": self._check_docker_support(),
            "vscode_available": self._check_vscode_available(),
            "devin_available": self._check_devin_available(),
            "is_wsl": self.is_wsl,
        }

    def _check_docker_support(self) -> bool:
        """Check if Docker is supported on this platform"""
        # Docker is supported on all major platforms
        return self.system in ["linux", "darwin", "windows"]

    def _check_vscode_available(self) -> bool:
        """Check if VSCode is available on the system"""
        vscode_paths = self._get_vscode_paths()
        return any(Path(path).exists() for path in vscode_paths)

    def _check_devin_available(self) -> bool:
        """Check if Devin Desktop is available on the system"""
        devin_paths = self._get_devin_paths()
        return any(Path(path).exists() for path in devin_paths)

    def _get_vscode_paths(self) -> list:
        """Get potential VSCode installation paths for the current platform"""
        if self.system == "windows":
            return [
                Path.home() / "AppData/Local/Programs/Microsoft VS Code/Code.exe",
                Path("C:/Program Files/Microsoft VS Code/Code.exe"),
                Path("C:/Program Files (x86)/Microsoft VS Code/Code.exe"),
            ]
        elif self.system == "darwin":
            return [
                Path(
                    "/Applications/Visual Studio Code.app/Contents/Resources/app/bin/code"
                ),
                Path.home()
                / "Applications/Visual Studio Code.app/Contents/Resources/app/bin/code",
            ]
        elif self.system == "linux":
            paths = [
                Path("/usr/bin/code"),
                Path("/usr/local/bin/code"),
                Path("/snap/bin/code"),
                Path.home() / ".local/bin/code",
            ]

            # If running in WSL, also check for Windows VSCode installations
            if self.is_wsl:
                paths.extend(
                    self._wsl_editor_candidates(
                        "AppData/Local/Programs/Microsoft VS Code/Code.exe",
                        "Microsoft VS Code/Code.exe",
                    )
                )

            return paths
        return []

    def _get_devin_paths(self) -> list:
        """Get potential Devin Desktop installation paths for the current platform"""
        if self.system == "windows":
            return [
                Path.home() / "AppData/Local/Programs/Devin/bin/devin-desktop.cmd",
                Path.home() / "AppData/Local/Programs/Devin/Devin.exe",
                Path("C:/Program Files/Devin/bin/devin-desktop.cmd"),
                Path("C:/Program Files (x86)/Devin/bin/devin-desktop.cmd"),
            ]
        elif self.system == "darwin":
            return [
                Path(
                    "/Applications/Devin.app/Contents/Resources/app/bin/devin-desktop"
                ),
                Path.home()
                / "Applications/Devin.app/Contents/Resources/app/bin/devin-desktop",
            ]
        elif self.system == "linux":
            paths = [
                Path("/usr/bin/devin-desktop"),
                Path("/usr/local/bin/devin-desktop"),
                Path("/snap/bin/devin-desktop"),
                Path.home() / ".local/bin/devin-desktop",
            ]

            # If running in WSL, also check for Windows Devin installations
            if self.is_wsl:
                paths.extend(
                    self._wsl_editor_candidates(
                        "AppData/Local/Programs/Devin/bin/devin-desktop.cmd",
                        "Devin/bin/devin-desktop.cmd",
                    )
                )

            return paths
        return []

    def get_docker_platform(self) -> str:
        """Get Docker platform string for multi-arch builds"""
        return f"linux/{self.architecture}"

    def get_base_image(self, python_version: str) -> str:
        """Get the appropriate base image for the platform"""
        # Use official Python slim images which support multi-arch
        return f"python:{python_version}-slim"

    def get_shell_command(self) -> str:
        """Get the appropriate shell command for the platform"""
        if self.system == "windows":
            return "powershell"
        return "/bin/bash"

    def get_home_mount_path(self) -> str:
        """Get the home directory path for Docker mounting"""
        # Use ~/.venvoy/home subdirectory instead of full home directory
        venvoy_home = Path.home() / ".venvoy" / "home"
        if self.system == "windows":
            # Convert Windows path to Docker-compatible format
            return str(venvoy_home).replace("\\", "/")
        return str(venvoy_home)

    def supports_buildx(self) -> bool:
        """Check if Docker BuildX is supported"""
        # BuildX is supported on Docker 19.03+ on all platforms
        return True
