#!/usr/bin/env python3
"""
Architectural Baseline Test Suite

This script runs a comprehensive set of computations that are prone to showing
different numerical results across different CPU architectures (x86_64 vs ARM64).

The differences are typically in the last 2-4 decimal places and are due to:
- Different BLAS/LAPACK backends (Accelerate on macOS, OpenBLAS on Linux)
- Floating-point precision handling (80-bit extended precision on x86_64)
- Compiler optimizations and math library implementations
- Different accumulation patterns in floating-point operations

Usage:
    python test_architectural_differences.py > results.txt

To compare results across architectures:
    # On x86_64
    python test_architectural_differences.py > results_x86_64.txt
    
    # On ARM64
    python test_architectural_differences.py > results_arm64.txt
    
    # Compare
    diff results_x86_64.txt results_arm64.txt
"""

import sys
import platform
from typing import Dict, Any

try:
    import numpy as np
except ImportError:
    print("ERROR: NumPy is required but not installed.")
    print("Please install NumPy: pip install numpy")
    print("Or run this script inside a venvoy environment with NumPy installed.")
    sys.exit(1)


def print_header(title: str):
    """Print a formatted section header"""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)


def print_result(label: str, value: Any, precision: int = 17):
    """Print a formatted result"""
    if isinstance(value, (float, np.floating)):
        print(f"{label:40s}: {value:.{precision}f}")
    elif isinstance(value, np.ndarray):
        if value.size <= 5:
            print(f"{label:40s}: {value}")
        else:
            print(f"{label:40s}: shape={value.shape}, dtype={value.dtype}")
            print(f"{'':40s}  first={value.flat[0]:.{precision}f}, "
                  f"last={value.flat[-1]:.{precision}f}")
    else:
        print(f"{label:40s}: {value}")


def test_1_blas_matrix_multiplication():
    """Test 1: BLAS Matrix Multiplication
    
    Matrix multiplication uses the BLAS backend, which differs between
    architectures (Accelerate on macOS, OpenBLAS on Linux).
    """
    print_header("Test 1: BLAS Matrix Multiplication")
    
    np.random.seed(42)
    A = np.random.rand(100, 100).astype(np.float64)
    B = np.random.rand(100, 100).astype(np.float64)
    
    C = A @ B
    
    print_result("A @ B [0, 0]", C[0, 0])
    print_result("A @ B [50, 50]", C[50, 50])
    print_result("A @ B [99, 99]", C[99, 99])
    print_result("Sum of all elements", np.sum(C))
    print_result("Frobenius norm", np.linalg.norm(C, 'fro'))


def test_2_lapack_eigenvalue_decomposition():
    """Test 2: LAPACK Eigenvalue Decomposition
    
    Eigenvalue decomposition uses LAPACK, which can produce different
    results due to different implementations.
    """
    print_header("Test 2: LAPACK Eigenvalue Decomposition")
    
    np.random.seed(42)
    A = np.random.rand(50, 50).astype(np.float64)
    # Make symmetric for real eigenvalues
    A = (A + A.T) / 2
    
    eigenvals, eigenvecs = np.linalg.eig(A)
    eigenvals = np.sort(eigenvals)
    
    print_result("First eigenvalue (smallest)", eigenvals[0])
    print_result("Last eigenvalue (largest)", eigenvals[-1])
    print_result("Sum of eigenvalues", np.sum(eigenvals))
    print_result("First eigenvector [0]", eigenvecs[:, 0][0])


def test_3_lapack_svd():
    """Test 3: LAPACK SVD Decomposition
    
    Singular Value Decomposition is highly sensitive to numerical
    differences in the LAPACK backend.
    """
    print_header("Test 3: LAPACK SVD Decomposition")
    
    np.random.seed(42)
    A = np.random.rand(100, 50).astype(np.float64)
    
    U, s, Vt = np.linalg.svd(A, full_matrices=False)
    
    print_result("First singular value", s[0])
    print_result("Last singular value", s[-1])
    print_result("Sum of singular values", np.sum(s))
    print_result("U[0, 0]", U[0, 0])
    print_result("Vt[0, 0]", Vt[0, 0])


def test_4_matrix_inverse():
    """Test 4: Matrix Inverse
    
    Matrix inversion uses LAPACK and can show differences.
    """
    print_header("Test 4: Matrix Inverse")
    
    np.random.seed(42)
    A = np.random.rand(50, 50).astype(np.float64)
    # Make well-conditioned
    A = A + np.eye(50) * 10
    
    A_inv = np.linalg.inv(A)
    
    print_result("A_inv[0, 0]", A_inv[0, 0])
    print_result("A_inv[25, 25]", A_inv[25, 25])
    print_result("A_inv[49, 49]", A_inv[49, 49])
    print_result("Trace of A_inv", np.trace(A_inv))


def test_5_floating_point_accumulation():
    """Test 5: Floating-Point Accumulation
    
    Accumulating many floating-point operations can show differences
    due to extended precision on x86_64 vs standard precision on ARM64.
    """
    print_header("Test 5: Floating-Point Accumulation")
    
    # Simple accumulation
    result = 0.0
    for i in range(1000000):
        result += 0.1
    
    print_result("Sum of 1e6 * 0.1", result)
    print_result("Difference from 100000.0", abs(result - 100000.0))
    
    # Series summation
    series_sum = sum(1.0 / (i + 1) for i in range(100000))
    print_result("Harmonic series sum (1e5 terms)", series_sum)
    
    # Alternating series
    alt_sum = sum((-1.0) ** i / (i + 1) for i in range(100000))
    print_result("Alternating series sum (1e5 terms)", alt_sum)


def test_6_kahan_summation():
    """Test 6: Kahan Summation Algorithm
    
    Kahan summation is designed to reduce accumulation errors.
    Compare with regular summation to see differences.
    """
    print_header("Test 6: Kahan Summation vs Regular Summation")
    
    np.random.seed(42)
    values = np.random.rand(100000).astype(np.float64) * 1e-10
    
    # Regular summation
    regular_sum = np.sum(values)
    
    # Kahan summation
    kahan_sum = 0.0
    c = 0.0  # Compensation
    for val in values:
        y = val - c
        t = kahan_sum + y
        c = (t - kahan_sum) - y
        kahan_sum = t
    
    print_result("Regular sum", regular_sum)
    print_result("Kahan sum", kahan_sum)
    print_result("Difference", abs(regular_sum - kahan_sum))


def test_7_trigonometric_large_inputs():
    """Test 7: Trigonometric Functions with Large Inputs
    
    Large angle reduction can differ between math library implementations.
    """
    print_header("Test 7: Trigonometric Functions with Large Inputs")
    
    large_angle = 1e15
    
    # Standard library
    sin_std = np.sin(large_angle)
    cos_std = np.cos(large_angle)
    tan_std = np.tan(large_angle)
    
    print_result("sin(1e15)", sin_std)
    print_result("cos(1e15)", cos_std)
    print_result("tan(1e15)", tan_std)
    
    # Multiple large angles
    angles = np.array([1e10, 1e12, 1e14, 1e15], dtype=np.float64)
    results = np.sin(angles)
    print_result("sin([1e10, 1e12, 1e14, 1e15])", results)


def test_8_floating_point_edge_cases():
    """Test 8: Floating-Point Edge Cases
    
    Classic floating-point representation issues.
    """
    print_header("Test 8: Floating-Point Edge Cases")
    
    # 0.1 + 0.2 == 0.3
    a = np.float64(0.1)
    b = np.float64(0.2)
    c = np.float64(0.3)
    
    print_result("0.1 + 0.2", a + b)
    print_result("0.3", c)
    print_result("0.1 + 0.2 == 0.3", (a + b) == c)
    print_result("Difference", abs((a + b) - c))
    
    # Accumulated operations
    x = np.float64(1.0)
    for i in range(1000):
        x = x * 1.0001 - 0.0001
    
    print_result("Accumulated x (1000 iterations)", x)


def test_9_large_matrix_operations():
    """Test 9: Large Matrix Operations
    
    Large matrices stress the BLAS/LAPACK backend most effectively.
    """
    print_header("Test 9: Large Matrix Operations")
    
    np.random.seed(42)
    A = np.random.rand(500, 500).astype(np.float64)
    B = np.random.rand(500, 500).astype(np.float64)
    
    # Matrix multiplication
    C = A @ B
    print_result("Large A @ B [0, 0]", C[0, 0])
    print_result("Large A @ B [250, 250]", C[250, 250])
    print_result("Large A @ B [499, 499]", C[499, 499])
    
    # SVD on large matrix
    U, s, Vt = np.linalg.svd(A, full_matrices=False)
    print_result("Large matrix first singular value", s[0])
    print_result("Large matrix last singular value", s[-1])
    
    # Matrix inverse
    A_well_cond = A + np.eye(500) * 10
    A_inv = np.linalg.inv(A_well_cond)
    print_result("Large matrix inverse [0, 0]", A_inv[0, 0])


def test_10_numerical_integration():
    """Test 10: Numerical Integration
    
    Integration can accumulate errors differently.
    """
    print_header("Test 10: Numerical Integration")
    
    # Simple trapezoidal rule
    def f(x):
        return np.sin(x) * np.exp(-x)
    
    x = np.linspace(0, 10, 100000, dtype=np.float64)
    y = f(x)
    
    # Trapezoidal integration
    dx = x[1] - x[0]
    # Use trapezoid (NumPy 2.0+) with fallback to trapz (NumPy < 2.0)
    integral = np.trapezoid(y, x) if hasattr(np, 'trapezoid') else np.trapz(y, x)
    print_result("Trapezoidal integral of sin(x)*exp(-x)", integral)
    
    # Simpson's rule (using scipy if available, otherwise approximate)
    try:
        from scipy import integrate
        integral_simpson = integrate.simpson(y, x)
        print_result("Simpson integral of sin(x)*exp(-x)", integral_simpson)
    except ImportError:
        print_result("Simpson integral", "scipy not available")


def test_11_linear_solver():
    """Test 11: Linear System Solver
    
    Solving linear systems uses LAPACK and can show differences.
    """
    print_header("Test 11: Linear System Solver")
    
    np.random.seed(42)
    A = np.random.rand(100, 100).astype(np.float64)
    A = A + np.eye(100) * 10  # Make well-conditioned
    b = np.random.rand(100).astype(np.float64)
    
    x = np.linalg.solve(A, b)
    
    print_result("Solution x[0]", x[0])
    print_result("Solution x[50]", x[50])
    print_result("Solution x[99]", x[99])
    print_result("Residual norm", np.linalg.norm(A @ x - b))


def test_12_cholesky_decomposition():
    """Test 12: Cholesky Decomposition
    
    Cholesky decomposition is sensitive to numerical precision.
    """
    print_header("Test 12: Cholesky Decomposition")
    
    np.random.seed(42)
    A = np.random.rand(50, 50).astype(np.float64)
    # Make positive definite
    A = A @ A.T + np.eye(50) * 0.1
    
    L = np.linalg.cholesky(A)
    
    print_result("Cholesky L[0, 0]", L[0, 0])
    print_result("Cholesky L[25, 25]", L[25, 25])
    print_result("Cholesky L[49, 49]", L[49, 49])
    print_result("Reconstruction error", np.linalg.norm(L @ L.T - A))


def print_system_info():
    """Print system and NumPy configuration information"""
    print_header("System Information")
    
    print_result("Platform", platform.platform())
    print_result("Architecture", platform.machine())
    print_result("Processor", platform.processor())
    print_result("Python version", platform.python_version())
    print_result("NumPy version", np.__version__)
    
    print("\nNumPy Configuration:")
    np.show_config()
    
    # Try to get BLAS info
    try:
        import numpy.core._multiarray_umath as m
        print("\nBLAS Information:")
        print(f"  {m.__config__.blas_opt_info}")
    except Exception:
        pass


def main():
    """Run all architectural difference tests"""
    print("=" * 80)
    print("  Architectural Baseline Test Suite")
    print("  Testing computations prone to architectural differences")
    print("=" * 80)
    
    # Print system info first
    print_system_info()
    
    # Run all tests
    test_1_blas_matrix_multiplication()
    test_2_lapack_eigenvalue_decomposition()
    test_3_lapack_svd()
    test_4_matrix_inverse()
    test_5_floating_point_accumulation()
    test_6_kahan_summation()
    test_7_trigonometric_large_inputs()
    test_8_floating_point_edge_cases()
    test_9_large_matrix_operations()
    test_10_numerical_integration()
    test_11_linear_solver()
    test_12_cholesky_decomposition()
    
    print("\n" + "=" * 80)
    print("  Test Suite Complete")
    print("=" * 80)
    print("\nTo compare results across architectures:")
    print("  1. Run this script on each architecture")
    print("  2. Save output to files (e.g., results_x86_64.txt, results_arm64.txt)")
    print("  3. Compare using: diff results_x86_64.txt results_arm64.txt")
    print("\nExpected differences:")
    print("  - Most differences in last 2-4 decimal places")
    print("  - BLAS/LAPACK operations most likely to differ")
    print("  - Differences typically < 1e-15 relative error")
    print("=" * 80)


if __name__ == "__main__":
    main()

