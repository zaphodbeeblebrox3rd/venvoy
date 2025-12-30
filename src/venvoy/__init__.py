"""
venvoy - A multi-OS, multi-architecture, immutable, portable, and shareable
python environment
"""

__version__ = "0.1.0"
__author__ = "Your Name"
__email__ = "your.email@example.com"

from .container_manager import ContainerManager, ContainerRuntime
from .core import VenvoyEnvironment
from .platform_detector import PlatformDetector

__all__ = [
    "VenvoyEnvironment",
    "ContainerManager",
    "ContainerRuntime",
    "PlatformDetector",
]
