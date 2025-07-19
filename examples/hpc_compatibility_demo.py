#!/usr/bin/env python3
"""
HPC Compatibility Demo

This script demonstrates how venvoy automatically detects and uses
the best available container runtime for your environment.
"""

import os
import sys
from pathlib import Path

# Add the src directory to the path so we can import venvoy
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from venvoy.container_manager import ContainerManager, ContainerRuntime


def demo_runtime_detection():
    """Demonstrate automatic runtime detection"""
    print("🔧 Venvoy HPC Compatibility Demo")
    print("=" * 50)
    
    # Create container manager
    manager = ContainerManager()
    
    # Get runtime information
    info = manager.get_runtime_info()
    
    print(f"Detected Runtime: {info['runtime']}")
    print(f"Version: {info['version']}")
    print(f"HPC Environment: {info['is_hpc']}")
    
    if info['is_hpc']:
        print("\n🏢 HPC Environment Detected!")
        if info['runtime'] in ['apptainer', 'singularity']:
            print("✅ Perfect! Using Apptainer/Singularity")
            print("💡 No root access required")
            print("🔬 Ideal for scientific computing")
        elif info['runtime'] == 'podman':
            print("✅ Good! Using Podman")
            print("💡 Rootless containers available")
        else:
            print("⚠️  Using Docker")
            print("💡 May require root access on HPC clusters")
    else:
        print("\n💻 Development Environment")
        print(f"✅ Using {info['runtime']} for container management")
    
    return manager


def demo_runtime_availability():
    """Check what runtimes are available"""
    print("\n📋 Available Container Runtimes:")
    print("-" * 30)
    
    manager = ContainerManager()
    
    runtimes = [
        ContainerRuntime.APPTAINER,
        ContainerRuntime.SINGULARITY,
        ContainerRuntime.PODMAN,
        ContainerRuntime.DOCKER
    ]
    
    for runtime in runtimes:
        available = manager._check_runtime_available(runtime)
        status = "✅ Available" if available else "❌ Not available"
        print(f"{runtime.value:12} : {status}")
    
    print("\n💡 Venvoy automatically chooses the best available runtime")


def demo_hpc_environment_detection():
    """Show how HPC environment detection works"""
    print("\n🔍 HPC Environment Detection:")
    print("-" * 30)
    
    manager = ContainerManager()
    
    # Check HPC indicators
    hpc_indicators = [
        'SLURM_JOB_ID',
        'PBS_JOBID', 
        'LSB_JOBID',
        'SGE_JOB_ID',
        'HOSTNAME'
    ]
    
    print("Environment Variables:")
    for indicator in hpc_indicators:
        value = os.environ.get(indicator, "Not set")
        if value != "Not set":
            print(f"  {indicator}: {value} ✅")
        else:
            print(f"  {indicator}: {value}")
    
    # Check hostname patterns
    hostname = os.environ.get('HOSTNAME', '')
    hpc_patterns = ['login', 'compute', 'node', 'hpc', 'cluster']
    
    print(f"\nHostname: {hostname}")
    for pattern in hpc_patterns:
        if pattern in hostname.lower():
            print(f"  Contains '{pattern}' ✅")
    
    is_hpc = manager._is_hpc_environment()
    print(f"\nHPC Environment Detected: {is_hpc}")


def demo_container_operations():
    """Show how container operations work across runtimes"""
    print("\n🚀 Container Operations:")
    print("-" * 30)
    
    manager = ContainerManager()
    info = manager.get_runtime_info()
    
    print(f"Using runtime: {info['runtime']}")
    
    # Example of how venvoy would run a container
    example_image = "zaphodbeeblebrox3rd/venvoy:python3.11"
    example_volumes = {
        "/home/user/data": "/workspace/data",
        "/home/user/code": "/workspace/code"
    }
    
    print(f"\nExample container run:")
    print(f"  Image: {example_image}")
    print(f"  Volumes: {example_volumes}")
    
    if info['runtime'] == 'docker':
        print(f"  Command: docker run -v /home/user/data:/workspace/data -v /home/user/code:/workspace/code {example_image}")
    elif info['runtime'] in ['apptainer', 'singularity']:
        print(f"  Command: {info['runtime']} run --bind /home/user/data:/workspace/data --bind /home/user/code:/workspace/code {example_image}.sif")
    elif info['runtime'] == 'podman':
        print(f"  Command: podman run -v /home/user/data:/workspace/data -v /home/user/code:/workspace/code {example_image}")


def main():
    """Run the HPC compatibility demo"""
    try:
        # Demo 1: Runtime detection
        manager = demo_runtime_detection()
        
        # Demo 2: Runtime availability
        demo_runtime_availability()
        
        # Demo 3: HPC environment detection
        demo_hpc_environment_detection()
        
        # Demo 4: Container operations
        demo_container_operations()
        
        print("\n" + "=" * 50)
        print("🎉 Demo Complete!")
        print("\n💡 Key Benefits:")
        print("  • Automatic runtime detection")
        print("  • HPC compatibility out of the box")
        print("  • No code changes needed")
        print("  • Works on clusters without root access")
        
        print("\n🚀 Next Steps:")
        print("  • Run 'venvoy runtime-info' to check your setup")
        print("  • Run 'venvoy init' to create your first environment")
        print("  • Check docs/HPC_COMPATIBILITY.md for detailed information")
        
    except Exception as e:
        print(f"❌ Error during demo: {e}")
        print("💡 Make sure you have at least one container runtime installed")
        print("   (Docker, Apptainer, Singularity, or Podman)")


if __name__ == "__main__":
    main() 