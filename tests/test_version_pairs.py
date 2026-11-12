"""The published image tags must match the build script and the app."""

import re
from pathlib import Path

import pytest

from venvoy.core import VenvoyEnvironment

ROOT = Path(__file__).resolve().parents[1]
BUILD_SCRIPT = ROOT / "scripts" / "build-python-r.sh"
DOCKERFILE = ROOT / "docker" / "Dockerfile.combined"


def published_pairs():
    text = BUILD_SCRIPT.read_text(encoding="utf-8")
    block = re.search(r"VERSION_PAIRS=\((.*?)\)", text, re.S)
    assert block, "VERSION_PAIRS block missing from build-python-r.sh"
    return re.findall(r'"(\d+\.\d+):(\d+\.\d+)"', block.group(1))


def test_app_tags_match_build_script():
    pairs = published_pairs()
    assert pairs == [
        ("3.13", "4.5"),
        ("3.12", "4.4"),
        ("3.11", "4.3"),
        ("3.11", "4.2"),
        ("3.10", "4.2"),
    ]
    for python_version, r_version in pairs:
        tag = VenvoyEnvironment._get_combined_image_tag(python_version, r_version)
        assert tag == f"python{python_version}-r{r_version}"


def test_unknown_python_is_rejected():
    with pytest.raises(ValueError, match="Invalid Python/R version combination"):
        VenvoyEnvironment._get_combined_image_tag("3.9", "4.2")


def test_r_version_arg_survives_from():
    """ENV R_VERSION can only see an ARG declared after FROM."""
    text = DOCKERFILE.read_text(encoding="utf-8")
    from_at = text.index("\nFROM ")
    env_at = text.index("ENV R_VERSION=")
    assert "ARG R_VERSION" in text[from_at:env_at]
