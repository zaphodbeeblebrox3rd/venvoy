"""
Tests for platform detection
"""

from venvoy.platform_detector import PlatformDetector


class TestPlatformDetector:
    """Test platform detection functionality"""

    def test_initialization(self):
        """Test PlatformDetector initialization"""
        detector = PlatformDetector()
        assert detector.system is not None
        assert detector.machine is not None
        assert detector.architecture is not None

    def test_detect_returns_dict(self):
        """Test that detect() returns a dictionary with expected keys"""
        detector = PlatformDetector()
        info = detector.detect()

        expected_keys = [
            "system",
            "machine",
            "architecture",
            "platform",
            "python_version",
            "python_executable",
            "home_directory",
            "docker_supported",
            "vscode_available",
        ]

        for key in expected_keys:
            assert key in info

    def test_get_base_image(self):
        """Test base image selection"""
        detector = PlatformDetector()

        for version in ["3.9", "3.10", "3.11", "3.12", "3.13"]:
            image = detector.get_base_image(version)
            assert image == f"python:{version}-slim"

    def test_get_docker_platform(self):
        """Test Docker platform string generation"""
        detector = PlatformDetector()
        platform = detector.get_docker_platform()
        assert platform.startswith("linux/")

    def test_supports_buildx(self):
        """Test BuildX support detection"""
        detector = PlatformDetector()
        assert detector.supports_buildx() is True
