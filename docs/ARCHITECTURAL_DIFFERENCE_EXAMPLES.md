# Architectural Difference Examples

This document provides real-world examples that demonstrate how computational results can differ between x86_64 and ARM64 architectures, even when using the same code and seed values.

## Understanding the Differences

While modern scientific libraries like NumPy are designed for cross-platform reproducibility, there are still cases where architectural differences can lead to different numerical results:

- **BLAS/LAPACK backends**: macOS uses Accelerate, Linux often uses OpenBLAS
- **Floating-point precision**: x86_64 can use 80-bit extended precision in some cases
- **Compiler optimizations**: Different code generation can affect intermediate calculations
- **Math library implementations**: Different implementations of trigonometric and other functions

## Example 1: BLAS/LAPACK Backend Differences

The most common source of differences is the underlying BLAS/LAPACK library used for matrix operations. macOS uses Accelerate, while Linux typically uses OpenBLAS.

```python
import numpy as np

# Set seed for reproducibility
np.random.seed(42)

# Create a matrix that can expose numerical differences
A = np.random.rand(100, 100).astype(np.float64)
B = np.random.rand(100, 100).astype(np.float64)

# Matrix multiplication - uses BLAS backend
C = A @ B

# Check the last few digits of a specific element
print(f"Element [0,0]: {C[0,0]}")
print(f"Full precision: {C[0,0]:.17f}")

# Try eigenvalue decomposition (uses LAPACK)
eigenvals = np.linalg.eig(A)[0]
print(f"First eigenvalue: {eigenvals[0]:.17f}")
```

**Expected difference**: The last few decimal places may differ between architectures due to different BLAS implementations.

## Example 2: Extended Precision Accumulation

x86_64 processors can use 80-bit extended precision in some floating-point operations, which can lead to different accumulation patterns.

```python
import numpy as np

# Accumulate many small floating-point operations
result = 0.0
for i in range(1000000):
    result += 0.1

# The "exact" result should be 100000.0
# But floating-point errors accumulate differently
print(f"Accumulated result: {result:.17f}")
print(f"Difference from expected: {abs(result - 100000.0):.2e}")

# More complex: summing a series
series_sum = sum(1.0 / (i+1) for i in range(100000))
print(f"Series sum: {series_sum:.17f}")
```

**Expected difference**: Small differences in the last few decimal places due to different precision handling.

## Example 3: Trigonometric Functions with Large Inputs

Different math library implementations can produce slightly different results for trigonometric functions, especially with very large inputs.

```python
import numpy as np
import math

# Large angles - precision differences can show up
large_angle = 1e15
result_sin = math.sin(large_angle)
result_cos = math.cos(large_angle)

print(f"sin(1e15): {result_sin:.17f}")
print(f"cos(1e15): {result_cos:.17f}")

# NumPy version
result_np_sin = np.sin(large_angle)
print(f"np.sin(1e15): {result_np_sin:.17f}")
```

**Expected difference**: Last few decimal places may differ due to different reduction algorithms.

## Example 4: Check Your BLAS Backend

This example helps identify which BLAS backend is being used, which is often the source of differences.

```python
import numpy as np

# Check which BLAS is being used
print("NumPy configuration:")
print(np.show_config())

# Or check directly
try:
    import numpy.core._multiarray_umath as m
    print(f"\nBLAS info: {m.__config__.blas_opt_info}")
except:
    pass
```

**Expected difference**: Different backends will be reported (Accelerate on macOS, OpenBLAS on Linux).

## Example 5: Floating-Point Edge Cases

Operations that expose precision differences and accumulation errors.

```python
import numpy as np

# Operations that can expose precision differences
a = np.float64(0.1)
b = np.float64(0.2)
c = np.float64(0.3)

# This should be True, but might differ in last bits
result = (a + b) == c
print(f"0.1 + 0.2 == 0.3: {result}")
print(f"0.1 + 0.2 = {(a + b):.17f}")
print(f"0.3 = {c:.17f}")

# Multiple operations that accumulate errors
x = np.float64(1.0)
for i in range(1000):
    x = x * 1.0001 - 0.0001

print(f"Accumulated x: {x:.17f}")
```

**Expected difference**: Small differences in the last decimal places due to different rounding behavior.

## Example 6: Large Matrix Operations (Most Likely to Show Differences)

This is the most reliable example for demonstrating architectural differences, as it stresses the BLAS/LAPACK backend.

```python
import numpy as np

np.random.seed(42)
# Large matrix operations that stress BLAS
A = np.random.rand(500, 500)
B = np.random.rand(500, 500)

# Matrix multiplication
C = A @ B
print(f"C[0,0] = {C[0,0]:.17f}")

# SVD decomposition (uses LAPACK)
U, s, Vt = np.linalg.svd(A)
print(f"First singular value: {s[0]:.17f}")

# Matrix inverse
A_inv = np.linalg.inv(A)
print(f"A_inv[0,0] = {A_inv[0,0]:.17f}")
```

**Expected difference**: The last few decimal places of these results are most likely to differ between x86_64 and ARM64 due to different BLAS/LAPACK implementations.

## Running These Examples

1. **On x86_64 machine**:
   ```bash
   python architectural_examples.py > results_x86_64.txt
   ```

2. **On ARM64 machine (M1 Mac)**:
   ```bash
   python architectural_examples.py > results_arm64.txt
   ```

3. **Compare results**:
   ```bash
   diff results_x86_64.txt results_arm64.txt
   ```

## What to Expect

- **Most differences** will be in the last 2-4 decimal places
- **BLAS operations** (matrix multiplication, SVD, etc.) are most likely to differ
- **Simple operations** (like NumPy's RNG) are designed to be identical
- **Differences are typically very small** (often < 1e-15 relative error)

## Why These Differences Matter

For scientific reproducibility:

1. **Use tolerance-based comparisons** instead of exact equality
   ```python
   # Instead of:
   assert result == expected
   
   # Use:
   np.testing.assert_allclose(result, expected, rtol=1e-10)
   ```

2. **Document the architecture** used for published results
3. **Test on target architecture** before finalizing results
4. **Use same architecture** when bit-for-bit reproducibility is required

## Notes

- Modern libraries like NumPy are well-designed for cross-platform consistency
- Most differences are very small and may not affect practical results
- The differences are inherent to the hardware and cannot be eliminated by containerization
- Venvoy standardizes the software environment but cannot eliminate hardware-level differences

