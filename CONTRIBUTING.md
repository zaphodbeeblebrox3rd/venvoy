# Contributing to venvoy

Thank you for your interest in contributing to venvoy! This document provides guidelines and information for contributors to help maintain the project's quality and scientific computing focus.

## 🔬 Our Mission

venvoy is dedicated to **scientific reproducibility** and creating truly portable Python and R environments that deliver identical results across any platform. We serve data scientists, researchers, and teams who need:

- Exact same numerical results from the same analysis, regardless of hardware
- Bit-for-bit identical outputs across Intel, Apple Silicon, and ARM servers
- Complete environment snapshots for research validation and replication studies
- Guaranteed reproducibility for regulatory compliance and peer review
- HPC cluster compatibility for research computing without root access

## 📋 Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Contributing Process](#contributing-process)
- [Coding Standards](#coding-standards)
- [Testing Guidelines](#testing-guidelines)
- [Documentation Standards](#documentation-standards)
- [Scientific Computing Considerations](#scientific-computing-considerations)
- [Release Process](#release-process)
- [Community Guidelines](#community-guidelines)

## 🤝 Code of Conduct

This project and everyone participating in it is governed by our [Code of Conduct](CODE_OF_CONDUCT.md). By participating, you are expected to uphold this code. Please report unacceptable behavior to [zaphodbeeblebrox3rd@users.noreply.github.com](mailto:zaphodbeeblebrox3rd@users.noreply.github.com).

## 🚀 Getting Started

### Prerequisites

- Python 3.9 or higher
- Docker, Apptainer, Singularity, or Podman
- Git
- Basic understanding of containerization concepts
- Familiarity with scientific computing workflows (recommended)

### Quick Start

1. **Fork the repository** on GitHub
2. **Clone your fork** locally:
   ```bash
   git clone https://github.com/YOUR_USERNAME/venvoy.git
   cd venvoy
   ```
3. **Set up the development environment** (see [Development Setup](#development-setup))
4. **Create a feature branch**:
   ```bash
   git checkout -b feature/your-feature-name
   ```

## 🛠️ Development Setup

### 1. Install Dependencies

```bash
# Install development dependencies
pip install -e ".[dev]"

# Or using the Makefile
make install-dev
```

### 2. Set Up Pre-commit Hooks

```bash
# Install pre-commit hooks
make install-dev

# Or manually
pre-commit install
```

### 3. Verify Installation

```bash
# Run tests to ensure everything works
make test

# Check code formatting
make format

# Run linting
make lint
```

### 4. Development Environment

For development, you can use venvoy itself:

```bash
# Create a development environment
venvoy init --name venvoy-dev

# Run your development environment
venvoy run --name venvoy-dev
```

## 🔄 Contributing Process

### 1. Choose What to Work On

- **Issues**: Look for issues labeled `good first issue`, `help wanted`, or `bug`
- **Features**: Check the roadmap in discussions or propose new features
- **Documentation**: Help improve documentation and examples
- **Testing**: Add tests for existing functionality or edge cases

### 2. Create a Branch

```bash
# Create a descriptive branch name
git checkout -b feature/improve-hpc-detection
git checkout -b bug/fix-docker-permissions
git checkout -b docs/add-scientific-workflow-examples
```

### 3. Make Your Changes

- Write clean, readable code
- Follow our [coding standards](#coding-standards)
- Add tests for new functionality
- Update documentation as needed
- Consider [scientific computing impact](#scientific-computing-considerations)

### 4. Test Your Changes

```bash
# Run all tests
make test

# Run specific test categories
pytest tests/test_platform_detector.py -v
pytest tests/test_basic.py -v

# Test on different platforms (if possible)
# Test with different container runtimes
```

### 5. Submit a Pull Request

- Use our [Pull Request template](.github/pull_request_template.md)
- Provide a clear description of your changes
- Link to related issues
- Ensure all checks pass

## 📝 Coding Standards

### Python Code Style

We use several tools to maintain code quality:

- **Black**: Code formatting (line length: 88)
- **isort**: Import sorting
- **flake8**: Linting
- **mypy**: Type checking

```bash
# Format code
make format

# Check formatting
make lint

# Type checking
mypy src/venvoy/
```

### Code Organization

```
src/venvoy/
├── cli.py              # Command-line interface
├── core.py             # Core environment management
├── container_manager.py # Container runtime management
├── docker_manager.py   # Docker-specific operations
├── platform_detector.py # Cross-platform detection
└── templates/          # Dockerfile templates
```

### Naming Conventions

- **Functions**: `snake_case`
- **Classes**: `PascalCase`
- **Constants**: `UPPER_SNAKE_CASE`
- **Files**: `snake_case.py`

### Documentation

- Use docstrings for all public functions and classes
- Follow Google-style docstrings
- Include type hints for all function parameters and return values

```python
def create_environment(
    name: str, 
    python_version: str = "3.11",
    runtime: str = "python"
) -> bool:
    """Create a new venvoy environment.
    
    Args:
        name: The name of the environment to create
        python_version: Python version to use (default: "3.11")
        runtime: Runtime type ("python" or "r")
        
    Returns:
        True if environment was created successfully
        
    Raises:
        RuntimeError: If environment already exists
    """
```

## 🧪 Testing Guidelines

### Test Structure

```
tests/
├── __init__.py
├── test_basic.py           # Basic functionality tests
├── test_platform_detector.py # Platform detection tests
└── conftest.py            # Test configuration
```

### Writing Tests

- **Unit tests**: Test individual functions and methods
- **Integration tests**: Test component interactions
- **Platform tests**: Test cross-platform compatibility
- **Container tests**: Test different container runtimes

### Test Examples

```python
def test_platform_detection():
    """Test platform detection functionality."""
    detector = PlatformDetector()
    platform = detector.detect_platform()
    
    assert platform.system in ["linux", "darwin", "windows"]
    assert platform.architecture in ["x86_64", "arm64", "arm32"]

def test_container_runtime_detection():
    """Test container runtime detection."""
    manager = ContainerManager()
    runtime = manager.detect_runtime()
    
    assert runtime in [
        ContainerRuntime.DOCKER,
        ContainerRuntime.APPTAINER,
        ContainerRuntime.SINGULARITY,
        ContainerRuntime.PODMAN
    ]
```

### Running Tests

```bash
# Run all tests
make test

# Run with coverage
pytest tests/ --cov=src/venvoy --cov-report=html

# Run specific test file
pytest tests/test_platform_detector.py -v

# Run tests in parallel
pytest tests/ -n auto
```

## 📚 Documentation Standards

### README Updates

- Keep the README current with new features
- Update installation instructions if needed
- Add examples for new functionality
- Maintain the scientific computing focus

### Code Documentation

- Document all public APIs
- Include usage examples
- Explain scientific computing implications
- Document cross-platform considerations

### Example Documentation

```python
def export_environment(
    name: str, 
    format: str = "yaml",
    output: Optional[str] = None
) -> str:
    """Export environment for scientific reproducibility.
    
    This function creates a complete snapshot of the environment
    that can be shared with collaborators or used for peer review.
    The exported environment ensures identical results across
    different platforms and architectures.
    
    Args:
        name: Environment name to export
        format: Export format ("yaml", "dockerfile", "tarball", "archive")
        output: Output file path (optional)
        
    Returns:
        Path to the exported file
        
    Examples:
        >>> export_environment("my-research", "archive")
        "my-research-20240101_120000.tar.gz"
        
    Note:
        The "archive" format creates a comprehensive binary archive
        suitable for long-term scientific reproducibility and
        regulatory compliance.
    """
```

## 🔬 Scientific Computing Considerations

### Reproducibility First

All changes should maintain or improve scientific reproducibility:

- **Version Pinning**: Ensure exact package versions are preserved
- **Cross-Platform**: Test on multiple architectures (x86_64, ARM64)
- **Container Runtimes**: Support Docker, Apptainer, Singularity, Podman
- **HPC Compatibility**: Consider research computing environments

### Research Workflow Impact

Consider how changes affect:

- **Peer Review**: Can reviewers reproduce results?
- **Collaboration**: Do environments work across institutions?
- **Long-term Storage**: Will environments work years later?
- **Regulatory Compliance**: Meet FDA, clinical trial requirements?

### Testing Scientific Workflows

```bash
# Test Python scientific workflow
venvoy init --runtime python --name test-scientific
venvoy run --name test-scientific
# Inside container:
pip install numpy scipy pandas matplotlib
python -c "import numpy; print(numpy.__version__)"

# Test R statistical workflow
venvoy init --runtime r --name test-r-stats
venvoy run --name test-r-stats
# Inside container:
install.packages(c("survival", "meta"))
R -e "packageVersion('survival')"

# Test cross-platform export/import
venvoy export --name test-scientific --format archive
# Test import on different system
venvoy import test-scientific-*.tar.gz --format archive
```

## 🚀 Release Process

### Version Numbering

We follow [Semantic Versioning](https://semver.org/):

- **MAJOR**: Breaking changes
- **MINOR**: New features (backward compatible)
- **PATCH**: Bug fixes (backward compatible)

### Release Checklist

- [ ] Update version in `pyproject.toml`
- [ ] Update CHANGELOG.md
- [ ] Run full test suite
- [ ] Test on multiple platforms
- [ ] Test with different container runtimes
- [ ] Update documentation
- [ ] Create release notes

### Creating a Release

```bash
# Update version
# Edit pyproject.toml

# Run tests
make test

# Build and publish
make publish

# Create GitHub release
# Tag the release
git tag v0.1.1
git push origin v0.1.1
```

## 👥 Community Guidelines

### Getting Help

- **GitHub Discussions**: For questions and general discussion
- **Issues**: For bug reports and feature requests
- **Pull Requests**: For code contributions
- **Email**: For security issues or Code of Conduct violations

### Communication

- **Be respectful**: Follow our Code of Conduct
- **Be constructive**: Provide helpful feedback
- **Be patient**: Maintainers are volunteers
- **Be specific**: Provide clear, detailed information

### Recognition

Contributors are recognized in:

- **README**: Listed in acknowledgments
- **Release Notes**: Mentioned for significant contributions
- **GitHub**: Appear in contributor graphs

## 🎯 Types of Contributions

### Code Contributions

- **Bug fixes**: Fix issues and improve stability
- **Features**: Add new functionality
- **Performance**: Optimize existing code
- **Refactoring**: Improve code structure

### Documentation

- **README updates**: Keep documentation current
- **Code comments**: Improve code readability
- **Examples**: Add usage examples
- **Tutorials**: Create learning materials

### Testing

- **Unit tests**: Test individual components
- **Integration tests**: Test system interactions
- **Platform tests**: Test cross-platform compatibility
- **Performance tests**: Benchmark improvements

### Community

- **Issue triage**: Help categorize and prioritize issues
- **Code review**: Review pull requests
- **Mentoring**: Help new contributors
- **Advocacy**: Promote the project

## 🔧 Development Tools

### Recommended Tools

- **IDE**: Cursor (AI-first) or VSCode with Python extensions
- **Terminal**: Modern terminal with good shell support
- **Git**: Latest version with good merge conflict resolution
- **Docker**: For container testing

### Useful Commands

```bash
# Development workflow
make install-dev    # Install development dependencies
make test          # Run tests
make format        # Format code
make lint          # Check code quality
make clean         # Clean build artifacts

# venvoy-specific
venvoy runtime-info  # Check container runtime
venvoy list         # List environments
venvoy --help       # Get help
```

## 📞 Contact

- **Maintainer**: [zaphodbeeblebrox3rd](https://github.com/zaphodbeeblebrox3rd)
- **Email**: [zaphodbeeblebrox3rd@users.noreply.github.com](mailto:zaphodbeeblebrox3rd@users.noreply.github.com)
- **Discussions**: [GitHub Discussions](https://github.com/zaphodbeeblebrox3rd/venvoy/discussions)
- **Issues**: [GitHub Issues](https://github.com/zaphodbeeblebrox3rd/venvoy/issues)

## 🙏 Thank You

Thank you for contributing to venvoy! Your contributions help advance scientific reproducibility and make research more accessible to the global scientific community. Together, we're building tools that enable researchers to share exact computational environments and ensure their work can be reproduced years later.

---

*This contributing guide is a living document. Please suggest improvements through issues or pull requests.*
