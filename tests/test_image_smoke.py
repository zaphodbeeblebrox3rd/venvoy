"""Smoke-check a published image. Off unless VENVOY_TEST_IMAGES=1.

Rollback: leave the variable unset. pytest then skips this file and does not
pull or start any image.

    VENVOY_TEST_IMAGES=1 pytest tests/test_image_smoke.py

Optional VENVOY_TEST_IMAGE_TAG limits the run to one tag, for example
python3.13-r4.5, so a check does not pull every pair.
"""

import os
import shutil
import subprocess

import pytest

from tests.test_version_pairs import published_pairs

pytestmark = pytest.mark.image

IMAGE = "docker.io/zaphodbeeblebrox3rd/venvoy"

if os.environ.get("VENVOY_TEST_IMAGES") != "1":
    pytest.skip(
        "set VENVOY_TEST_IMAGES=1 to start published images",
        allow_module_level=True,
    )

if shutil.which("docker") is None:
    pytest.skip("docker is not on PATH", allow_module_level=True)


def _tags():
    only = os.environ.get("VENVOY_TEST_IMAGE_TAG")
    tags = [f"python{py}-r{r_version}" for py, r_version in published_pairs()]
    if only:
        assert only in tags, f"{only} is not one of {tags}"
        return [only]
    return tags


def _run(tag, *args):
    completed = subprocess.run(
        ["docker", "run", "--rm", "--platform", "linux/amd64", f"{IMAGE}:{tag}", *args],
        capture_output=True,
        text=True,
        timeout=180,
        check=False,
    )
    output = (completed.stdout + completed.stderr).strip()
    assert completed.returncode == 0, output
    return output


@pytest.mark.parametrize("tag", _tags())
def test_python_starts(tag):
    python_version = tag.split("-r", 1)[0].replace("python", "")
    assert python_version in _run(tag, "python", "--version")


@pytest.mark.parametrize("tag", _tags())
def test_r_starts(tag):
    assert "R version" in _run(tag, "R", "--version")


@pytest.mark.parametrize("tag", _tags())
def test_uv_starts(tag):
    assert _run(tag, "uv", "--version")
