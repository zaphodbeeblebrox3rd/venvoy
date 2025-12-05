"""
Command-line interface for venvoy
"""

import click
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

from .core import VenvoyEnvironment
from .container_manager import ContainerManager
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
        venvoy export           # Export for sharing (yaml/dockerfile/tarball/archive)
        venvoy import-archive   # Import comprehensive binary archive
        venvoy history          # View environment history
        venvoy update/upgrade   # Update venvoy to latest version
        venvoy exit/deactivate  # Exit virtual environment (same as 'deactivate')

    Scientific Reproducibility:
        venvoy export --format archive    # Create comprehensive binary archive
        venvoy import-archive archive.tar.gz  # Restore from binary archive

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
    type=click.Choice(["3.9", "3.10", "3.11", "3.12", "3.13"]),
    help="Python version to use (when runtime=python)",
)
@click.option(
    "--r-version",
    default="4.4",
    type=click.Choice(["4.2", "4.3", "4.4", "4.5"]),
    help="R version to use (when runtime=r)",
)
@click.option(
    "--name", 
    default="venvoy-env", 
    help="Name for the environment"
)
@click.option(
    "--force", 
    is_flag=True, 
    help="Force reinitialize even if environment exists"
)
def init(runtime: str, python_version: str, r_version: str, name: str, force: bool):
    """Initialize a new portable Python or R environment"""
    if runtime == "python":
        console.print(Panel.fit("🚀 Initializing venvoy Python environment", style="bold blue"))
    elif runtime == "r":
        console.print(Panel.fit("📊 Initializing venvoy R environment", style="bold green"))
    else:
        console.print(Panel.fit("🚀 Initializing venvoy environment", style="bold blue"))
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        # Detect platform and check prerequisites
        task = progress.add_task("Detecting platform and checking prerequisites...", total=None)
        detector = PlatformDetector()
        platform_info = detector.detect()
        
        progress.update(task, description="Checking container runtime...")
        container_manager = ContainerManager()
        runtime_info = container_manager.get_runtime_info()
        
        progress.update(task, description="Detecting available editors...")
        # Just detect editors, don't prompt for installation
        vscode_available = container_manager.platform._check_vscode_available()
        cursor_available = container_manager.platform._check_cursor_available()
        
        if cursor_available:
            editor_type, editor_available = "cursor", True
        elif vscode_available:
            editor_type, editor_available = "vscode", True
        else:
            editor_type, editor_available = "none", False
        
        progress.update(task, description="Creating environment...")
        env = VenvoyEnvironment(name=name, python_version=python_version, runtime=runtime, r_version=r_version)
        
        try:
            env.initialize(force=force, editor_type=editor_type, editor_available=editor_available)
        except RuntimeError as e:
            if "already exists" in str(e):
                progress.remove_task(task)
                console.print(f"\n❌ {e}")
                console.print(f"\n💡 To reinitialize the existing environment '{name}', use:")
                console.print(f"   venvoy init --name {name} --force")
                console.print(f"\n🔍 To see all your environments:")
                console.print(f"   venvoy list")
                console.print(f"\n🚀 To start working with the existing environment:")
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
        if editor_type == "cursor":
            console.print("💡 Use 'venvoy run' to start working in your environment")
            console.print("🧠 Cursor will automatically connect to your container with AI assistance")
        elif editor_type == "vscode":
            console.print("💡 Use 'venvoy run' to start working in your environment")
            console.print("🔧 VSCode will automatically connect to your container")
    else:
        console.print("💡 Use 'venvoy run' to launch an interactive shell in your environment")
        console.print("🐚 Your environment will start with an enhanced AI-ready bash/conda shell")


@main.command()
@click.option(
    "--name", 
    default="venvoy-env", 
    help="Name of the environment to freeze"
)
@click.option(
    "--include-dev", 
    is_flag=True, 
    help="Include development dependencies"
)
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
@click.option(
    "--name", 
    default="venvoy-env", 
    help="Name of the environment to run"
)
@click.option(
    "--command", 
    help="Command to run (default: interactive shell)"
)
@click.option(
    "--mount", 
    multiple=True, 
    help="Additional volume mounts (host:container)"
)
def run(name: str, command: str, mount: tuple):
    """Launch the portable Python environment"""
    console.print(Panel.fit("🏃 Launching environment - RUN COMMAND", style="bold magenta"))
    
    # Use the bootstrap script approach for consistency
    import subprocess
    import sys
    from pathlib import Path
    
    # Get the bootstrap script path
    bootstrap_script = Path.home() / ".venvoy" / "bin" / "venvoy"
    
    if not bootstrap_script.exists():
        console.print("❌ venvoy bootstrap script not found. Please run 'venvoy update' first.", style="red")
        sys.exit(1)
    
    # Build the command to pass to the bootstrap script
    cmd_args = ["run"]
    if name != "venvoy-env":  # Only add --name if it's not the default
        cmd_args.extend(["--name", name])
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
        console.print("❌ venvoy bootstrap script not found. Please run 'venvoy update' first.", style="red")
        sys.exit(1)


@main.command()
@click.option(
    "--name", 
    default="venvoy-env", 
    help="Name of the environment to export"
)
@click.option(
    "--format", 
    default="yaml",
    type=click.Choice(["yaml", "dockerfile", "tarball", "archive", "wheelhouse"]),
    help="Export format"
)
@click.option(
    "--output", 
    help="Output file path"
)
def export(name: str, format: str, output: str):
    """Export environment for sharing/archival
    
    Formats:
    - yaml: Environment specification (requirements.txt style)
    - dockerfile: Standalone Dockerfile for custom builds
    - tarball: Complete offline package with dependencies
    - archive: Comprehensive binary archive for scientific reproducibility (architecture-specific)
    - wheelhouse: Cross-architecture package cache with source distributions and multi-arch wheels
    
    The 'archive' format creates a large file (1-5GB) containing the complete
    Docker image, system packages, and metadata for long-term archival and
    regulatory compliance. Use this for scientific reproducibility when
    package abandonment or PyPI changes are a concern.
    
    The 'wheelhouse' format creates a cross-architecture package cache containing:
    - Python: Source distributions (architecture-independent) and wheels for multiple architectures
    - R: Source packages and binary packages for multiple architectures
    This allows installation on any architecture (amd64, arm64) without depending on
    repository availability (PyPI/CRAN), while remaining compatible across different CPU architectures.
    """
    if format == "archive":
        console.print(Panel.fit("📦 Creating Comprehensive Binary Archive", style="bold red"))
        console.print("⚠️  [yellow]This creates a large file (1-5GB) for long-term scientific reproducibility[/yellow]")
    elif format == "wheelhouse":
        console.print(Panel.fit("📦 Creating Cross-Architecture Wheelhouse", style="bold cyan"))
        console.print("🌐 [cyan]This creates a package cache compatible across architectures (amd64, arm64)[/cyan]")
    else:
        console.print(Panel.fit("📤 Exporting environment", style="bold yellow"))
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Exporting environment...", total=None)
        
        env = VenvoyEnvironment(name=name)
        
        if format == "yaml":
            progress.update(task, description="Generating environment.yaml...")
            output_path = env.export_yaml(output)
        elif format == "dockerfile":
            progress.update(task, description="Generating Dockerfile...")
            output_path = env.export_dockerfile(output)
        elif format == "tarball":
            progress.update(task, description="Creating tarball...")
            output_path = env.export_tarball(output)
        elif format == "archive":
            progress.update(task, description="Creating comprehensive binary archive...")
            output_path = env.export_archive(output)
        elif format == "wheelhouse":
            progress.update(task, description="Creating cross-architecture wheelhouse...")
            output_path = env.export_wheelhouse(output)
        
        progress.remove_task(task)
    
    if format == "archive":
        console.print(f"✅ [green]Comprehensive archive created:[/green] {output_path}")
        console.print("🔬 [cyan]This archive ensures bit-for-bit reproducible results[/cyan]")
        console.print("📁 [dim]Contains complete Docker image, system packages, and metadata[/dim]")
    elif format == "wheelhouse":
        console.print(f"✅ [green]Cross-architecture wheelhouse created:[/green] {output_path}")
        console.print("🌐 [cyan]Compatible across architectures (amd64, arm64)[/cyan]")
        console.print("📦 [dim]Contains source distributions and multi-arch packages (Python + R)[/dim]")
        console.print("💡 [dim]Install on any architecture without repository dependency[/dim]")
    else:
        console.print(f"✅ Environment exported: {output_path}")


def _list_environments():
    """Internal function to list all venvoy environments"""
    console.print(Panel.fit("📋 Venvoy Environments", style="bold blue"))
    
    env = VenvoyEnvironment()
    environments = env.list_environments()
    
    if not environments:
        console.print("No environments found.")
        console.print ("Here is an example on how to create one: 'venvoy init --python-version 3.13 --name mynewpy313'")
        return
    
    for env_info in environments:
        console.print(f"🐍 {env_info['name']} (Python {env_info['python_version']})")
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
def list():
    """List all venvoy environments (conda-like alias)"""
    _list_environments()


@main.command()
@click.option(
    "--name", 
    default="venvoy-env", 
    help="Name of the environment to list exports for"
)
def history(name: str):
    """List environment export history"""
    console.print(Panel.fit(f"📜 Environment Export History: {name}", style="bold purple"))
    
    env = VenvoyEnvironment(name=name)
    exports = env.list_environment_exports()
    
    if not exports:
        console.print(f"No export history found for environment '{name}'.")
        console.print("💡 Environment exports are created automatically when packages change.")
        return
    
    console.print(f"Found {len(exports)} environment exports:\n")
    
    for i, export in enumerate(exports, 1):
        # Status indicator for most recent
        status = "🔥 Latest" if i == 1 else f"#{i:2d}"
        
        console.print(f"{status} {export['formatted_time']}")
        console.print(f"    📦 {export['total_packages']} packages ({export['conda_packages']} conda, {export['pip_packages']} pip)")
        console.print(f"    💾 {export['file'].name}")
        
        if i < len(exports):  # Don't add separator after last item
            console.print()
    
    console.print(f"\n💡 Use 'venvoy init --name {name}' to restore from any of these exports")
    console.print(f"📂 Export files stored in: ~/venvoy-projects/{name}/")
    console.print("🔄 New exports are created automatically when packages change")


@main.command()
@click.option(
    "--name", 
    default="venvoy-env", 
    help="Name of the environment to configure"
)
def configure(name: str):
    """Configure environment settings"""
    console.print(Panel.fit("⚙️  Configure Environment", style="bold cyan"))
    
    env = VenvoyEnvironment(name=name)
    
    if not env.config_file.exists():
        console.print(f"❌ Environment '{name}' not found. Use 'venvoy init' to create it.")
        return
    
    # Check current editor configuration
    current_editor_type, current_editor_available = env._get_editor_config()
    docker_manager = DockerManager()
    actual_vscode = docker_manager.platform._check_vscode_available()
    actual_cursor = docker_manager.platform._check_cursor_available()
    
    console.print(f"Current editor: {current_editor_type.title() if current_editor_type != 'none' else 'None'}")
    console.print(f"Current status: {'✅ Enabled' if current_editor_available else '❌ Disabled'}")
    console.print(f"VSCode available: {'✅ Yes' if actual_vscode else '❌ No'}")
    console.print(f"Cursor available: {'✅ Yes' if actual_cursor else '❌ No'}")
    
    # Check if configuration needs updating
    needs_update = False
    new_config = {}
    
    if actual_cursor and actual_vscode:
        if not current_editor_available or current_editor_type == "none":
            console.print("\n🎉 Both AI editors are available!")
            choice = click.prompt(
                "Which would you prefer? (1=Cursor, 2=VSCode, 3=None)", 
                type=click.Choice(['1', '2', '3'])
            )
            if choice == '1':
                new_config = {'editor_type': 'cursor', 'editor_available': True}
                console.print("🧠 Cursor integration enabled!")
            elif choice == '2':
                new_config = {'editor_type': 'vscode', 'editor_available': True}
                console.print("🔧 VSCode integration enabled!")
            else:
                new_config = {'editor_type': 'none', 'editor_available': False}
                console.print("🐚 Interactive shell mode enabled!")
            needs_update = True
    elif actual_cursor and (current_editor_type != "cursor" or not current_editor_available):
        if click.confirm("Cursor is available. Enable Cursor integration?"):
            new_config = {'editor_type': 'cursor', 'editor_available': True}
            console.print("🧠 Cursor integration enabled!")
            needs_update = True
    elif actual_vscode and (current_editor_type != "vscode" or not current_editor_available):
        if click.confirm("VSCode is available. Enable VSCode integration?"):
            new_config = {'editor_type': 'vscode', 'editor_available': True}
            console.print("🔧 VSCode integration enabled!")
            needs_update = True
    elif not actual_cursor and not actual_vscode and current_editor_available:
        console.print("⚠️  No AI editors are available. Switching to interactive shell mode.")
        new_config = {'editor_type': 'none', 'editor_available': False}
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
    
    console.print("\n🚀 **venvoy** includes multiple package managers for optimal performance:\n")
    
    # Mamba info
    console.print("🐍 **mamba** - Fast conda replacement")
    console.print("   • ⚡ 10-100x faster dependency resolution than conda")
    console.print("   • 🔄 Drop-in replacement for conda commands")
    console.print("   • 📦 Best for: Scientific packages, complex dependencies")
    console.print("   • Usage: `mamba install numpy pandas scikit-learn`")
    console.print("   • Channels: conda-forge (default), bioconda, etc.\n")
    
    # UV info  
    console.print("🦄 **uv** - Ultra-fast Python package installer")
    console.print("   • ⚡ 10-100x faster than pip for pure Python packages")
    console.print("   • 🏗️  Written in Rust for maximum performance")
    console.print("   • 📦 Best for: Pure Python packages, web frameworks")
    console.print("   • Usage: `uv pip install requests flask fastapi`")
    console.print("   • Note: Uses PyPI registry\n")
    
    # Pip info
    console.print("🐍 **pip** - Standard Python package installer")
    console.print("   • 📚 Universal compatibility")
    console.print("   • 🔧 Fallback for packages not available elsewhere")
    console.print("   • 📦 Best for: Legacy packages, special cases")
    console.print("   • Usage: `pip install some-package`\n")
    
    console.print("💡 **Recommendations:**")
    console.print("   • For AI/ML packages: `mamba install -c conda-forge tensorflow pytorch`")
    console.print("   • For web development: `uv pip install fastapi uvicorn`")
    console.print("   • For data science: `mamba install pandas numpy matplotlib jupyter`")
    console.print("   • For quick installs: `uv pip install requests beautifulsoup4`")


@main.command()
@click.option(
    "--force", 
    is_flag=True, 
    help="Skip confirmation prompts"
)
@click.option(
    "--keep-projects", 
    is_flag=True, 
    help="Keep environment exports in ~/venvoy-projects"
)
@click.option(
    "--keep-images", 
    is_flag=True, 
    help="Keep Docker images"
)
def uninstall(force: bool, keep_projects: bool, keep_images: bool):
    """Uninstall venvoy and clean up all files"""
    import os
    import shutil
    import subprocess
    import platform
    from pathlib import Path
    
    console.print(Panel.fit("🗑️  venvoy Uninstaller", style="bold red"))
    
    # Detect platform
    system = platform.system().lower()
    home_path = Path.home()
    
    install_dir = home_path / ".venvoy" / "bin"
    venvoy_dir = home_path / ".venvoy"
    projects_dir = home_path / "venvoy-projects"
    
    # Show what will be removed
    console.print("")
    console.print("This will remove:", style="bold yellow")
    console.print(f"  📁 Installation directory: {install_dir}")
    console.print(f"  📁 Configuration directory: {venvoy_dir}")
    if not keep_projects:
        console.print(f"  📁 Projects directory: {projects_dir}")
    console.print("  🔗 PATH entries from shell configuration files")
    if not keep_images:
        console.print("  🐳 Docker images (venvoy/bootstrap:latest and venvoy/* images)")
    console.print("")
    
    if not force:
        confirm = click.confirm("Are you sure you want to uninstall venvoy?")
        if not confirm:
            console.print("❌ Uninstallation cancelled", style="bold red")
            return
    
    console.print("")
    console.print("🗑️  Removing venvoy...", style="bold red")
    
    # Remove installation directory
    if install_dir.exists():
        shutil.rmtree(install_dir)
        console.print("✅ Removed installation directory", style="green")
    
    # Remove configuration directory
    if venvoy_dir.exists():
        shutil.rmtree(venvoy_dir)
        console.print("✅ Removed configuration directory", style="green")
    
    # Handle projects directory
    if projects_dir.exists():
        if keep_projects:
            console.print(f"📁 Kept projects directory: {projects_dir}", style="yellow")
        else:
            if not force:
                remove_projects = click.confirm("Remove projects directory with environment exports?")
                if remove_projects:
                    shutil.rmtree(projects_dir)
                    console.print("✅ Removed projects directory", style="green")
                else:
                    console.print(f"📁 Kept projects directory: {projects_dir}", style="yellow")
            else:
                shutil.rmtree(projects_dir)
                console.print("✅ Removed projects directory", style="green")
    
    # Remove PATH entries from shell configuration files
    if system in ["linux", "darwin"]:  # Linux and macOS
        shell_files = [
            home_path / ".bashrc",
            home_path / ".zshrc",
            home_path / ".config" / "fish" / "config.fish",
            home_path / ".profile",
            home_path / ".bash_profile"
        ]
        
        for shell_file in shell_files:
            if shell_file.exists():
                try:
                    # Read current content
                    with open(shell_file, 'r') as f:
                        content = f.read()
                    
                    # Check if venvoy PATH is present
                    if str(install_dir) in content:
                        # Create backup
                        backup_file = shell_file.with_suffix(shell_file.suffix + '.venvoy-backup')
                        shutil.copy2(shell_file, backup_file)
                        
                        # Remove venvoy-related lines
                        lines = content.split('\n')
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
                        with open(shell_file, 'w') as f:
                            f.write('\n'.join(new_lines))
                        
                        console.print(f"✅ Cleaned PATH from {shell_file.name}", style="green")
                        console.print(f"   📋 Backup saved as: {backup_file.name}", style="dim")
                        
                except Exception as e:
                    console.print(f"⚠️  Warning: Could not clean {shell_file.name}: {e}", style="yellow")
        
        # Remove system-wide symlink if it exists
        system_link = Path("/usr/local/bin/venvoy")
        if system_link.exists() and system_link.is_symlink():
            try:
                system_link.unlink()
                console.print("✅ Removed system-wide symlink", style="green")
            except PermissionError:
                console.print("⚠️  Could not remove system-wide symlink (permission denied)", style="yellow")
    
    elif system == "windows":
        # Windows PATH cleanup
        try:
            import winreg
            
            # Get current user PATH
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment", 0, winreg.KEY_READ | winreg.KEY_WRITE) as key:
                try:
                    current_path, _ = winreg.QueryValueEx(key, "PATH")
                    if str(install_dir) in current_path:
                        # Create backup
                        backup_path = Path(os.environ.get('TEMP', '.')) / f"venvoy-path-backup-{os.getpid()}.txt"
                        with open(backup_path, 'w') as f:
                            f.write(current_path)
                        
                        # Remove venvoy from PATH
                        path_parts = [p for p in current_path.split(';') if str(install_dir) not in p]
                        new_path = ';'.join(path_parts)
                        
                        winreg.SetValueEx(key, "PATH", 0, winreg.REG_EXPAND_SZ, new_path)
                        console.print("✅ Removed venvoy from user PATH", style="green")
                        console.print(f"📋 PATH backup saved to: {backup_path}", style="dim")
                        
                except FileNotFoundError:
                    pass  # PATH key doesn't exist
        except ImportError:
            console.print("⚠️  Could not clean Windows PATH (winreg not available)", style="yellow")
        except Exception as e:
            console.print(f"⚠️  Warning: Could not clean Windows PATH: {e}", style="yellow")
    
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
                    subprocess.run([container_runtime, "image", "inspect", "zaphodbeeblebrox3rd/venvoy:bootstrap"], 
                                 capture_output=True, check=True)
                    subprocess.run([container_runtime, "rmi", "zaphodbeeblebrox3rd/venvoy:bootstrap"], 
                                 capture_output=True, check=True)
                    console.print("✅ Removed bootstrap image", style="green")
                except subprocess.CalledProcessError:
                    pass  # Image doesn't exist
                
                # Remove venvoy environment images
                try:
                    result = subprocess.run([container_runtime, "images", "--format", "{{.Repository}}:{{.Tag}}"], 
                                          capture_output=True, text=True, check=True)
                    venvoy_images = [line for line in result.stdout.strip().split('\n') 
                                   if line.startswith('zaphodbeeblebrox3rd/venvoy') and 'bootstrap' not in line]
                    
                    if venvoy_images:
                        console.print("Found venvoy environment images:", style="yellow")
                        for image in venvoy_images:
                            console.print(f"  {image}")
                        
                        if not force:
                            remove_images = click.confirm("Remove all venvoy environment images?")
                            if remove_images:
                                for image in venvoy_images:
                                    try:
                                        subprocess.run([container_runtime, "rmi", image], 
                                                     capture_output=True, check=True)
                                    except subprocess.CalledProcessError:
                                        pass  # Ignore errors
                                console.print("✅ Removed venvoy environment images", style="green")
                        else:
                            for image in venvoy_images:
                                try:
                                    subprocess.run([container_runtime, "rmi", image], 
                                                 capture_output=True, check=True)
                                except subprocess.CalledProcessError:
                                    pass  # Ignore errors
                            console.print("✅ Removed venvoy environment images", style="green")
                            
                except subprocess.CalledProcessError:
                    pass  # No images or command failed
                
                # Remove stopped containers (Docker/Podman only)
                try:
                    result = subprocess.run([container_runtime, "ps", "-a", "--format", "{{.Names}}"], 
                                          capture_output=True, text=True, check=True)
                    venvoy_containers = [line for line in result.stdout.strip().split('\n') 
                                       if 'venvoy' in line.lower() or 'bootstrap' in line.lower()]
                    
                    for container in venvoy_containers:
                        if container and container != "NAMES":
                            try:
                                subprocess.run([container_runtime, "rm", container], 
                                             capture_output=True, check=True)
                            except subprocess.CalledProcessError:
                                pass  # Ignore errors
                    
                    if venvoy_containers:
                        console.print("✅ Removed venvoy containers", style="green")
                        
                except subprocess.CalledProcessError:
                    pass  # No containers or command failed
                    
            elif container_runtime in ["apptainer", "singularity"]:
                # Apptainer/Singularity use cache clean instead of rmi
                console.print("🧹 Cleaning Apptainer/Singularity cache...", style="cyan")
                try:
                    subprocess.run([container_runtime, "cache", "clean", "--force"], 
                                 capture_output=True, check=True)
                    console.print("✅ Cleaned container cache", style="green")
                except subprocess.CalledProcessError:
                    console.print("⚠️  Could not clean cache", style="yellow")
        else:
            console.print("⚠️  No container runtime available, skipping image cleanup", style="yellow")
    
    console.print("")
    console.print("🎉 venvoy uninstalled successfully!", style="bold green")
    console.print("")
    console.print("📋 Next steps:", style="cyan")
    console.print("   1. Restart your terminal to update PATH")
    console.print("   2. Remove any remaining Docker volumes manually if needed:")
    console.print("      docker volume ls | grep venvoy", style="dim")
    console.print("")
    console.print("💡 To reinstall venvoy later, run the installer again", style="yellow")


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
        progress.update(task, description="Detecting platform and checking prerequisites...")
        detector = PlatformDetector()
        platform_info = detector.detect()
        
        progress.update(task, description="Checking container runtime...")
        container_manager = ContainerManager()
        runtime_info = container_manager.get_runtime_info()
        console.print(f"🔧 Using {runtime_info['runtime']} {runtime_info['version']}")
        if runtime_info['is_hpc']:
            console.print(f"🏢 HPC environment detected - using {runtime_info['runtime']} for best compatibility")
        
        progress.update(task, description="Checking AI editor installation...")
        # Try to detect editors (may not work if running inside container)
        vscode_available = container_manager.platform._check_vscode_available()
        cursor_available = container_manager.platform._check_cursor_available()
        
        if cursor_available:
            editor_type, editor_available = "cursor", True
        elif vscode_available:
            editor_type, editor_available = "vscode", True
        else:
            editor_type, editor_available = "none", False
        
        progress.remove_task(task)
    
    console.print("✅ Venvoy setup completed!")
    
    if editor_available:
        if editor_type == "cursor":
            console.print("🧠 Cursor detected and configured")
        elif editor_type == "vscode":
            console.print("🔧 VSCode detected and configured")
    else:
        console.print("🐚 No AI editor detected in this environment")
        console.print("   💡 Editor detection will happen when you run 'venvoy run'")
        console.print("   💡 If you have Cursor or VSCode installed, 'venvoy run' will automatically launch it")
    
    console.print("\n📋 Next steps:")
    console.print("   1. Run: venvoy init --python-version <version> --name <environment-name>")
    console.print("   2. Run: venvoy run --name <environment-name>")
    console.print("      (This will automatically launch Cursor/VSCode if available)")
    console.print("   3. Start coding with AI-powered environments!")


@main.command()
@click.option(
    "--name", 
    default="venvoy-env", 
    help="Name of the environment to restore"
)
def restore(name: str):
    """Interactively restore environment from a previous export"""
    console.print(Panel.fit("🔄 Environment Restoration", style="bold green"))
    
    env = VenvoyEnvironment(name=name)
    
    # Check if environment exists
    if not env.config_file.exists():
        console.print(f"❌ Environment '{name}' not found. Run 'venvoy init --name {name}' first.")
        return
    
    # Get list of exports
    exports = env.list_environment_exports()
    
    if not exports:
        console.print("📭 No environment exports found for this environment.")
        console.print("💡 Environment exports are created automatically when you install packages.")
        return
    
    # Present interactive selection
    selected_export = env.select_environment_export()
    
    if selected_export:
        console.print(f"🔄 Restoring environment from: {selected_export.name}")
        env.restore_from_environment_export(selected_export)
        console.print("✅ Environment restored successfully!")
        console.print("💡 Run 'venvoy run' to start working with the restored environment")
    else:
        console.print("🚫 Restoration cancelled")


@main.command()
@click.argument("archive_path", type=click.Path(exists=True))
@click.option(
    "--force", 
    is_flag=True, 
    help="Overwrite existing environment"
)
def import_archive(archive_path: str, force: bool):
    """Import environment from a comprehensive binary archive"""
    console.print(Panel.fit("📦 Importing Binary Archive", style="bold blue"))
    console.print(f"📁 Archive: {archive_path}")
    
    if not force:
        console.print("⚠️  [yellow]This will load Docker images and restore environment configuration[/yellow]")
        if not click.confirm("Continue with import?"):
            console.print("🚫 Import cancelled")
            return
    
    try:
        # Create temporary environment for import
        temp_env = VenvoyEnvironment()
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Importing archive...", total=None)
            
            progress.update(task, description="Extracting and analyzing archive...")
            env_name = temp_env.import_archive(archive_path, force=force)
            
            progress.remove_task(task)
        
        console.print(f"✅ [green]Archive imported successfully![/green]")
        console.print(f"📦 Environment: {env_name}")
        console.print(f"🚀 Run with: [cyan]venvoy run --name {env_name}[/cyan]")
        console.print(f"📋 View history: [cyan]venvoy history --name {env_name}[/cyan]")
        
    except Exception as e:
        console.print(f"❌ [red]Import failed:[/red] {str(e)}")
        if "already exists" in str(e):
            console.print("💡 Use --force to overwrite existing environment")


@main.command()
@click.argument("wheelhouse_path", type=click.Path(exists=True))
@click.option(
    "--force", 
    is_flag=True, 
    help="Overwrite existing environment"
)
def import_wheelhouse(wheelhouse_path: str, force: bool):
    """Import environment from a cross-architecture wheelhouse"""
    console.print(Panel.fit("📦 Importing Cross-Architecture Wheelhouse", style="bold cyan"))
    console.print(f"📁 Wheelhouse: {wheelhouse_path}")
    
    if not force:
        console.print("🌐 [cyan]This will restore packages for cross-architecture compatibility[/cyan]")
        if not click.confirm("Continue with import?"):
            console.print("🚫 Import cancelled")
            return
    
    try:
        # Create temporary environment for import
        temp_env = VenvoyEnvironment()
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Importing wheelhouse...", total=None)
            
            progress.update(task, description="Extracting and analyzing wheelhouse...")
            env_name = temp_env.import_wheelhouse(wheelhouse_path, force=force)
            
            progress.remove_task(task)
        
        console.print(f"✅ [green]Wheelhouse imported successfully![/green]")
        console.print(f"📦 Environment: {env_name}")
        console.print(f"🌐 [cyan]Packages are cross-architecture compatible (amd64, arm64)[/cyan]")
        console.print(f"🚀 To build and use: [cyan]venvoy init --name {env_name} --force[/cyan]")
        console.print(f"💡 [dim]Packages will be installed from local cache (no repository access needed)[/dim]")
        
    except Exception as e:
        console.print(f"❌ [red]Import failed:[/red] {str(e)}")
        if "already exists" in str(e):
            console.print("💡 Use --force to overwrite existing environment")


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
        
        if info['is_hpc']:
            console.print("\n🏢 HPC Environment Detected!")
            if info['runtime'] in ['apptainer', 'singularity']:
                console.print("✅ Using Apptainer/Singularity - perfect for HPC!")
                console.print("💡 No root access required")
            elif info['runtime'] == 'podman':
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
            runtime = runtime_info['runtime']
            
            console.print(f"🔧 Using {runtime} to update bootstrap image...")
            
            # Format image URI based on container runtime
            if runtime in ['apptainer', 'singularity']:
                image_uri = "docker://zaphodbeeblebrox3rd/venvoy:bootstrap"
                # For Apptainer/Singularity, use --force to overwrite existing SIF files
                result = subprocess.run(
                    [runtime, "pull", "--force", image_uri],
                    capture_output=True,
                    text=True,
                    check=True
                )
            else:
                image_uri = "zaphodbeeblebrox3rd/venvoy:bootstrap"
                result = subprocess.run(
                    [runtime, "pull", image_uri],
                    capture_output=True,
                    text=True,
                    check=True
                )
            
            progress.remove_task(task)
            
            console.print("✅ venvoy updated successfully!")
            console.print("✨ All new features are now active")
            console.print("")
            console.print("🆕 New features available:")
            console.print("   • Dynamic code updates without container rebuilds")
            console.print("   • Enhanced container runtime support")
            console.print("   • Improved HPC cluster compatibility")
            console.print("   • Better error handling")
            
        except RuntimeError as e:
            progress.remove_task(task)
            if "No supported container runtime found" in str(e):
                console.print("ℹ️  Running inside a container - skipping bootstrap image update")
                console.print("💡 The bootstrap image will be updated when you run venvoy from outside the container")
                console.print("✅ venvoy source code is already up to date")
            else:
                console.print(f"❌ Failed to update venvoy: {e}")
                console.print("💡 Try running the installer again:")
                console.print("   curl -fsSL https://raw.githubusercontent.com/zaphodbeeblebrox3rd/venvoy/main/install.sh | bash")
        except subprocess.CalledProcessError as e:
            progress.remove_task(task)
            console.print(f"❌ Failed to update venvoy: {e}")
            console.print("💡 Try running the installer again:")
            console.print("   curl -fsSL https://raw.githubusercontent.com/zaphodbeeblebrox3rd/venvoy/main/install.sh | bash")


# Note: upgrade command is handled by the bootstrap script
# This prevents "unexpected extra argument" errors


@main.command()
def exit():
    """Exit virtual environment (same as 'deactivate')"""
    import os
    import subprocess
    
    # Check if we're in a virtual environment
    if os.environ.get('VIRTUAL_ENV'):
        console.print("🚪 Exiting virtual environment...")
        try:
            # Try to call the deactivate function
            subprocess.run(['deactivate'], shell=True, check=True)
        except subprocess.CalledProcessError:
            # If deactivate command fails, try to unset environment variables manually
            console.print("💡 Deactivate command not found, manually cleaning environment...")
            if 'VIRTUAL_ENV' in os.environ:
                del os.environ['VIRTUAL_ENV']
            if 'PATH' in os.environ and 'venvoy-test' in os.environ['PATH']:
                # Remove venvoy-test from PATH
                path_parts = os.environ['PATH'].split(':')
                path_parts = [p for p in path_parts if 'venvoy-test' not in p]
                os.environ['PATH'] = ':'.join(path_parts)
            console.print("✅ Virtual environment deactivated")
    else:
        console.print("ℹ️  No virtual environment currently active")
        console.print("💡 Use 'deactivate' directly if you're in a virtual environment")


@main.command()
def deactivate():
    """Exit virtual environment (alias for 'venvoy exit')"""
    # Just call the exit command
    exit()


if __name__ == "__main__":
    main() 