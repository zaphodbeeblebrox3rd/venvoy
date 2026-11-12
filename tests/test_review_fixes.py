"""Tests for the runtime order, snapshot version, and retired export formats."""

from pathlib import Path

from click.testing import CliRunner

from venvoy import __version__
from venvoy.cli import main
from venvoy.container_manager import ContainerRuntime, preferred_runtimes
from venvoy.core import _package_version


def test_hpc_prefers_apptainer_and_laptops_prefer_docker():
    hpc = preferred_runtimes(True)
    laptop = preferred_runtimes(False)

    assert hpc[0] == ContainerRuntime.APPTAINER
    assert hpc[1] == ContainerRuntime.SINGULARITY
    assert laptop[0] == ContainerRuntime.DOCKER
    assert laptop[1] == ContainerRuntime.PODMAN


def test_snapshot_version_matches_package():
    assert _package_version() == __version__


def test_retired_export_formats_do_not_run():
    runner = CliRunner()
    result = runner.invoke(main, ["export", "--format", "wheelhouse", "--name", "unused"])
    assert result.exit_code == 0
    assert "retired" in result.output
    assert "yaml" in result.output


def test_retired_import_formats_do_not_run(tmp_path, monkeypatch):
    archive = tmp_path / "env-archive.tar.gz"
    archive.write_bytes(b"not-an-archive")
    monkeypatch.chdir(tmp_path)

    runner = CliRunner()
    result = runner.invoke(main, ["import", str(archive), "--format", "archive"])
    assert result.exit_code == 0
    assert "retired" in result.output


def test_base_image_does_not_install_miniconda():
    dockerfile = (
        Path(__file__).resolve().parents[1] / "docker" / "Dockerfile.base"
    ).read_text(encoding="utf-8")
    assert "ARG INSTALL_MINICONDA=0" in dockerfile
    assert "Miniconda3-latest" not in dockerfile
    assert "/opt/conda" not in dockerfile
    assert "uv pip install --system" in dockerfile
