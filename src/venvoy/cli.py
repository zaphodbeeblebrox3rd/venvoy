"""
Command-line interface for venvoy
"""

import click
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

from .core import VenvoyEnvironment
from .docker_manager import DockerManager
from .platform_detector import PlatformDetector

console = Console()


@click.group()
@click.version_option()
def main():
    """venvoy - A portable Python environment manager"""
    pass


@main.command()
@click.option(
    "--python-version",
    default="3.11",
    type=click.Choice(["3.9", "3.10", "3.11", "3.12", "3.13"]),
    help="Python version to use",
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
def init(python_version: str, name: str, force: bool):
    """Initialize a new portable Python environment"""
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
        
        progress.update(task, description="Checking Docker installation...")
        docker_manager = DockerManager()
        docker_manager.ensure_docker_installed()
        
        progress.update(task, description="Checking AI editor installation...")
        editor_type, editor_available = docker_manager.ensure_editor_installed()
        
        progress.update(task, description="Creating environment...")
        env = VenvoyEnvironment(name=name, python_version=python_version)
        env.initialize(force=force, editor_type=editor_type, editor_available=editor_available)
        
        progress.update(task, description="Building and launching container...")
        env.build_and_launch()
        
        progress.remove_task(task)
    
    console.print(f"✅ Environment '{name}' initialized successfully!")
    console.print(f"🐍 Python {python_version} runtime ready")
    
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
    help="Name of the environment to build"
)
@click.option(
    "--tag", 
    help="Tag for the built image"
)
@click.option(
    "--push", 
    is_flag=True, 
    help="Push to registry after building"
)
def build(name: str, tag: str, push: bool):
    """Build multi-architecture Docker image"""
    console.print(Panel.fit("🔨 Building multi-arch image", style="bold green"))
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Building image...", total=None)
        
        env = VenvoyEnvironment(name=name)
        
        progress.update(task, description="Setting up BuildKit...")
        env.setup_buildx()
        
        progress.update(task, description="Building multi-arch image...")
        image_tag = env.build_multiarch(tag=tag)
        
        if push:
            progress.update(task, description="Pushing to registry...")
            env.push_image(image_tag)
        
        progress.remove_task(task)
    
    console.print(f"✅ Multi-arch image built: {image_tag}")
    if push:
        console.print("📤 Image pushed to registry")


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
    console.print(Panel.fit("🏃 Launching environment", style="bold magenta"))
    
    env = VenvoyEnvironment(name=name)
    env.run(command=command, additional_mounts=list(mount))


@main.command()
@click.option(
    "--name", 
    default="venvoy-env", 
    help="Name of the environment to export"
)
@click.option(
    "--format", 
    default="yaml",
    type=click.Choice(["yaml", "dockerfile", "tarball"]),
    help="Export format"
)
@click.option(
    "--output", 
    help="Output file path"
)
def export(name: str, format: str, output: str):
    """Export environment for sharing/archival"""
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
        
        progress.remove_task(task)
    
    console.print(f"✅ Environment exported: {output_path}")


@main.command()
def list():
    """List all venvoy environments"""
    console.print(Panel.fit("📋 Venvoy Environments", style="bold blue"))
    
    env = VenvoyEnvironment()
    environments = env.list_environments()
    
    if not environments:
        console.print("No environments found. Use 'venvoy init' to create one.")
        return
    
    for env_info in environments:
        console.print(f"🐍 {env_info['name']} (Python {env_info['python_version']})")
        console.print(f"   Created: {env_info['created']}")
        console.print(f"   Status: {env_info['status']}")


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


if __name__ == "__main__":
    main() 