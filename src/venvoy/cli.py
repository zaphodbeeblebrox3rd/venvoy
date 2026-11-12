"""
Command-line interface for venvoy
"""

from pathlib import Path

import click
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

from .container_manager import ContainerManager, ContainerRuntime
from .core import VenvoyEnvironment
from .platform_detector import PlatformDetector

console = Console()


@click.group()
@click.version_option()
def main():
    """venvoy - A portable Python environment manager

    Core Mission: Scientific Reproducibility for Data Science

    🏢 HPC Compatible: Automatically uses Apptainer/Singularity on clusters
    🔧 Multi-Runtime: Supports Docker, Apptainer, Singularity, and Podman

    Quick Start Examples:
        venvoy init --runtime python --python-version 3.13 --name mynewpy313
        venvoy init --runtime r --r-version 4.4 --name myrstats

    Common Commands:
        venvoy init             # Initialize new environment (Python or R)
        venvoy run              # Launch environment
        venvoy runtime-info     # Show container runtime information
        venvoy export           # Export a YAML snapshot of the environment
        venvoy import           # Import a YAML snapshot
        venvoy history          # View environment history
        venvoy update/upgrade   # Update venvoy to latest version
        venvoy exit/deactivate  # Exit virtual environment (same as 'deactivate')

    Scientific Reproducibility:
        venvoy export --format yaml    # Snapshot the environment as YAML

    HPC Support:
        venvoy runtime-info     # Check what runtime will be used
        venvoy init             # Works on clusters with Apptainer/Singularity
    """
    pass


@main.command()
@click.option(
    "--runtime",
    default="python",
    type=click.Choice(["python", "r"]),
    help="Runtime environment (python or r)",
)
@click.option(
    "--python-version",
    default="3.11",
    type=click.Choice(["3.10", "3.11", "3.12", "3.13"]),
    help="Python version to use (when runtime=python)",
)
@click.option(
    "--r-version",
    default="4.3",
    type=click.Choice(["4.2", "4.3", "4.4", "4.5"]),
    help="R version to use (when runtime=r)",
)
@click.option("--name", default="venvoy-env", help="Name for the environment")
@click.option(
    "--force", is_flag=True, help="Force reinitialize even if environment exists"
)
def init(runtime: str, python_version: str, r_version: str, name: str, force: bool):
    """Initialize a new portable Python or R environment"""
    # Validate Python/R version combination
    try:
        from .core import VenvoyEnvironment
        VenvoyEnvironment._get_combined_image_tag(python_version, r_version)
    except ValueError as e:
        console.print(
            Panel.fit("❌ Invalid Version Combination", style="bold red")
        )
        console.print(str(e))
        return
    
    if runtime == "python":
        console.print(
            Panel.fit("🚀 Initializing venvoy Python environment", style="bold blue")
        )
    elif runtime == "r":
        console.print(
            Panel.fit("📊 Initializing venvoy R environment", style="bold green")
        )
    else:
        console.print(
            Panel.fit("🚀 Initializing venvoy environment", style="bold blue")
        )

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        # Detect platform and check prerequisites
        task = progress.add_task(
            "Detecting platform and checking prerequisites...", total=None
        )
        detector = PlatformDetector()
        platform_info = detector.detect()
        # Validate platform detection results
        required_keys = ["system", "architecture", "platform", "python_version"]
        for key in required_keys:
            if key not in platform_info:
                raise RuntimeError(f"Platform detection failed: missing key '{key}'")
            if not platform_info[key]:
                raise RuntimeError(
                    f"Platform detection failed: empty value for '{key}'"
                )

        progress.update(task, description="Checking container runtime...")
        container_manager = ContainerManager()
        runtime_info = container_manager.get_runtime_info()
        # Validate runtime info
        required_runtime_keys = ["runtime", "version", "is_hpc"]
        for key in required_runtime_keys:
            if key not in runtime_info:
                raise RuntimeError(f"Runtime detection failed: missing key '{key}'")
        if not runtime_info["runtime"]:
            raise RuntimeError("Runtime detection failed: no runtime detected")

        progress.update(task, description="Detecting available editors...")
        # Just detect editors, don't prompt for installation
        vscode_available = container_manager.platform._check_vscode_available()
        devin_available = container_manager.platform._check_devin_available()

        if devin_available:
            editor_type, editor_available = "devin", True
        elif vscode_available:
            editor_type, editor_available = "vscode", True
        else:
            editor_type, editor_available = "none", False

        progress.update(task, description="Creating environment...")
        env = VenvoyEnvironment(
            name=name,
            python_version=python_version,
            runtime=runtime,
            r_version=r_version,
        )

        try:
            env.initialize(
                force=force, editor_type=editor_type, editor_available=editor_available
            )
        except RuntimeError as e:
            if "already exists" in str(e):
                progress.remove_task(task)
                console.print(f"\n❌ {e}")
                console.print(
                    f"\n💡 To reinitialize the existing environment '{name}', use:"
                )
                console.print(f"   venvoy init --name {name} --force")
                console.print("\n🔍 To see all your environments:")
                console.print("   venvoy list")
                console.print("\n🚀 To start working with the existing environment:")
                console.print(f"   venvoy run --name {name}")
                return
            else:
                # Re-raise other RuntimeErrors
                raise

        progress.update(task, description="Finalizing setup...")
        # Environment is ready to use

        progress.remove_task(task)

    console.print(f"✅ Environment '{name}' initialized successfully!")
    if runtime == "python":
        console.print(f"🐍 Python {python_version} runtime ready")
    elif runtime == "r":
        console.print(f"📊 R {r_version} runtime ready")

    if editor_available:
        if editor_type == "devin":
            console.print(
                f"💡 Use 'venvoy run --name {name}' to start working in your environment"
            )
            console.print(
                "🧠 Devin will automatically connect to your container with AI assistance"
            )
        elif editor_type == "vscode":
            console.print(
                f"💡 Use 'venvoy run --name {name}' to start working in your environment"
            )
            console.print("🔧 VSCode will automatically connect to your container")
    else:
        console.print(
            f"💡 Use 'venvoy run --name {name}' to launch an interactive shell in your environment"
        )
        console.print(
            "🐚 Your environment will start with an enhanced AI-ready bash shell"
        )


@main.command()
@click.option("--name", default="venvoy-env", help="Name of the environment to freeze")
@click.option("--include-dev", is_flag=True, help="Include development dependencies")
def freeze(name: str, include_dev: bool):
    """Freeze the current environment state"""
    console.print(Panel.fit("❄️  Freezing environment state", style="bold cyan"))

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Freezing environment...", total=None)

        env = VenvoyEnvironment(name=name)

        progress.update(task, description="Downloading wheels...")
        env.download_wheels(include_dev=include_dev)

        progress.update(task, description="Creating snapshot...")
        env.create_snapshot()

        progress.remove_task(task)

    console.print("✅ Environment frozen successfully!")
    console.print("📦 All packages downloaded to vendor/ directory")


@main.command()
@click.argument("name_arg", required=False)
@click.option("--name", default=None, help="Name of the environment to run")
@click.option("--command", help="Command to run (default: interactive shell)")
@click.option(
    "--mount", multiple=True, help="Additional volume mounts (host:container)"
)
def run(name_arg: str, name: str, command: str, mount: tuple):
    """Launch the portable Python environment

    You can specify the environment name as a positional argument:
    venvoy run my-env

    Or use the --name option:
    venvoy run --name my-env

    If both are provided, --name takes precedence.
    """
    console.print(
        Panel.fit("🏃 Launching environment - RUN COMMAND", style="bold magenta")
    )

    # Use the bootstrap script approach for consistency
    import subprocess
    import sys
    from pathlib import Path

    # Get the bootstrap script path
    bootstrap_script = Path.home() / ".venvoy" / "bin" / "venvoy"

    if not bootstrap_script.exists():
        console.print(
            "❌ venvoy bootstrap script not found. Please run 'venvoy update' first.",
            style="red",
        )
        sys.exit(1)

    # Determine the environment name: --name takes precedence, then name_arg, then default
    env_name = name if name is not None else (name_arg if name_arg else "venvoy-env")

    # Build the command to pass to the bootstrap script
    cmd_args = ["run"]
    if env_name != "venvoy-env":  # Only add --name if it's not the default
        cmd_args.extend(["--name", env_name])
    if command:
        cmd_args.extend(["--command", command])
    if mount:
        for m in mount:
            cmd_args.extend(["--mount", m])

    # Execute the bootstrap script with the run command
    try:
        result = subprocess.run([str(bootstrap_script)] + cmd_args, check=True)
        return result.returncode
    except subprocess.CalledProcessError as e:
        console.print(f"❌ Failed to run environment: {e}", style="red")
        sys.exit(e.returncode)
    except FileNotFoundError:
        console.print(
            "❌ venvoy bootstrap script not found. Please run 'venvoy update' first.",
            style="red",
        )
        sys.exit(1)


@main.command()
@click.option("--name", default="venvoy-env", help="Name of the environment to export")
@click.option(
    "--format",
    default="yaml",
    type=click.Choice(["yaml", "dockerfile", "tarball", "archive", "wheelhouse"]),
    help="Export format. yaml is the snapshot. Other choices are retired.",
)
@click.option("--output", help="Output file path")
def export(name: str, format: str, output: str):
    """Export an environment as a YAML snapshot.

    dockerfile, tarball, archive, and wheelhouse are retired. YAML is the snapshot format.
    """
    if format != "yaml":
        console.print(
            f"{format} export is retired. YAML is the environment snapshot format."
        )
        console.print(f"Use: venvoy export --name {name} --format yaml")
        return

    console.print(Panel.fit("Exporting environment", style="bold yellow"))

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Exporting environment...", total=None)
        env = VenvoyEnvironment(name=name)
        progress.update(task, description="Generating environment.yaml...")
        output_path = env.export_yaml(output)
        progress.remove_task(task)

    console.print(f"Environment exported: {output_path}")


def _list_environments():
    """Internal function to list all venvoy environments"""
    console.print(Panel.fit("📋 Venvoy Environments", style="bold blue"))

    env = VenvoyEnvironment()
    environments = env.list_environments()

    if not environments:
        console.print("No environments found.")
        console.print(
            "Here is an example on how to create one: "
            "'venvoy init --python-version 3.13 --name mynewpy313'"
        )
        return

    for env_info in environments:
        if env_info.get("runtime") == "r":
            console.print(
                f"📊 {env_info['name']} (R {env_info.get('r_version', 'unknown')})"
            )
        else:
            console.print(
                f"🐍 {env_info['name']} (Python {env_info.get('python_version', 'unknown')})"
            )
        console.print(f"   Created: {env_info['created']}")
        console.print(f"   Status: {env_info['status']}")


@main.command()
def list():
    """List all venvoy environments"""
    _list_environments()


# Hidden 'env' command group for conda-like compatibility (undocumented)
@main.group(hidden=True)
def env():
    """Hidden command group for conda-like compatibility"""
    pass


@env.command(hidden=True)
def list():  # noqa: F811
    """List all venvoy environments (conda-like alias)"""
    _list_environments()


@main.command()
@click.option(
    "--name", default="venvoy-env", help="Name of the environment to list exports for"
)
def history(name: str):
    """List environment export history"""
    console.print(
        Panel.fit(f"📜 Environment Export History: {name}", style="bold purple")
    )

    env = VenvoyEnvironment(name=name)
    exports = env.list_environment_exports()

    if not exports:
        console.print(f"No export history found for environment '{name}'.")
        console.print(
            "💡 Environment exports are created automatically when packages change."
        )
        return

    console.print(f"Found {len(exports)} environment exports:\n")

    for i, export in enumerate(exports, 1):
        # Status indicator for most recent
        status = "🔥 Latest" if i == 1 else f"#{i:2d}"

        console.print(f"{status} {export['formatted_time']}")
        console.print(
            f"    📦 {export['total_packages']} packages ({export['python_packages']} Python, {export['r_packages']} R)"
        )
        console.print(f"    💾 {export['file'].name}")

        if i < len(exports):  # Don't add separator after last item
            console.print()

    console.print(f"\nUse 'venvoy init --name {name}' to restore from any of these exports")
    console.print(f"Export files stored in: {env.projects_dir}")
    console.print("New exports are created automatically when packages change")


@main.command()
@click.option(
    "--name", default="venvoy-env", help="Name of the environment to configure"
)
def configure(name: str):
    """Configure environment settings"""
    console.print(Panel.fit("⚙️  Configure Environment", style="bold cyan"))

    env = VenvoyEnvironment(name=name)

    if not env.config_file.exists():
        console.print(
            f"❌ Environment '{name}' not found. Use 'venvoy init' to create it."
        )
        return

    # Check current editor configuration
    current_editor_type, current_editor_available = env._get_editor_config()
    detector = PlatformDetector()
    actual_vscode = detector._check_vscode_available()
    actual_devin = detector._check_devin_available()

    console.print(
        f"Current editor: {current_editor_type.title() if current_editor_type != 'none' else 'None'}"
    )
    console.print(
        f"Current status: {'✅ Enabled' if current_editor_available else '❌ Disabled'}"
    )
    console.print(f"VSCode available: {'✅ Yes' if actual_vscode else '❌ No'}")
    console.print(f"Devin available: {'✅ Yes' if actual_devin else '❌ No'}")

    # Check if configuration needs updating
    needs_update = False
    new_config = {}

    if actual_devin and actual_vscode:
        if not current_editor_available or current_editor_type == "none":
            console.print("\n🎉 Both AI editors are available!")
            choice = click.prompt(
                "Which would you prefer? (1=Devin, 2=VSCode, 3=None)",
                type=click.Choice(["1", "2", "3"]),
            )
            if choice == "1":
                new_config = {"editor_type": "devin", "editor_available": True}
                console.print("🧠 Devin integration enabled!")
            elif choice == "2":
                new_config = {"editor_type": "vscode", "editor_available": True}
                console.print("🔧 VSCode integration enabled!")
            else:
                new_config = {"editor_type": "none", "editor_available": False}
                console.print("🐚 Interactive shell mode enabled!")
            needs_update = True
    elif actual_devin and (
        current_editor_type != "devin" or not current_editor_available
    ):
        if click.confirm("Devin is available. Enable Devin integration?"):
            new_config = {"editor_type": "devin", "editor_available": True}
            console.print("🧠 Devin integration enabled!")
            needs_update = True
    elif actual_vscode and (
        current_editor_type != "vscode" or not current_editor_available
    ):
        if click.confirm("VSCode is available. Enable VSCode integration?"):
            new_config = {"editor_type": "vscode", "editor_available": True}
            console.print("🔧 VSCode integration enabled!")
            needs_update = True
    elif not actual_devin and not actual_vscode and current_editor_available:
        console.print(
            "⚠️  No AI editors are available. Switching to interactive shell mode."
        )
        new_config = {"editor_type": "none", "editor_available": False}
        console.print("🐚 Environment will use interactive shell mode.")
        needs_update = True

    if needs_update:
        env._update_config(new_config)
    else:
        console.print("✅ Environment configuration is up to date.")


@main.command()
def package_managers():
    """Show information about available package managers"""
    console.print(Panel.fit("📦 Package Manager Guide", style="bold green"))

    console.print(
        "\n🚀 **venvoy** includes multiple package managers for optimal performance:\n"
    )

    # UV info
    console.print("🦄 **uv** - Ultra-fast Python package installer")
    console.print("   • ⚡ 10-100x faster than pip for pure Python packages")
    console.print("   • 🏗️  Written in Rust for maximum performance")
    console.print("   • 📦 Best for: All Python packages")
    console.print("   • Usage: `uv pip install requests flask fastapi numpy pandas`")
    console.print("   • Note: Uses PyPI registry\n")

    # Pip info
    console.print("🐍 **pip** - Standard Python package installer")
    console.print("   • 📚 Universal compatibility")
    console.print("   • 🔧 Fallback for packages not available via uv")
    console.print("   • 📦 Best for: Legacy packages, special cases")
    console.print("   • Usage: `pip install some-package`\n")

    # R packages info
    console.print("📊 **R packages** - CRAN package management")
    console.print("   • 📦 Install R packages from CRAN")
    console.print("   • Usage: `R -e \"install.packages('tidyverse')\"`")
    console.print("   • Or: `install.packages(c('tidyverse', 'devtools'))`\n")

    console.print("💡 **Recommendations:**")
    console.print(
        "   • For AI/ML packages: `uv pip install tensorflow pytorch scikit-learn`"
    )
    console.print("   • For web development: `uv pip install fastapi uvicorn`")
    console.print(
        "   • For data science: `uv pip install pandas numpy matplotlib jupyter`"
    )
    console.print("   • For quick installs: `uv pip install requests beautifulsoup4`")
    console.print("   • For R packages: `R -e \"install.packages('tidyverse')\"`")


@main.command()
@click.option("--force", is_flag=True, help="Skip confirmation prompts")
@click.option(
    "--keep-projects",
    is_flag=True,
    help="Keep environment exports in ~/.venvoy/projects",
)
@click.option("--keep-images", is_flag=True, help="Keep Docker images")
def uninstall(force: bool, keep_projects: bool, keep_images: bool):
    """Uninstall venvoy and clean up all files"""
    import os
    import platform
    import shutil
    import subprocess
    from pathlib import Path

    console.print(Panel.fit("🗑️  venvoy Uninstaller", style="bold red"))

    # Detect platform
    system = platform.system().lower()
    home_path = Path.home()

    install_dir = home_path / ".venvoy" / "bin"
    venvoy_dir = home_path / ".venvoy"
    projects_dir = venvoy_dir / "projects"

    # Show what will be removed
    console.print("")
    console.print("This will remove:", style="bold yellow")
    console.print(f"  📁 Installation directory: {install_dir}")
    console.print(f"  📁 Configuration directory: {venvoy_dir}")
    if not keep_projects:
        console.print(f"  📁 Projects directory: {projects_dir}")
    console.print("  🔗 PATH entries from shell configuration files")
    if not keep_images:
        console.print(
            "  🐳 Docker images (venvoy/bootstrap:latest and venvoy/* images)"
        )
    console.print("")

    if not force:
        confirm = click.confirm("Are you sure you want to uninstall venvoy?")
        if not confirm:
            console.print("❌ Uninstallation cancelled", style="bold red")
            return

    console.print("")
    console.print("🗑️  Removing venvoy...", style="bold red")

    # Projects live inside ~/.venvoy/projects. Keep that directory by removing
    # its siblings instead of deleting the parent first.
    keep_project_tree = keep_projects
    if projects_dir.exists() and not keep_projects and not force:
        keep_project_tree = not click.confirm(
            "Remove projects directory with environment exports?"
        )

    if venvoy_dir.exists():
        if keep_project_tree and projects_dir.exists():
            for child in list(venvoy_dir.iterdir()):
                if child.resolve() == projects_dir.resolve():
                    continue
                if child.is_dir():
                    shutil.rmtree(child)
                else:
                    child.unlink()
            console.print(
                f"Removed configuration directory and kept {projects_dir}",
                style="green",
            )
        else:
            shutil.rmtree(venvoy_dir)
            console.print("Removed configuration directory", style="green")

    # Remove PATH entries from shell configuration files
    if system in ["linux", "darwin"]:  # Linux and macOS
        shell_files = [
            home_path / ".bashrc",
            home_path / ".zshrc",
            home_path / ".config" / "fish" / "config.fish",
            home_path / ".profile",
            home_path / ".bash_profile",
        ]

        for shell_file in shell_files:
            if shell_file.exists():
                try:
                    # Read current content
                    with open(shell_file, "r") as f:
                        content = f.read()

                    # Check if venvoy PATH is present
                    if str(install_dir) in content:
                        # Create backup
                        backup_file = shell_file.with_suffix(
                            shell_file.suffix + ".venvoy-backup"
                        )
                        shutil.copy2(shell_file, backup_file)

                        # Remove venvoy-related lines
                        lines = content.split("\n")
                        new_lines = []
                        skip_next = 0

                        for i, line in enumerate(lines):
                            if skip_next > 0:
                                skip_next -= 1
                                continue

                            if "# Added by venvoy installer" in line:
                                # Skip this line and the next 2 lines (comment + export + blank)
                                skip_next = 2
                                continue
                            elif str(install_dir) in line:
                                # Skip any line containing the install dir
                                continue
                            else:
                                new_lines.append(line)

                        # Write cleaned content
                        with open(shell_file, "w") as f:
                            f.write("\n".join(new_lines))

                        console.print(
                            f"✅ Cleaned PATH from {shell_file.name}", style="green"
                        )
                        console.print(
                            f"   📋 Backup saved as: {backup_file.name}", style="dim"
                        )

                except Exception as e:
                    console.print(
                        f"⚠️  Warning: Could not clean {shell_file.name}: {e}",
                        style="yellow",
                    )

        # Remove system-wide symlink if it exists
        system_link = Path("/usr/local/bin/venvoy")
        if system_link.exists() and system_link.is_symlink():
            try:
                system_link.unlink()
                console.print("✅ Removed system-wide symlink", style="green")
            except PermissionError:
                console.print(
                    "⚠️  Could not remove system-wide symlink (permission denied)",
                    style="yellow",
                )

    elif system == "windows":
        # Windows PATH cleanup
        try:
            import winreg

            # Get current user PATH
            with winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                "Environment",
                0,
                winreg.KEY_READ | winreg.KEY_WRITE,
            ) as key:
                try:
                    current_path, _ = winreg.QueryValueEx(key, "PATH")
                    if str(install_dir) in current_path:
                        # Create backup
                        backup_path = (
                            Path(os.environ.get("TEMP", "."))
                            / f"venvoy-path-backup-{os.getpid()}.txt"
                        )
                        with open(backup_path, "w") as f:
                            f.write(current_path)

                        # Remove venvoy from PATH
                        path_parts = [
                            p
                            for p in current_path.split(";")
                            if str(install_dir) not in p
                        ]
                        new_path = ";".join(path_parts)

                        winreg.SetValueEx(
                            key, "PATH", 0, winreg.REG_EXPAND_SZ, new_path
                        )
                        console.print("✅ Removed venvoy from user PATH", style="green")
                        console.print(
                            f"📋 PATH backup saved to: {backup_path}", style="dim"
                        )

                except FileNotFoundError:
                    pass  # PATH key doesn't exist
        except ImportError:
            console.print(
                "⚠️  Could not clean Windows PATH (winreg not available)", style="yellow"
            )
        except Exception as e:
            console.print(
                f"⚠️  Warning: Could not clean Windows PATH: {e}", style="yellow"
            )

    # Remove container images
    if not keep_images:
        console.print("")
        console.print("🐳 Cleaning up container images...", style="cyan")

        # Detect container runtime
        container_runtime = None
        for runtime in ["docker", "apptainer", "singularity", "podman"]:
            try:
                subprocess.run([runtime, "--version"], capture_output=True, check=True)
                container_runtime = runtime
                break
            except (subprocess.CalledProcessError, FileNotFoundError):
                continue

        if container_runtime:
            if container_runtime in ["docker", "podman"]:
                # Docker/Podman use 'rmi' command
                try:
                    # Remove bootstrap image
                    subprocess.run(
                        [
                            container_runtime,
                            "image",
                            "inspect",
                            "zaphodbeeblebrox3rd/venvoy:bootstrap",
                        ],
                        capture_output=True,
                        check=True,
                    )
                    subprocess.run(
                        [
                            container_runtime,
                            "rmi",
                            "zaphodbeeblebrox3rd/venvoy:bootstrap",
                        ],
                        capture_output=True,
                        check=True,
                    )
                    console.print("✅ Removed bootstrap image", style="green")
                except subprocess.CalledProcessError:
                    pass  # Image doesn't exist

                # Remove venvoy environment images
                try:
                    result = subprocess.run(
                        [
                            container_runtime,
                            "images",
                            "--format",
                            "{{.Repository}}:{{.Tag}}",
                        ],
                        capture_output=True,
                        text=True,
                        check=True,
                    )
                    venvoy_images = [
                        line
                        for line in result.stdout.strip().split("\n")
                        if line.startswith("zaphodbeeblebrox3rd/venvoy")
                        and "bootstrap" not in line
                    ]

                    if venvoy_images:
                        console.print(
                            "Found venvoy environment images:", style="yellow"
                        )
                        for image in venvoy_images:
                            console.print(f"  {image}")

                        if not force:
                            remove_images = click.confirm(
                                "Remove all venvoy environment images?"
                            )
                            if remove_images:
                                for image in venvoy_images:
                                    try:
                                        subprocess.run(
                                            [container_runtime, "rmi", image],
                                            capture_output=True,
                                            check=True,
                                        )
                                    except subprocess.CalledProcessError:
                                        pass  # Ignore errors
                                console.print(
                                    "✅ Removed venvoy environment images",
                                    style="green",
                                )
                        else:
                            for image in venvoy_images:
                                try:
                                    subprocess.run(
                                        [container_runtime, "rmi", image],
                                        capture_output=True,
                                        check=True,
                                    )
                                except subprocess.CalledProcessError:
                                    pass  # Ignore errors
                            console.print(
                                "✅ Removed venvoy environment images", style="green"
                            )

                except subprocess.CalledProcessError:
                    pass  # No images or command failed

                # Remove stopped containers (Docker/Podman only)
                try:
                    result = subprocess.run(
                        [container_runtime, "ps", "-a", "--format", "{{.Names}}"],
                        capture_output=True,
                        text=True,
                        check=True,
                    )
                    venvoy_containers = [
                        line
                        for line in result.stdout.strip().split("\n")
                        if "venvoy" in line.lower() or "bootstrap" in line.lower()
                    ]

                    for container in venvoy_containers:
                        if container and container != "NAMES":
                            try:
                                subprocess.run(
                                    [container_runtime, "rm", container],
                                    capture_output=True,
                                    check=True,
                                )
                            except subprocess.CalledProcessError:
                                pass  # Ignore errors

                    if venvoy_containers:
                        console.print("✅ Removed venvoy containers", style="green")

                except subprocess.CalledProcessError:
                    pass  # No containers or command failed

            elif container_runtime in ["apptainer", "singularity"]:
                # Apptainer/Singularity use cache clean instead of rmi
                console.print(
                    "🧹 Cleaning Apptainer/Singularity cache...", style="cyan"
                )
                try:
                    subprocess.run(
                        [container_runtime, "cache", "clean", "--force"],
                        capture_output=True,
                        check=True,
                    )
                    console.print("✅ Cleaned container cache", style="green")
                except subprocess.CalledProcessError:
                    console.print("⚠️  Could not clean cache", style="yellow")
        else:
            console.print(
                "⚠️  No container runtime available, skipping image cleanup",
                style="yellow",
            )

    console.print("")
    console.print("🎉 venvoy uninstalled successfully!", style="bold green")
    console.print("")
    console.print("📋 Next steps:", style="cyan")
    console.print("   1. Restart your terminal to update PATH")
    console.print("   2. Remove any remaining Docker volumes manually if needed:")
    console.print("      docker volume ls | grep venvoy", style="dim")
    console.print("")
    console.print(
        "💡 To reinstall venvoy later, run the installer again", style="yellow"
    )


@main.command()
def setup():
    """Initial setup and configuration of venvoy (run once after installation)"""
    console.print(Panel.fit("⚙️  Venvoy Initial Setup", style="bold green"))

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Setting up venvoy...", total=None)

        # Detect platform and check prerequisites
        progress.update(
            task, description="Detecting platform and checking prerequisites..."
        )
        detector = PlatformDetector()
        platform_info = detector.detect()
        # Validate platform detection results
        required_keys = ["system", "architecture", "platform", "python_version"]
        for key in required_keys:
            if key not in platform_info:
                raise RuntimeError(f"Platform detection failed: missing key '{key}'")
            if not platform_info[key]:
                raise RuntimeError(
                    f"Platform detection failed: empty value for '{key}'"
                )

        progress.update(task, description="Checking container runtime...")
        container_manager = ContainerManager()
        runtime_info = container_manager.get_runtime_info()
        # Validate runtime info
        required_runtime_keys = ["runtime", "version", "is_hpc"]
        for key in required_runtime_keys:
            if key not in runtime_info:
                raise RuntimeError(f"Runtime detection failed: missing key '{key}'")
        if not runtime_info["runtime"]:
            raise RuntimeError("Runtime detection failed: no runtime detected")
        console.print(f"🔧 Using {runtime_info['runtime']} {runtime_info['version']}")
        if runtime_info["is_hpc"]:
            console.print(
                f"🏢 HPC environment detected - using "
                f"{runtime_info['runtime']} for best compatibility"
            )

        progress.update(task, description="Checking AI editor installation...")
        # Try to detect editors (may not work if running inside container)
        vscode_available = container_manager.platform._check_vscode_available()
        devin_available = container_manager.platform._check_devin_available()

        if devin_available:
            editor_type, editor_available = "devin", True
        elif vscode_available:
            editor_type, editor_available = "vscode", True
        else:
            editor_type, editor_available = "none", False

        # Create ~/.venvoy/home directory for container mount
        progress.update(task, description="Creating venvoy home directory...")
        venvoy_home_dir = Path.home() / ".venvoy" / "home"
        venvoy_home_dir.mkdir(parents=True, exist_ok=True)
        # Set permissions: 755 (rwxr-xr-x) - user can read/write/execute, group/others can read/execute
        venvoy_home_dir.chmod(0o755)

        progress.remove_task(task)

    console.print("✅ Venvoy setup completed!")

    if editor_available:
        if editor_type == "devin":
            console.print("🧠 Devin detected and configured")
        elif editor_type == "vscode":
            console.print("🔧 VSCode detected and configured")
    else:
        console.print("🐚 No AI editor detected in this environment")
        console.print("   💡 Editor detection will happen when you run 'venvoy run'")
        console.print(
            "   💡 If you have Devin or VSCode installed, 'venvoy run' will automatically launch it"
        )

    console.print("\n📋 Next steps:")
    console.print(
        "   1. Run: venvoy init --python-version <version> --name <environment-name>"
    )
    console.print("   2. Run: venvoy run --name <environment-name>")
    console.print("      (This will automatically launch Devin/VSCode if available)")
    console.print("   3. Start coding with AI-powered environments!")


@main.command()
@click.option("--name", default="venvoy-env", help="Name of the environment to restore")
def restore(name: str):
    """Interactively restore environment from a previous export"""
    console.print(Panel.fit("🔄 Environment Restoration", style="bold green"))

    env = VenvoyEnvironment(name=name)

    # Check if environment exists
    if not env.config_file.exists():
        console.print(
            f"❌ Environment '{name}' not found. Run 'venvoy init --name {name}' first."
        )
        return

    # Get list of exports
    exports = env.list_environment_exports()

    if not exports:
        console.print("📭 No environment exports found for this environment.")
        console.print(
            "💡 Environment exports are created automatically when you install packages."
        )
        return

    # Present interactive selection
    selected_export = env.select_environment_export()

    if selected_export:
        console.print(f"🔄 Restoring environment from: {selected_export.name}")
        env.restore_from_environment_export(selected_export)
        console.print("✅ Environment restored successfully!")
        console.print(
            f"💡 Run 'venvoy run --name {name}' to start working with the restored environment"
        )
    else:
        console.print("🚫 Restoration cancelled")


@main.command(name="import")
@click.argument("file_path", type=click.Path(exists=True))
@click.option(
    "--format",
    default=None,
    type=click.Choice(["yaml", "dockerfile", "tarball", "archive", "wheelhouse"]),
    help="Import format. yaml is supported. Other choices are retired.",
)
@click.option("--force", is_flag=True, help="Overwrite existing environment")
def import_cmd(file_path: str, format: str, force: bool):
    """Import an environment from a YAML snapshot.

    dockerfile, tarball, archive, and wheelhouse are retired.
    """
    if format is None:
        if file_path.endswith(".yaml") or file_path.endswith(".yml"):
            format = "yaml"
        else:
            console.print(
                "Only YAML import is supported. dockerfile, tarball, archive, and wheelhouse are retired."
            )
            console.print("Export a YAML snapshot with: venvoy export --format yaml")
            return

    if format != "yaml":
        console.print(
            f"{format} import is retired. YAML is the environment snapshot format."
        )
        console.print("Use: venvoy import <file.yaml> --format yaml")
        return

    console.print(Panel.fit("Importing environment from YAML", style="bold green"))
    console.print(f"YAML: {file_path}")
    if not force and not click.confirm("Continue with import?"):
        console.print("Import cancelled")
        return

    try:
        temp_env = VenvoyEnvironment()
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Importing YAML...", total=None)
            env_name = temp_env.import_yaml(file_path, force=force)
            progress.remove_task(task)

        console.print(f"YAML imported successfully: {env_name}")
        console.print(f"To use it: venvoy init --name {env_name} --force")
    except Exception as e:
        console.print(f"Import failed: {e}")
        if "already exists" in str(e):
            console.print("Use --force to overwrite the existing environment")


@main.command()
@click.argument("name_arg", required=False)
@click.option("--name", default=None, help="Name of the environment to serve")
@click.option(
    "--port",
    type=int,
    default=None,
    help="Port for the in-container SSH server (default: auto-select a free port)",
)
@click.option(
    "--login-node",
    default=None,
    help="Login node hostname users SSH into (default: $VENVOY_LOGIN_NODE or $SLURM_SUBMIT_HOST)",
)
@click.option(
    "--bind-address",
    default="127.0.0.1",
    help="Address the SSH server binds to on the compute node (127.0.0.1 is most secure)",
)
@click.option(
    "--mount", multiple=True, help="Additional volume mounts (host:container)"
)
@click.option(
    "--pubkey-file",
    multiple=True,
    help="Public key file(s) to authorize (default: your ~/.ssh/authorized_keys and ~/.ssh/*.pub)",
)
def remote(
    name_arg: str,
    name: str,
    port: int,
    login_node: str,
    bind_address: str,
    mount: tuple,
    pubkey_file: tuple,
):
    """Serve an environment over SSH for a remote Devin to connect to.

    Run this ON A COMPUTE NODE inside a Slurm allocation. It starts an SSH
    server inside the venvoy container and prints a 'venvoy connect' command to
    run on your laptop. The connection tunnels through the login node.

    Example (interactive allocation):
        srun --pty bash
        venvoy remote --name my-research --login-node login.hpc.example.edu
    """
    from .remote import REMOTE_ENABLED, RemoteError, RemoteServer

    if not REMOTE_ENABLED:
        console.print(
            "❌ The remote bridge is disabled (REMOTE_ENABLED=False).", style="red"
        )
        return

    env_name = name if name is not None else (name_arg if name_arg else "venvoy-env")
    console.print(
        Panel.fit("🛰️  Starting venvoy remote environment", style="bold magenta")
    )

    env = VenvoyEnvironment(name=env_name)
    if not env.config_file.exists():
        console.print(
            f"❌ Environment '{env_name}' not found. Run 'venvoy init --name {env_name}' first.",
            style="red",
        )
        return

    try:
        server = RemoteServer(
            env=env,
            port=port,
            bind_address=bind_address,
            login_node=login_node,
            extra_mounts=list(mount),
            authorized_key_files=list(pubkey_file) or None,
        )
        return server.serve()
    except RemoteError as exc:
        console.print(f"❌ {exc}", style="red")
    except Exception as exc:  # noqa: BLE001
        console.print(f"❌ Failed to start remote environment: {exc}", style="red")


@main.command()
@click.argument("token", required=False)
@click.option(
    "--login-node",
    default=None,
    help="Login node hostname (overrides the value embedded in the token)",
)
@click.option("--alias", default=None, help="SSH host alias to create (default: venvoy-<name>)")
@click.option(
    "--workspace", default=None, help="Folder to open inside the container (default: /workspace)"
)
@click.option(
    "--editor",
    type=click.Choice(["devin-desktop", "code"]),
    default="devin-desktop",
    help="Editor to launch (default: devin-desktop)",
)
@click.option("--no-open", is_flag=True, help="Only write the SSH config; do not launch the editor")
@click.option("--print-config", is_flag=True, help="Print the SSH config block and exit")
def connect(
    token: str,
    login_node: str,
    alias: str,
    workspace: str,
    editor: str,
    no_open: bool,
    print_config: bool,
):
    """Connect local Devin to a remote venvoy environment.

    Run this ON YOUR LAPTOP using the token printed by 'venvoy remote' on the
    cluster. It writes an SSH config entry that tunnels through the login node
    and launches Devin Remote-SSH into the container.

    Example:
        venvoy connect eyJ2Ijox... --login-node login.hpc.example.edu
    """
    from .remote import REMOTE_ENABLED, RemoteClient, RemoteError, decode_token

    if not REMOTE_ENABLED:
        console.print(
            "❌ The remote bridge is disabled (REMOTE_ENABLED=False).", style="red"
        )
        return

    if not token:
        console.print("❌ A connection token is required.", style="red")
        console.print("💡 Copy the 'venvoy connect <token>' line printed on the cluster.")
        return

    try:
        payload = decode_token(token)
        client = RemoteClient(
            payload=payload,
            login_node=login_node,
            alias=alias,
            workspace=workspace,
        )

        if print_config:
            console.print(client.build_ssh_block())
            return

        client.write_ssh_config()
        console.print(
            Panel.fit("🔌 venvoy connection configured", style="bold green")
        )
        console.print(f"🔗 SSH host alias: {client.alias}")
        console.print(f"🖥️  Compute node: {payload['compute_node']} (via {client.login_node})")
        console.print(f"📁 Workspace: {client.workspace}")
        console.print(f"📝 SSH config updated: {client.ssh_config}")

        if no_open:
            console.print(
                f"\n💡 Open manually with: {editor} --folder-uri "
                f"vscode-remote://ssh-remote+{client.alias}{client.workspace}"
            )
            return

        console.print(f"\n🧠 Launching {editor} Remote-SSH...")
        if client.launch_editor(editor=editor):
            console.print("✅ Editor launched. It will install its remote server on first connect.")
        else:
            console.print(
                f"⚠️  Could not launch '{editor}'. Open manually with:", style="yellow"
            )
            console.print(
                f"   {editor} --folder-uri vscode-remote://ssh-remote+{client.alias}{client.workspace}"
            )
    except RemoteError as exc:
        console.print(f"❌ {exc}", style="red")
    except Exception as exc:  # noqa: BLE001
        console.print(f"❌ Failed to configure connection: {exc}", style="red")


@main.command()
def runtime_info():
    """Show information about the detected container runtime"""
    console.print(Panel.fit("🔧 Container Runtime Information", style="bold blue"))

    try:
        container_manager = ContainerManager()
        info = container_manager.get_runtime_info()

        console.print(f"Runtime: {info['runtime']}")
        console.print(f"Version: {info['version']}")
        console.print(f"HPC Environment: {info['is_hpc']}")

        if info["is_hpc"]:
            console.print("\n🏢 HPC Environment Detected!")
            if info["runtime"] in ["apptainer", "singularity"]:
                console.print("✅ Using Apptainer/Singularity - perfect for HPC!")
                console.print("💡 No root access required")
            elif info["runtime"] == "podman":
                console.print("✅ Using Podman - rootless containers available")
            else:
                console.print("⚠️  Using Docker - may require root access on HPC")
        else:
            console.print("\n💻 Development Environment")
            console.print(f"✅ Using {info['runtime']} for container management")

    except Exception as e:
        console.print(f"❌ Error detecting runtime: {e}")


@main.command()
def update():
    """Update venvoy to the latest version"""
    import subprocess

    console.print(Panel.fit("🔄 Updating venvoy", style="bold blue"))

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Updating venvoy...", total=None)

        # Update bootstrap image
        progress.update(task, description="Updating bootstrap image...")

        try:
            # Use ContainerManager to update with the correct runtime
            container_manager = ContainerManager()
            runtime_info = container_manager.get_runtime_info()
            runtime = runtime_info["runtime"]

            console.print(f"🔧 Using {runtime} to update bootstrap image...")

            # Use ContainerManager's pull_image method which handles normalization
            # For Podman, it will automatically add docker.io/ prefix
            bootstrap_image = "zaphodbeeblebrox3rd/venvoy:bootstrap"
            if not container_manager.pull_image(bootstrap_image):
                raise RuntimeError("Failed to pull bootstrap image")

            progress.remove_task(task)

            console.print("✅ venvoy updated successfully!")
            console.print("✨ All new features are now active")
            console.print("")
            console.print("🆕 New features available:")
            console.print("   • Dynamic code updates without container rebuilds")
            console.print("   • Enhanced container runtime support")
            console.print("   • Improved HPC cluster compatibility")
            console.print("   • Better error handling")
            console.print("   • Removal of dependency on conda")

        except RuntimeError as e:
            progress.remove_task(task)
            if "No supported container runtime found" in str(e):
                console.print(
                    "ℹ️  Running inside a container - skipping bootstrap image update"
                )
                console.print(
                    "💡 The bootstrap image will be updated when you run venvoy from outside the container"
                )
                console.print("✅ venvoy source code is already up to date")
            else:
                console.print(f"❌ Failed to update venvoy: {e}")
                console.print("💡 Try running the installer again:")
                console.print(
                    "   curl -fsSL https://raw.githubusercontent.com/zaphodbeeblebrox3rd/venvoy/main/install.sh | bash"
                )
        except subprocess.CalledProcessError as e:
            progress.remove_task(task)
            console.print(f"❌ Failed to update venvoy: {e}")
            console.print("💡 Try running the installer again:")
            console.print(
                "   curl -fsSL https://raw.githubusercontent.com/zaphodbeeblebrox3rd/venvoy/main/install.sh | bash"
            )


# Note: upgrade command is handled by the bootstrap script
# This prevents "unexpected extra argument" errors


@main.command()
@click.option(
    "--name", default=None, help="Name of the venvoy environment container to stop"
)
def exit(name: str):
    """Exit virtual environment or stop venvoy container"""
    import os
    import shutil
    import subprocess

    # If --name is provided, try to stop the container
    if name:
        container_manager = ContainerManager()
        runtime = container_manager.runtime

        # Find containers matching the environment name pattern
        # Container names follow pattern: venvoy-{name}-{pid}
        try:
            if runtime == ContainerRuntime.DOCKER:
                docker_path = shutil.which("docker")
                if docker_path:
                    # List all containers and find ones matching the pattern
                    result = subprocess.run(
                        [docker_path, "ps", "-a", "--format", "{{.Names}}"],
                        capture_output=True,
                        text=True,
                        check=True,
                    )
                    containers = [
                        c.strip() for c in result.stdout.split("\n") if c.strip()
                    ]
                    matching_containers = [
                        c for c in containers if c.startswith(f"venvoy-{name}-")
                    ]

                    if matching_containers:
                        for container in matching_containers:
                            console.print(f"🛑 Stopping container: {container}")
                            subprocess.run([docker_path, "stop", container], check=True)
                            subprocess.run([docker_path, "rm", container], check=True)
                        console.print(
                            f"✅ Stopped and removed containers for environment '{name}'"
                        )
                    else:
                        console.print(
                            f"ℹ️  No running containers found for environment '{name}'"
                        )
                else:
                    console.print("❌ Docker not found in PATH")
            elif runtime == ContainerRuntime.PODMAN:
                podman_path = shutil.which("podman")
                if podman_path:
                    # List all containers and find ones matching the pattern
                    result = subprocess.run(
                        [podman_path, "ps", "-a", "--format", "{{.Names}}"],
                        capture_output=True,
                        text=True,
                        check=True,
                    )
                    containers = [
                        c.strip() for c in result.stdout.split("\n") if c.strip()
                    ]
                    matching_containers = [
                        c for c in containers if c.startswith(f"venvoy-{name}-")
                    ]

                    if matching_containers:
                        for container in matching_containers:
                            console.print(f"🛑 Stopping container: {container}")
                            subprocess.run([podman_path, "stop", container], check=True)
                            subprocess.run([podman_path, "rm", container], check=True)
                        console.print(
                            f"✅ Stopped and removed containers for environment '{name}'"
                        )
                    else:
                        console.print(
                            f"ℹ️  No running containers found for environment '{name}'"
                        )
                else:
                    console.print("❌ Podman not found in PATH")
            else:
                console.print(
                    f"ℹ️  Container stopping not supported for {runtime.value} runtime"
                )
        except subprocess.CalledProcessError as e:
            console.print(f"❌ Failed to stop container: {e}")
        except Exception as e:
            console.print(f"❌ Error: {e}")
        return

    # Otherwise, handle virtual environment deactivation
    if os.environ.get("VIRTUAL_ENV"):
        console.print("🚪 Exiting virtual environment...")
        try:
            # Try to call the deactivate function
            subprocess.run(["deactivate"], shell=True, check=True)
        except subprocess.CalledProcessError:
            # If deactivate command fails, try to unset environment variables manually
            console.print(
                "💡 Deactivate command not found, manually cleaning environment..."
            )
            if "VIRTUAL_ENV" in os.environ:
                del os.environ["VIRTUAL_ENV"]
            if "PATH" in os.environ and "venvoy-test" in os.environ["PATH"]:
                # Remove venvoy-test from PATH
                path_parts = os.environ["PATH"].split(":")
                path_parts = [p for p in path_parts if "venvoy-test" not in p]
                os.environ["PATH"] = ":".join(path_parts)
            console.print("✅ Virtual environment deactivated")
    else:
        console.print("ℹ️  No virtual environment currently active")
        console.print(
            "💡 Use 'venvoy exit --name <environment-name>' to stop a running container"
        )
        console.print(
            "💡 Or use 'deactivate' directly if you're in a virtual environment"
        )


@main.command()
def deactivate():
    """Exit virtual environment (alias for 'venvoy exit')"""
    # Just call the exit command
    exit()


@main.command()
@click.argument("name_arg", required=False)
@click.option("--name", default=None, help="Name of the venvoy environment to delete")
@click.option("--force", is_flag=True, help="Skip confirmation prompt")
def delete(name_arg: str, name: str, force: bool):
    """Delete a venvoy environment and its associated containers

    You can specify the environment name as a positional argument:
    venvoy delete my-env

    Or use the --name option:
    venvoy delete --name my-env

    If both are provided, --name takes precedence.
    """
    import shutil
    import subprocess

    # Determine the environment name: --name takes precedence, then name_arg
    env_name = name if name is not None else (name_arg if name_arg else None)

    if not env_name:
        console.print("❌ Environment name is required.", style="red")
        console.print("💡 Usage: venvoy delete <environment-name>")
        console.print("   Or: venvoy delete --name <environment-name>")
        return

    console.print(Panel.fit(f"🗑️  Deleting Environment: {env_name}", style="bold red"))

    env = VenvoyEnvironment(name=env_name)

    # Check if environment exists
    if not env.config_file.exists():
        console.print(f"❌ Environment '{env_name}' not found.", style="red")
        console.print("💡 Use 'venvoy list' to see all available environments")
        return

    # Show what will be deleted
    console.print("")
    console.print("This will remove:", style="bold yellow")
    console.print(f"  📁 Environment directory: {env.env_dir}")
    console.print(f"  📁 Projects directory: {env.projects_dir}")
    console.print("  🐳 Associated containers")
    console.print("")

    if not force:
        confirm = click.confirm(
            f"Are you sure you want to delete environment '{env_name}'?"
        )
        if not confirm:
            console.print("❌ Deletion cancelled", style="bold red")
            return

    # Stop and remove associated containers first
    console.print("🛑 Stopping associated containers...", style="cyan")
    try:
        container_manager = ContainerManager()
        runtime = container_manager.runtime

        if runtime == ContainerRuntime.DOCKER:
            docker_path = shutil.which("docker")
            if docker_path:
                # List all containers and find ones matching the pattern
                result = subprocess.run(
                    [docker_path, "ps", "-a", "--format", "{{.Names}}"],
                    capture_output=True,
                    text=True,
                    check=True,
                )
                containers = [c.strip() for c in result.stdout.split("\n") if c.strip()]
                matching_containers = [
                    c for c in containers if c.startswith(f"venvoy-{env_name}-")
                ]

                for container in matching_containers:
                    console.print(f"  🛑 Stopping container: {container}")
                    subprocess.run(
                        [docker_path, "stop", container],
                        capture_output=True,
                        check=False,
                    )
                    subprocess.run(
                        [docker_path, "rm", container], capture_output=True, check=False
                    )

                if matching_containers:
                    console.print(
                        f"✅ Stopped and removed {len(matching_containers)} container(s)",
                        style="green",
                    )
        elif runtime == ContainerRuntime.PODMAN:
            podman_path = shutil.which("podman")
            if podman_path:
                result = subprocess.run(
                    [podman_path, "ps", "-a", "--format", "{{.Names}}"],
                    capture_output=True,
                    text=True,
                    check=True,
                )
                containers = [c.strip() for c in result.stdout.split("\n") if c.strip()]
                matching_containers = [
                    c for c in containers if c.startswith(f"venvoy-{env_name}-")
                ]

                for container in matching_containers:
                    console.print(f"  🛑 Stopping container: {container}")
                    subprocess.run(
                        [podman_path, "stop", container],
                        capture_output=True,
                        check=False,
                    )
                    subprocess.run(
                        [podman_path, "rm", container], capture_output=True, check=False
                    )

                if matching_containers:
                    console.print(
                        f"✅ Stopped and removed {len(matching_containers)} container(s)",
                        style="green",
                    )
    except Exception as e:
        console.print(f"⚠️  Warning: Could not stop containers: {e}", style="yellow")

    # Delete environment directory
    console.print("")
    console.print("🗑️  Removing environment files...", style="cyan")
    try:
        if env.env_dir.exists():
            shutil.rmtree(env.env_dir)
            console.print(
                f"✅ Removed environment directory: {env.env_dir}", style="green"
            )
    except Exception as e:
        console.print(f"❌ Failed to remove environment directory: {e}", style="red")
        return

    # Delete projects directory (optional - contains exports)
    try:
        if env.projects_dir.exists():
            if force or click.confirm(
                f"Also remove projects directory with exports? ({env.projects_dir})"
            ):
                shutil.rmtree(env.projects_dir)
                console.print(
                    f"✅ Removed projects directory: {env.projects_dir}", style="green"
                )
            else:
                console.print(
                    f"📁 Kept projects directory: {env.projects_dir}", style="yellow"
                )
    except Exception as e:
        console.print(
            f"⚠️  Warning: Could not remove projects directory: {e}", style="yellow"
        )

    console.print("")
    console.print(
        f"✅ Environment '{env_name}' deleted successfully!", style="bold green"
    )
    console.print("💡 Use 'venvoy list' to see remaining environments")


if __name__ == "__main__":
    main()
