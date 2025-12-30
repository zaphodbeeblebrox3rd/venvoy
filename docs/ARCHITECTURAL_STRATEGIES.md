# Architectural Strategies for Scientific Reproducibility

This document provides detailed strategies to eliminate or minimize the impact of CPU architecture differences on computational reproducibility. While venvoy ensures identical software environments across platforms, hardware-level differences in floating-point operations, BLAS/LAPACK implementations, and compiler optimizations can still affect numerical results.

## Overview

CPU architecture differences (x86_64 vs ARM64) can cause small numerical variations in:
- Matrix operations (BLAS/LAPACK backends)
- Floating-point accumulation
- Trigonometric and transcendental functions
- Compiler-optimized mathematical operations

These differences are typically in the last 2-4 decimal places and are inherent to the hardware. The strategies below help minimize their impact on scientific reproducibility.

## Strategy 1: Use Explicit Precision Types

**Problem**: Default floating-point types may vary between platforms or operations.

**Solution**: Always explicitly specify precision types in NumPy and other numerical libraries.

```python
import numpy as np

# ❌ Avoid: Implicit precision
A = np.random.rand(100, 100)  # May default to float64 or float32

# ✅ Good: Explicit precision
A = np.random.rand(100, 100).astype(np.float64)
B = np.array([1.0, 2.0, 3.0], dtype=np.float64)

# For critical calculations, consider float32 for consistency
# (though float64 is generally preferred for precision)
A = np.random.rand(100, 100).astype(np.float32)
```

**Best Practices**:
- Use `np.float64` for most scientific computing (IEEE 754 double precision)
- Use `np.float32` only when memory constraints require it
- Document precision choices in your code comments
- Set precision at array creation, not after operations

## Strategy 2: Set Tolerances for Comparisons and Document Them

**Problem**: Exact equality comparisons fail due to floating-point representation differences, and without documented tolerances, it's unclear whether differences are acceptable.

**Solution**: Use tolerance-based comparisons that account for numerical precision, and explicitly document expected precision bounds in your code and documentation.

### Using Tolerance-Based Comparisons

```python
import numpy as np

# ❌ Avoid: Exact equality
assert result == expected  # Will fail due to floating-point differences

# ✅ Good: Tolerance-based comparison
np.testing.assert_allclose(result, expected, rtol=1e-10, atol=1e-12)

# For unit tests
def test_matrix_multiplication():
    A = np.random.rand(50, 50).astype(np.float64)
    B = np.random.rand(50, 50).astype(np.float64)
    C = A @ B
    
    # Use appropriate tolerances based on your problem
    expected = compute_expected_result(A, B)
    np.testing.assert_allclose(C, expected, rtol=1e-10, atol=1e-12)
```

**Choosing Tolerances**:
- **rtol (relative tolerance)**: For values that scale with magnitude
  - `rtol=1e-10` for well-conditioned problems
  - `rtol=1e-6` for ill-conditioned problems
- **atol (absolute tolerance)**: For values near zero
  - `atol=1e-12` for double precision
  - `atol=1e-6` for single precision

**Example**:
```python
# For large values, use relative tolerance
result = 1e10 * some_calculation()
expected = 1e10 * expected_calculation()
np.testing.assert_allclose(result, expected, rtol=1e-10)

# For values near zero, use absolute tolerance
result = 1e-15 * some_calculation()
expected = 1e-15 * expected_calculation()
np.testing.assert_allclose(result, expected, atol=1e-20)
```

### Documenting Tolerances

Document your tolerance choices in code comments, docstrings, and project documentation:

```python
"""
Matrix multiplication with documented tolerance.

Expected precision:
- Relative tolerance: 1e-10 (for well-conditioned matrices)
- Absolute tolerance: 1e-12 (for near-zero elements)
- Architecture-dependent differences: Last 2-4 decimal places acceptable
"""

def matrix_multiply(A, B, rtol=1e-10, atol=1e-12):
    """
    Multiply matrices A and B with documented precision.
    
    Parameters
    ----------
    A, B : np.ndarray
        Input matrices (float64)
    rtol : float
        Relative tolerance for validation (default: 1e-10)
    atol : float
        Absolute tolerance for validation (default: 1e-12)
    
    Returns
    -------
    C : np.ndarray
        Product matrix
        
    Notes
    -----
    Results may differ in the last 2-4 decimal places between
    x86_64 and ARM64 architectures due to BLAS implementation
    differences. These differences are expected and acceptable.
    """
    C = A @ B
    return C
```

**In Project Documentation** (README, papers, etc.):
```markdown
## Numerical Precision

This analysis uses double-precision floating-point arithmetic (float64).
Expected numerical tolerances:
- Matrix operations: rtol=1e-10, atol=1e-12
- Accumulation operations: rtol=1e-12
- Architecture-dependent variations: Last 2-4 decimal places

Results validated on both x86_64 and ARM64 architectures.
```

## Strategy 3: Pin Your BLAS/LAPACK Backend

**Problem**: Different platforms use different BLAS/LAPACK implementations (Accelerate on macOS, OpenBLAS on Linux), causing matrix operation differences.

**Solution**: Explicitly install and configure the same BLAS/LAPACK backend across all platforms.

### Using Conda/Mamba (Recommended)

```bash
# In your venvoy environment or requirements
conda install -c conda-forge "libblas=*=*openblas*" "liblapack=*=*openblas*"
```

### Using NumPy Configuration

```python
import numpy as np

# Check which BLAS is currently being used
print(np.show_config())

# Note: For deterministic results, also set OPENBLAS_NUM_THREADS=1
# (see Strategy 5: Use Deterministic Algorithms)
```

### In Your venvoy Environment

Add to your `requirements.txt` or environment YAML:

```yaml
# environment.yaml
dependencies:
  - numpy
  - scipy
  - openblas  # Explicitly request OpenBLAS
  - libblas=*=*openblas*
  - liblapack=*=*openblas*
```

### Verification

```python
import numpy as np

# Verify BLAS backend
config = np.show_config()
print(config)

# Test consistency
np.random.seed(42)
A = np.random.rand(100, 100).astype(np.float64)
B = np.random.rand(100, 100).astype(np.float64)
C = A @ B
print(f"Matrix multiplication result[0,0]: {C[0,0]:.17f}")
```

## Strategy 4: Avoid Extended Precision Accumulation

**Problem**: x86_64 processors can use 80-bit extended precision in some operations, leading to different accumulation patterns than ARM64.

**Solution**: Use specialized summation functions that provide consistent results.

```python
import math
import numpy as np

# ❌ Avoid: Naive accumulation
result = 0.0
for i in range(1000000):
    result += 0.1
# Result may differ between architectures

# ✅ Good: Use math.fsum() for exact summation
values = [0.1] * 1000000
result = math.fsum(values)

# ✅ Good: Use NumPy's sum (more consistent)
values = np.array([0.1] * 1000000, dtype=np.float64)
result = np.sum(values)

# ✅ Best: Kahan summation for maximum precision
def kahan_sum(values):
    """Kahan summation algorithm for high-precision accumulation."""
    s = 0.0
    c = 0.0  # Compensation for lost low-order bits
    for value in values:
        y = value - c
        t = s + y
        c = (t - s) - y
        s = t
    return s

result = kahan_sum([0.1] * 1000000)
```

**When to Use Each**:
- **`math.fsum()`**: For Python lists, provides exact rounding
- **`np.sum()`**: For NumPy arrays, generally consistent across platforms
- **Kahan summation**: For critical calculations requiring maximum precision

## Strategy 5: Use Deterministic Algorithms

**Problem**: Non-deterministic operations (GPU, hash-based operations) can vary between runs.

**Solution**: Disable non-deterministic features and set random seeds consistently.

```python
import numpy as np
import random
import os

# Set seeds for reproducibility
np.random.seed(42)
random.seed(42)
os.environ['PYTHONHASHSEED'] = '0'  # For hash-based operations

# Disable GPU non-determinism (if using TensorFlow/PyTorch)
# TensorFlow
import tensorflow as tf
tf.random.set_seed(42)
os.environ['TF_DETERMINISTIC_OPS'] = '1'
os.environ['TF_CUDNN_DETERMINISTIC'] = '1'

# PyTorch
import torch
torch.manual_seed(42)
torch.backends.cudnn.deterministic = True
torch.backends.cudnn.benchmark = False

# NumPy threading (can cause non-determinism)
os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['MKL_NUM_THREADS'] = '1'
os.environ['NUMEXPR_NUM_THREADS'] = '1'
os.environ['OMP_NUM_THREADS'] = '1'
```

**Best Practices**:
- Set all random seeds at the start of your script
- Document seed values in your code and publications
- Use the same seed across all architectures for comparison
- Disable GPU non-deterministic operations when possible

## Strategy 6: Run Validation Tests Across Architectures

**Problem**: Architecture-specific issues may not be discovered until deployment.

**Solution**: Include cross-architecture validation in your testing pipeline.

### Unit Tests with Tolerance

```python
import numpy as np
import pytest

class TestCrossArchitecture:
    """Tests that validate consistency across architectures."""
    
    def test_matrix_operations(self):
        """Test matrix operations with appropriate tolerances."""
        np.random.seed(42)
        A = np.random.rand(50, 50).astype(np.float64)
        B = np.random.rand(50, 50).astype(np.float64)
        
        # Expected result (computed on reference architecture)
        expected = np.array([[...]])  # Your expected values
        
        # Actual computation
        result = A @ B
        
        # Tolerance-based assertion
        np.testing.assert_allclose(
            result, expected, 
            rtol=1e-10, atol=1e-12,
            err_msg="Matrix multiplication differs beyond tolerance"
        )
    
    def test_accumulation(self):
        """Test accumulation operations."""
        values = np.linspace(0, 1, 10000, dtype=np.float64)
        result = np.sum(values)
        
        # Expected: sum of arithmetic series
        expected = 10000 * (0 + 1) / 2
        
        np.testing.assert_allclose(
            result, expected,
            rtol=1e-12, atol=1e-15
        )
```

### CI/CD Integration

```yaml
# .github/workflows/test-architectures.yml
name: Cross-Architecture Tests

on: [push, pull_request]

jobs:
  test-x86_64:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Run tests
        run: |
          python -m pytest tests/ -v
          python tests/validate_numerical_precision.py > results_x86_64.txt
  
  test-arm64:
    runs-on: [self-hosted, linux, ARM64]
    steps:
      - uses: actions/checkout@v2
      - name: Run tests
        run: |
          python -m pytest tests/ -v
          python tests/validate_numerical_precision.py > results_arm64.txt
      - name: Compare results
        run: |
          python tests/compare_architectures.py results_x86_64.txt results_arm64.txt
```

### Validation Script

```python
# validate_numerical_precision.py
"""Validate numerical precision across architectures."""

import numpy as np
import json

def run_validation_tests():
    """Run a suite of numerical tests."""
    np.random.seed(42)
    results = {}
    
    # Test 1: Matrix multiplication
    A = np.random.rand(100, 100).astype(np.float64)
    B = np.random.rand(100, 100).astype(np.float64)
    C = A @ B
    results['matrix_mult'] = {
        'C[0,0]': float(C[0,0]),
        'C[50,50]': float(C[50,50])
    }
    
    # Test 2: SVD
    U, s, Vt = np.linalg.svd(A)
    results['svd'] = {
        'first_singular': float(s[0]),
        'last_singular': float(s[-1])
    }
    
    # Test 3: Accumulation
    values = np.linspace(0, 1, 100000, dtype=np.float64)
    results['accumulation'] = {
        'sum': float(np.sum(values))
    }
    
    return results

if __name__ == '__main__':
    results = run_validation_tests()
    print(json.dumps(results, indent=2))
```

## Strategy 7: Consider Fixed-Point or Arbitrary Precision

**Problem**: For some applications, floating-point differences are unacceptable.

**Solution**: Use fixed-point arithmetic or arbitrary-precision libraries when exact reproducibility is required.

### Using Python's `decimal` Module

```python
from decimal import Decimal, getcontext

# Set precision
getcontext().prec = 50  # 50 decimal places

# Use Decimal for exact calculations
a = Decimal('0.1')
b = Decimal('0.2')
c = a + b
print(c)  # Exactly 0.3, not 0.30000000000000004

# For scientific calculations
result = Decimal('1.0') / Decimal('3.0')
print(result)  # Exact representation
```

### Using `mpmath` for Arbitrary Precision

```python
from mpmath import mp

# Set precision (in bits or decimal places)
mp.dps = 50  # 50 decimal places

# All operations use arbitrary precision
a = mp.mpf('0.1')
b = mp.mpf('0.2')
c = a + b
print(c)  # Exactly 0.3

# Matrix operations with arbitrary precision
import mpmath
A = mpmath.randmatrix(10, 10)
B = mpmath.randmatrix(10, 10)
C = A * B  # Exact matrix multiplication
```

### When to Use Each

- **`decimal.Decimal`**: Financial calculations, exact decimal arithmetic
- **`mpmath`**: High-precision scientific computing, symbolic math
- **Standard float64**: Most scientific computing (with tolerance-based comparisons)

**Trade-offs**:
- Arbitrary precision is **much slower** than native floating-point
- Use only when exact reproducibility is more important than performance
- Consider hybrid approaches: use arbitrary precision for critical steps only

## Implementation Checklist

When setting up a new project for cross-architecture reproducibility:

- [ ] Use explicit `np.float64` or `np.float32` types
- [ ] Replace all `==` comparisons with `np.allclose()` or `np.testing.assert_allclose()`
- [ ] Pin BLAS/LAPACK backend (prefer OpenBLAS via conda)
- [ ] Use `math.fsum()` or `np.sum()` for accumulation instead of loops
- [ ] Document expected tolerances in code comments and documentation
- [ ] Set random seeds (`np.random.seed()`, `PYTHONHASHSEED`)
- [ ] Disable GPU non-determinism if using TensorFlow/PyTorch
- [ ] Set thread limits (`OPENBLAS_NUM_THREADS=1`, etc.)
- [ ] Create cross-architecture validation tests
- [ ] Run tests on both x86_64 and ARM64 before publication
- [ ] Consider `decimal` or `mpmath` only if exact reproducibility is required

## Example: Complete Setup

```python
"""
Complete setup for cross-architecture reproducibility.
"""

import numpy as np
import os
import random

# 1. Set seeds
SEED = 42
np.random.seed(SEED)
random.seed(SEED)
os.environ['PYTHONHASHSEED'] = '0'

# 2. Disable threading for determinism
os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['MKL_NUM_THREADS'] = '1'
os.environ['NUMEXPR_NUM_THREADS'] = '1'
os.environ['OMP_NUM_THREADS'] = '1'

# 3. Define tolerances
RTOL = 1e-10  # Relative tolerance
ATOL = 1e-12  # Absolute tolerance

# 4. Use explicit precision
def create_matrix(n, dtype=np.float64):
    """Create random matrix with explicit precision."""
    return np.random.rand(n, n).astype(dtype)

# 5. Use tolerance-based comparisons
def validate_result(result, expected, rtol=RTOL, atol=ATOL):
    """Validate result with appropriate tolerances."""
    np.testing.assert_allclose(result, expected, rtol=rtol, atol=atol)

# 6. Example computation
A = create_matrix(100)
B = create_matrix(100)
C = A @ B  # Matrix multiplication

# Validate (with expected computed on reference architecture)
# expected = compute_expected(A, B)
# validate_result(C, expected)
```

## Additional Resources

- [ARCHITECTURAL_DIFFERENCE_EXAMPLES.md](./ARCHITECTURAL_DIFFERENCE_EXAMPLES.md) - Real-world examples of architectural differences
- [NumPy Documentation on Floating Point](https://numpy.org/doc/stable/user/basics.types.html#floating-point-numbers)
- [IEEE 754 Standard](https://en.wikipedia.org/wiki/IEEE_754) - Floating-point arithmetic standard
- [BLAS/LAPACK Documentation](https://www.netlib.org/blas/) - Linear algebra libraries

## Summary

While venvoy ensures identical software environments, hardware-level differences are inevitable. By following these strategies:

1. **Explicit precision** ensures consistent data types
2. **Tolerance-based comparisons and documentation** account for numerical differences and set clear expectations
3. **Pinned BLAS/LAPACK** standardizes matrix operations
4. **Proper accumulation** avoids precision loss
5. **Deterministic algorithms** eliminate randomness
6. **Cross-architecture testing** validates consistency
7. **Arbitrary precision** provides exact reproducibility when needed

You can achieve reproducible scientific results across different CPU architectures while maintaining practical performance.



