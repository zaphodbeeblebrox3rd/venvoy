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

## Related Documentation

- `docs/ARCHITECTURAL_STRATEGIES.md` - Detailed strategies for minimizing architectural differences (see Strategy 6)
- `docs/ARCHITECTURAL_DIFFERENCE_EXAMPLES.md` - Examples of common differences
- `README.md` - Main venvoy documentation

