"""
Quick test to verify DataComPy 0.19.2 works correctly
"""

import pandas as pd
from datacompy.core import Compare

# Create test dataframes
df1 = pd.DataFrame({
    'id': [1, 2, 3],
    'value': [10.0, 20.0, 30.0],
    'category': ['A', 'B', 'C']
})

df2 = pd.DataFrame({
    'id': [1, 2, 3],
    'value': [10.0, 20.1, 30.0],  # Small difference
    'category': ['A', 'B', 'C']
})

print("Testing DataComPy 0.19.2...")
print(f"DataComPy version: {pd.__version__}")

# Test 1: Identical dataframes
df_identical = df1.copy()
compare_identical = Compare(
    df1,
    df_identical,
    join_columns='id',
    abs_tol=0.0001,
    df1_name='Original',
    df2_name='Copy'
)

print("\n" + "="*60)
print("TEST 1: Identical DataFrames")
print("="*60)
print(f"Matches: {compare_identical.matches()}")
print(f"Expected: True")
assert compare_identical.matches() == True, "Identical dataframes should match!"
print("✓ PASS")

# Test 2: Different dataframes (within tolerance)
compare_within_tol = Compare(
    df1,
    df2,
    join_columns='id',
    abs_tol=0.2,  # Tolerance of 0.2
    rel_tol=0.0,
    df1_name='Original',
    df2_name='Modified'
)

print("\n" + "="*60)
print("TEST 2: DataFrames Within Tolerance")
print("="*60)
print(f"Matches: {compare_within_tol.matches()}")
print(f"Expected: True (difference 0.1 < tolerance 0.2)")
assert compare_within_tol.matches() == True, "Should match within tolerance!"
print("✓ PASS")

# Test 3: Different dataframes (outside tolerance)
compare_outside_tol = Compare(
    df1,
    df2,
    join_columns='id',
    abs_tol=0.05,  # Strict tolerance
    rel_tol=0.0,
    df1_name='Original',
    df2_name='Modified'
)

print("\n" + "="*60)
print("TEST 3: DataFrames Outside Tolerance")
print("="*60)
print(f"Matches: {compare_outside_tol.matches()}")
print(f"Expected: False (difference 0.1 > tolerance 0.05)")
assert compare_outside_tol.matches() == False, "Should NOT match outside tolerance!"
print("✓ PASS")

# Test 4: Show report
print("\n" + "="*60)
print("TEST 4: Full Report")
print("="*60)
print(compare_outside_tol.report())

# Test 5: Check available methods
print("\n" + "="*60)
print("Available Compare methods:")
print("="*60)
methods = [m for m in dir(compare_identical) if not m.startswith('_')]
for method in methods[:10]:  # Show first 10
    print(f"  - {method}")

print("\n" + "="*60)
print("ALL TESTS PASSED! ✓")
print("="*60)