# Architectural Baseline Test Suite

This directory contains a comprehensive test suite for detecting numerical differences between CPU architectures (x86_64 vs ARM64).

## Quick Start

```bash
# Run the test suite
python architectural_baseline/test_architectural_differences.py > results.txt

# Compare across architectures
diff results_x86_64.txt results_arm64.txt
```

## Documentation

For detailed information about:
- **How to use the test suite**: See `docs/ARCHITECTURAL_STRATEGIES.md` Strategy 6
- **What the tests cover**: See `docs/ARCHITECTURAL_STRATEGIES.md` Strategy 6
- **Interpreting results**: See `docs/ARCHITECTURAL_STRATEGIES.md` Strategy 6
- **Best practices**: See `docs/ARCHITECTURAL_STRATEGIES.md` Strategy 6

## Requirements

- Python 3.9+
- NumPy (will be available in venvoy environments)
- Optional: SciPy (for Simpson's rule integration test)

## Testing on the Host OS

If you need to run the test suite directly on your host OS (outside of a venvoy container), follow these steps to set up a Python virtual environment using `uv`:

### 1. Install uv

```bash
# Linux/macOS
curl -LsSf https://astral.sh/uv/install.sh | sh

# Or with pip (if you have Python already)
pip install uv

# Or with Homebrew (macOS)
brew install uv
```

After installation, restart your terminal or run `source ~/.bashrc` (or `~/.zshrc`).

### 2. Create and Activate a Virtual Environment

```bash
# Navigate to the project root
cd /path/to/venvoy

# Create a virtual environment
uv venv .venv-venvoy

# Activate the virtual environment
source .venv-venvoy/bin/activate   # Linux/macOS
# or
.venv-venvoy\Scripts\activate      # Windows
```

### 3. Install Required Packages

```bash
# Install NumPy (required)
uv pip install numpy

# Install SciPy (optional, for Simpson's rule integration test)
uv pip install scipy
```

### 4. Run the Test Suite

```bash
# Run and save results
python architectural_baseline/test_architectural_differences.py > architectural_baseline/results.txt

# Or run with full output to terminal
python architectural_baseline/test_architectural_differences.py
```

### 5. Deactivate When Done

```bash
deactivate
```

## Related Documentation

- `docs/ARCHITECTURAL_STRATEGIES.md` - Detailed strategies for minimizing architectural differences (see Strategy 6)
- `docs/ARCHITECTURAL_DIFFERENCE_EXAMPLES.md` - Examples of common differences
- `README.md` - Main venvoy documentation

