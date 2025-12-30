"""
Basic tests that don't require external dependencies
"""

import pytest


def test_basic_import():
    """Test that we can import basic modules"""
    try:
        import click  # noqa: F401
        import rich  # noqa: F401
        import yaml  # noqa: F401

        assert True
    except ImportError as e:
        pytest.fail(f"Failed to import required module: {e}")


def test_venvoy_import():
    """Test that we can import venvoy modules"""
    try:
        from venvoy.platform_detector import PlatformDetector

        detector = PlatformDetector()
        assert detector is not None
    except ImportError as e:
        pytest.fail(f"Failed to import venvoy module: {e}")


def test_platform_detector_basic():
    """Test basic platform detector functionality without docker"""
    from venvoy.platform_detector import PlatformDetector

    detector = PlatformDetector()

    # Test basic properties
    assert hasattr(detector, "system")
    assert hasattr(detector, "machine")
    assert hasattr(detector, "architecture")

    # Test detect method returns dict
    info = detector.detect()
    assert isinstance(info, dict)
    assert "system" in info
    assert "architecture" in info
