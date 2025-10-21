#!/usr/bin/env python3
"""
Simple test runner for SKEYE Python tests.
Run from project root directory.

Usage:
    python run_python_tests.py
"""

import sys
import unittest
from pathlib import Path

# Add directories to path
project_root = Path(__file__).parent
test_unit_dir = project_root / "test" / "unit"
v2_dir = project_root / "src" / "flight-system" / "v2"

sys.path.insert(0, str(test_unit_dir))
sys.path.insert(0, str(v2_dir))

print("="*70)
print("SKEYE Flight System - Python Unit Tests")
print("="*70)
print(f"Project root: {project_root}")
print(f"Test directory: {test_unit_dir}")
print(f"V2 directory: {v2_dir}")
print()

# Discover and run tests
loader = unittest.TestLoader()
suite = loader.discover(str(test_unit_dir), pattern='test_*.py')

runner = unittest.TextTestRunner(verbosity=2)
result = runner.run(suite)

# Print summary
print("\n" + "="*70)
print("TEST SUMMARY")
print("="*70)
print(f"Tests run: {result.testsRun}")
print(f"Successes: {result.testsRun - len(result.failures) - len(result.errors)}")
print(f"Failures: {len(result.failures)}")
print(f"Errors: {len(result.errors)}")
print(f"Skipped: {len(result.skipped)}")
print("="*70)

if result.wasSuccessful():
    print("✓ ALL TESTS PASSED")
    sys.exit(0)
else:
    print("✗ SOME TESTS FAILED")
    sys.exit(1)
