# Publishing venvoy to PyPI

This document explains how to publish venvoy to PyPI (Python Package Index).

## Prerequisites

1. **PyPI Account**: Create accounts on both [PyPI](https://pypi.org) and [TestPyPI](https://test.pypi.org)
2. **API Tokens**: Generate API tokens for both PyPI and TestPyPI
3. **Python 3.9+**: Required for building and publishing

## Setup

### 1. Create PyPI Accounts

- **PyPI**: https://pypi.org/account/register/
- **TestPyPI**: https://test.pypi.org/account/register/

### 2. Generate API Tokens

#### For PyPI:
1. Go to https://pypi.org/manage/account/token/
2. Create a new API token with scope "Entire account"
3. Copy the token (starts with `pypi-`)

#### For TestPyPI:
1. Go to https://test.pypi.org/manage/account/token/
2. Create a new API token with scope "Entire account"  
3. Copy the token (starts with `pypi-`)

### 3. Configure Credentials

#### Option A: Using .pypirc file (Recommended)
```bash
# Copy example configuration
cp .pypirc.example ~/.pypirc

# Edit with your tokens
nano ~/.pypirc
```

#### Option B: Environment Variables
```bash
export TWINE_USERNAME=__token__
export TWINE_PASSWORD=pypi-your-api-token-here
```

## Publishing Methods

### Method 1: Interactive Script (Recommended)

The interactive script provides a guided publishing experience:

```bash
# Run interactive publishing script
python scripts/publish.py
```

Features:
- ✅ Checks prerequisites automatically
- ✅ Builds and validates package
- ✅ Choice between TestPyPI, PyPI, or both
- ✅ Confirmation prompts for safety
- ✅ Clear error messages and guidance

### Method 2: Makefile Commands

#### Test on TestPyPI first:
```bash
make upload-test
```

#### Publish to production PyPI:
```bash
make upload
```

#### Check package before publishing:
```bash
make check-package
```

### Method 3: GitHub Actions (Automated)

#### Setup Trusted Publishing (Recommended)

1. **Configure PyPI Project**:
   - Go to your PyPI project settings
   - Add GitHub as a trusted publisher
   - Repository: `zaphodbeeblebrox3rd/venvoy`
   - Workflow: `publish-pypi.yml`
   - Environment: `pypi`

2. **Create GitHub Release**:
   ```bash
   # Tag and push
   git tag v0.1.0
   git push origin v0.1.0
   
   # Create release on GitHub
   # This will automatically trigger publishing
   ```

#### Manual Trigger:
```bash
# Go to GitHub Actions tab
# Select "Publish to PyPI" workflow
# Click "Run workflow"
```

### Method 4: Manual Commands

```bash
# Install build tools
pip install build twine

# Clean and build
rm -rf dist/
python -m build

# Check package
twine check dist/*

# Upload to TestPyPI
twine upload --repository testpypi dist/*

# Upload to PyPI
twine upload dist/*
```

## Publishing Checklist

Before publishing a new version:

- [ ] **Update version** in `pyproject.toml`
- [ ] **Update CHANGELOG** with new features/fixes
- [ ] **Run tests** to ensure everything works
- [ ] **Test locally** with `pip install -e .`
- [ ] **Check package** with `make check-package`
- [ ] **Test on TestPyPI** first
- [ ] **Verify installation** from TestPyPI works
- [ ] **Publish to PyPI**
- [ ] **Create GitHub release** with release notes
- [ ] **Test installation** from PyPI

## Version Management

### Semantic Versioning

venvoy follows [Semantic Versioning](https://semver.org/):

- **MAJOR** (1.0.0): Incompatible API changes
- **MINOR** (0.1.0): New functionality, backwards compatible
- **PATCH** (0.0.1): Bug fixes, backwards compatible

### Updating Version

Edit `pyproject.toml`:
```toml
[project]
version = "0.2.0"  # Update this line
```

## Testing Published Package

### From TestPyPI:
```bash
# Install from TestPyPI
pip install --index-url https://test.pypi.org/simple/ venvoy

# Test basic functionality
venvoy --help
```

### From PyPI:
```bash
# Install from PyPI
pip install venvoy

# Test basic functionality
venvoy --help
```

## Troubleshooting

### Common Issues

1. **"File already exists"**: Version already published, increment version number
2. **"Invalid credentials"**: Check API tokens in `~/.pypirc`
3. **"Package validation failed"**: Run `twine check dist/*` for details
4. **"Build failed"**: Check `pyproject.toml` configuration

### Getting Help

- **PyPI Help**: https://pypi.org/help/
- **Packaging Guide**: https://packaging.python.org/
- **Twine Documentation**: https://twine.readthedocs.io/

## Security Notes

- **Never commit API tokens** to version control
- **Use scoped tokens** when possible
- **Rotate tokens** regularly
- **Enable 2FA** on PyPI accounts
- **Use trusted publishing** for CI/CD

## Post-Publishing

After successful publishing:

1. **Verify package page**: Check https://pypi.org/project/venvoy/
2. **Test installation**: `pip install venvoy`
3. **Update documentation**: Ensure install instructions are current
4. **Announce release**: Share on relevant channels
5. **Monitor downloads**: Track adoption and usage 