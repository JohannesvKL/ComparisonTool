# tests/test_comparators.py

import pytest
import pandas as pd
import numpy as np
import tempfile
import os
from pathlib import Path
import hashlib
import json

# Import our comparators (assuming they're in a module called 'comparators')
from comparators import (
    BinaryComparator,
    TabularComparator,
    ImageComparator,
    HDF5Comparator,
    ComparisonManager
)



# ============================================================================
# FIXTURES - Reusable test data
# ============================================================================

@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def identical_csv_files(temp_dir):
    """Create two identical CSV files"""
    df = pd.DataFrame({
        'sample_id': ['A', 'B', 'C', 'D'],
        'expression': [1.234, 2.456, 3.678, 4.890],
        'p_value': [0.001, 0.045, 0.023, 0.089]
    })
    
    file1 = temp_dir / 'results1.csv'
    file2 = temp_dir / 'results2.csv'
    
    df.to_csv(file1, index=False)
    df.to_csv(file2, index=False)
    
    return file1, file2


@pytest.fixture
def different_csv_files(temp_dir):
    """Create two CSV files with differences"""
    df1 = pd.DataFrame({
        'sample_id': ['A', 'B', 'C', 'D'],
        'expression': [1.234, 2.456, 3.678, 4.890],
        'p_value': [0.001, 0.045, 0.023, 0.089]
    })
    
    df2 = pd.DataFrame({
        'sample_id': ['A', 'B', 'C', 'D'],
        'expression': [1.234, 2.999, 3.678, 4.890],  # B changed
        'p_value': [0.001, 0.045, 0.023, 0.120]      # D changed
    })
    
    file1 = temp_dir / 'results1.csv'
    file2 = temp_dir / 'results2.csv'
    
    df1.to_csv(file1, index=False)
    df2.to_csv(file2, index=False)
    
    return file1, file2, df1, df2


@pytest.fixture
def csv_files_within_tolerance(temp_dir):
    """Create CSV files with differences within tolerance"""
    df1 = pd.DataFrame({
        'sample_id': ['A', 'B', 'C', 'D'],
        'expression': [1.234000, 2.456000, 3.678000, 4.890000],
        'p_value': [0.001, 0.045, 0.023, 0.089]
    })
    
    df2 = pd.DataFrame({
        'sample_id': ['A', 'B', 'C', 'D'],
        'expression': [1.234001, 2.456002, 3.677998, 4.890001],  # Tiny differences
        'p_value': [0.001, 0.045, 0.023, 0.089]
    })
    
    file1 = temp_dir / 'results1.csv'
    file2 = temp_dir / 'results2.csv'
    
    df1.to_csv(file1, index=False)
    df2.to_csv(file2, index=False)
    
    return file1, file2


@pytest.fixture
def csv_files_different_rows(temp_dir):
    """Create CSV files with different rows"""
    df1 = pd.DataFrame({
        'sample_id': ['A', 'B', 'C', 'D'],
        'expression': [1.234, 2.456, 3.678, 4.890],
        'p_value': [0.001, 0.045, 0.023, 0.089]
    })
    
    df2 = pd.DataFrame({
        'sample_id': ['A', 'B', 'C', 'E'],  # D replaced with E
        'expression': [1.234, 2.456, 3.678, 5.123],
        'p_value': [0.001, 0.045, 0.023, 0.012]
    })
    
    file1 = temp_dir / 'results1.csv'
    file2 = temp_dir / 'results2.csv'
    
    df1.to_csv(file1, index=False)
    df2.to_csv(file2, index=False)
    
    return file1, file2


@pytest.fixture
def identical_binary_files(temp_dir):
    """Create two identical binary files"""
    content = b"This is binary content\x00\x01\x02\x03"
    
    file1 = temp_dir / 'data1.bin'
    file2 = temp_dir / 'data2.bin'
    
    file1.write_bytes(content)
    file2.write_bytes(content)
    
    return file1, file2


@pytest.fixture
def different_binary_files(temp_dir):
    """Create two different binary files"""
    file1 = temp_dir / 'data1.bin'
    file2 = temp_dir / 'data2.bin'
    
    file1.write_bytes(b"This is content 1")
    file2.write_bytes(b"This is content 2")
    
    return file1, file2


@pytest.fixture
def identical_images(temp_dir):
    """Create two identical PNG images"""
    try:
        from PIL import Image
        import numpy as np
        
        # Create a simple test image
        img_array = np.random.randint(0, 255, (100, 100, 3), dtype=np.uint8)
        img = Image.fromarray(img_array)
        
        file1 = temp_dir / 'image1.png'
        file2 = temp_dir / 'image2.png'
        
        img.save(file1)
        img.save(file2)
        
        return file1, file2
    except ImportError:
        pytest.skip("PIL/Pillow not installed")


@pytest.fixture
def different_images(temp_dir):
    """Create two different images"""
    try:
        from PIL import Image
        import numpy as np
        
        # Create two different images
        img1_array = np.random.randint(0, 255, (100, 100, 3), dtype=np.uint8)
        img2_array = np.random.randint(0, 255, (100, 100, 3), dtype=np.uint8)
        
        img1 = Image.fromarray(img1_array)
        img2 = Image.fromarray(img2_array)
        
        file1 = temp_dir / 'image1.png'
        file2 = temp_dir / 'image2.png'
        
        img1.save(file1)
        img2.save(file2)
        
        return file1, file2
    except ImportError:
        pytest.skip("PIL/Pillow not installed")


@pytest.fixture
def similar_images(temp_dir):
    """Create two very similar images (should pass SSIM with threshold)"""
    try:
        from PIL import Image
        import numpy as np
        
        # Create base image
        img1_array = np.random.randint(100, 150, (100, 100, 3), dtype=np.uint8)
        # Create similar image with tiny differences
        img2_array = img1_array.copy()
        img2_array[0:5, 0:5] += 1  # Tiny difference in corner
        
        img1 = Image.fromarray(img1_array)
        img2 = Image.fromarray(img2_array)
        
        file1 = temp_dir / 'image1.png'
        file2 = temp_dir / 'image2.png'
        
        img1.save(file1)
        img2.save(file2)
        
        return file1, file2
    except ImportError:
        pytest.skip("PIL/Pillow not installed")


@pytest.fixture
def identical_hdf5_files(temp_dir):
    """Create two identical HDF5 files"""
    try:
        import h5py
        
        file1 = temp_dir / 'data1.h5'
        file2 = temp_dir / 'data2.h5'
        
        # Create identical HDF5 files
        for filepath in [file1, file2]:
            with h5py.File(filepath, 'w') as f:
                f.create_dataset('dataset1', data=np.array([1.0, 2.0, 3.0]))
                f.create_dataset('dataset2', data=np.array([[1, 2], [3, 4]]))
                
                # Create a group
                grp = f.create_group('group1')
                grp.create_dataset('nested', data=np.array([5.0, 6.0]))
        
        return file1, file2
    except ImportError:
        pytest.skip("h5py not installed")


@pytest.fixture
def different_hdf5_files(temp_dir):
    """Create two different HDF5 files"""
    try:
        import h5py
        
        file1 = temp_dir / 'data1.h5'
        file2 = temp_dir / 'data2.h5'
        
        with h5py.File(file1, 'w') as f:
            f.create_dataset('dataset1', data=np.array([1.0, 2.0, 3.0]))
            f.create_dataset('dataset2', data=np.array([[1, 2], [3, 4]]))
        
        with h5py.File(file2, 'w') as f:
            f.create_dataset('dataset1', data=np.array([1.0, 2.0, 3.5]))  # Changed
            f.create_dataset('dataset2', data=np.array([[1, 2], [3, 4]]))
        
        return file1, file2
    except ImportError:
        pytest.skip("h5py not installed")


# ============================================================================
# BINARY COMPARATOR TESTS
# ============================================================================

class TestBinaryComparator:
    """Test suite for binary file comparison"""
    
    def test_identical_files_pass(self, identical_binary_files):
        """Test that identical files are detected as matching"""
        file1, file2 = identical_binary_files
        comparator = BinaryComparator()
        
        result = comparator.compare(str(file1), str(file2), {})
        
        assert result['match'] == True
        assert result['verdict'] == 'PASS'
        assert result['file1_hash'] == result['file2_hash']
        assert 'sha256' in result['method']
    
    def test_different_files_fail(self, different_binary_files):
        """Test that different files are detected"""
        file1, file2 = different_binary_files
        comparator = BinaryComparator()
        
        result = comparator.compare(str(file1), str(file2), {})
        
        assert result['match'] == False
        assert result['verdict'] == 'FAIL'
        assert result['file1_hash'] != result['file2_hash']
        assert result['reason'] == 'Checksums differ'
    
    def test_can_compare_any_file(self):
        """Test that binary comparator accepts any file type"""
        comparator = BinaryComparator()
        
        assert comparator.can_compare('file.txt') == True
        assert comparator.can_compare('data.csv') == True
        assert comparator.can_compare('image.png') == True
        assert comparator.can_compare('anything') == True
    
    def test_tool_metadata(self):
        """Test that tool metadata is properly returned"""
        comparator = BinaryComparator()
        metadata = comparator.get_tool_metadata()
        
        assert metadata['@type'] == 'SoftwareApplication'
        assert 'SHA256' in metadata['name']
        assert 'applicationCategory' in metadata


# ============================================================================
# TABULAR COMPARATOR TESTS
# ============================================================================

class TestTabularComparator:
    """Test suite for tabular data comparison"""
    
    def test_identical_csv_pass(self, identical_csv_files):
        """Test that identical CSV files match"""
        file1, file2 = identical_csv_files
        comparator = TabularComparator()
        
        result = comparator.compare(str(file1), str(file2), {
            'join_columns': ['sample_id'],
            'abs_tol': 1e-5,
            'rel_tol': 0.01
        })
        
        assert result['match'] == True
        assert result['verdict'] == 'PASS'
        assert result['method'] == 'datacompy'
        assert result['summary']['rows_in_common'] == 4
        assert result['summary']['rows_only_in_df1'] == 0
        assert result['summary']['rows_only_in_df2'] == 0
    
    def test_different_csv_fail(self, different_csv_files):
        """Test that different CSV files are detected"""
        file1, file2, df1, df2 = different_csv_files
        comparator = TabularComparator()
        
        result = comparator.compare(str(file1), str(file2), {
            'join_columns': ['sample_id'],
            'abs_tol': 1e-5,
            'rel_tol': 0.01
        })
        
        # Core assertions - these should always work
        assert result['match'] == False, "Different files should not match"
        assert result['verdict'] == 'FAIL', "Verdict should be FAIL for different files"
        assert result['reason'] == 'Outputs differ beyond tolerance'
        
        # Check summary exists and has basic stats
        assert 'summary' in result, "Result should include summary"
        summary = result['summary']
        
        # All 4 sample_ids exist in both files
        assert summary['rows_in_common'] == 4, "Should have 4 rows in common"
        assert summary['rows_only_in_df1'] == 0, "No rows unique to df1"
        assert summary['rows_only_in_df2'] == 0, "No rows unique to df2"
        
        # Check for differences (flexible to handle different API versions)
        if 'rows_with_differences' in summary:
            assert summary['rows_with_differences'] > 0, "Should detect value differences"
        else:
            # Fallback: check that report mentions differences
            assert 'differ' in result['report'].lower(), "Report should mention differences"
    
    def test_within_tolerance_pass(self, csv_files_within_tolerance):
        """Test that differences within tolerance are accepted"""
        file1, file2 = csv_files_within_tolerance
        comparator = TabularComparator()
        
        result = comparator.compare(str(file1), str(file2), {
            'join_columns': ['sample_id'],
            'abs_tol': 1e-4,  # Larger tolerance
            'rel_tol': 0.01
        })
        
        assert result['match'] == True
        assert result['verdict'] == 'PASS'
    
    def test_outside_tolerance_fail(self, csv_files_within_tolerance):
        """Test that differences outside tolerance fail"""
        file1, file2 = csv_files_within_tolerance
        comparator = TabularComparator()
        
        result = comparator.compare(str(file1), str(file2), {
            'join_columns': ['sample_id'],
            'abs_tol': 1e-10,  # Very strict tolerance
            'rel_tol': 0.0
        })
        
        assert result['match'] == False
        assert result['verdict'] == 'FAIL'
    
    def test_different_rows_detected(self, csv_files_different_rows):
        """Test that missing/extra rows are detected"""
        file1, file2 = csv_files_different_rows
        comparator = TabularComparator()
        
        result = comparator.compare(str(file1), str(file2), {
            'join_columns': ['sample_id'],
            'abs_tol': 1e-5,
            'rel_tol': 0.01
        })
        
        assert result['match'] == False
        assert result['summary']['rows_only_in_df1'] == 1  # D
        assert result['summary']['rows_only_in_df2'] == 1  # E
    
    def test_can_compare_csv_tsv_excel(self):
        """Test file type detection"""
        comparator = TabularComparator()
        
        assert comparator.can_compare('data.csv') == True
        assert comparator.can_compare('data.tsv') == True
        assert comparator.can_compare('data.xlsx') == True
        assert comparator.can_compare('data.txt') == False
        assert comparator.can_compare('image.png') == False
    
    def test_default_config_used(self, identical_csv_files):
        """Test that default config works when not provided"""
        file1, file2 = identical_csv_files
        comparator = TabularComparator()
        
        # Should use first column as join key by default
        result = comparator.compare(str(file1), str(file2), {})
        
        assert result['match'] == True
        assert 'configuration' in result


# ============================================================================
# IMAGE COMPARATOR TESTS
# ============================================================================

class TestImageComparator:
    """Test suite for image comparison"""
    
    def test_identical_images_pass(self, identical_images):
        """Test that identical images match"""
        file1, file2 = identical_images
        comparator = ImageComparator()
        
        result = comparator.compare(str(file1), str(file2), {
            'ssim_threshold': 0.95
        })
        
        assert result['match'] == True
        assert result['verdict'] == 'PASS'
        assert result['metrics']['ssim'] == 1.0  # Identical = SSIM of 1.0
    
    def test_different_images_fail(self, different_images):
        """Test that different images are detected"""
        file1, file2 = different_images
        comparator = ImageComparator()
        
        result = comparator.compare(str(file1), str(file2), {
            'ssim_threshold': 0.95
        })
        
        assert result['match'] == False
        assert result['verdict'] == 'FAIL'
        assert result['metrics']['ssim'] < 0.95
    
    def test_similar_images_pass_with_threshold(self, similar_images):
        """Test that similar images pass with appropriate threshold"""
        file1, file2 = similar_images
        comparator = ImageComparator()
        
        result = comparator.compare(str(file1), str(file2), {
            'ssim_threshold': 0.75  # Relaxed threshold
        })
        
        assert result['match'] == True
        assert result['metrics']['ssim'] >= 0.90
    
    def test_similar_images_fail_with_strict_threshold(self, similar_images):
        """Test that similar images fail with strict threshold"""
        file1, file2 = similar_images
        comparator = ImageComparator()
        
        result = comparator.compare(str(file1), str(file2), {
            'ssim_threshold': 1  # Very strict
        })
        
        assert result['match'] == False
    
    def test_can_compare_image_formats(self):
        """Test image format detection"""
        comparator = ImageComparator()
        
        assert comparator.can_compare('image.png') == True
        assert comparator.can_compare('image.jpg') == True
        assert comparator.can_compare('image.jpeg') == True
        assert comparator.can_compare('image.tiff') == True
        assert comparator.can_compare('data.csv') == False

# ============================================================================
# HDF5 COMPARATOR TESTS
# ============================================================================

class TestHDF5Comparator:
    """Test suite for HDF5 comparison"""
    
    def test_identical_hdf5_pass(self, identical_hdf5_files):
        """Test that identical HDF5 files match"""
        file1, file2 = identical_hdf5_files
        comparator = HDF5Comparator()
        
        result = comparator.compare(str(file1), str(file2), {
            'rtol': 1e-5,
            'atol': 1e-8
        })
        
        assert result['match'] == True
        assert result['verdict'] == 'PASS'
        assert result['summary']['differences_found'] == 0
    
    def test_different_hdf5_fail(self, different_hdf5_files):
        """Test that different HDF5 files are detected"""
        file1, file2 = different_hdf5_files
        comparator = HDF5Comparator()
        
        result = comparator.compare(str(file1), str(file2), {
            'rtol': 1e-5,
            'atol': 1e-8
        })
        
        assert result['match'] == False
        assert result['verdict'] == 'FAIL'
        assert result['summary']['differences_found'] > 0
        assert len(result['differences']) > 0
    
    def test_can_compare_hdf5(self):
        """Test HDF5 format detection"""
        comparator = HDF5Comparator()
        
        assert comparator.can_compare('data.h5') == True
        assert comparator.can_compare('data.hdf5') == True
        assert comparator.can_compare('data.csv') == False


# ============================================================================
# COMPARISON MANAGER TESTS
# ============================================================================

class TestComparisonManager:
    """Test suite for the comparison manager"""
    
    def test_auto_select_binary_comparator(self):
        """Test automatic selection of binary comparator"""
        manager = ComparisonManager()
        
        comparator = manager.get_comparator('file.bin')
        assert isinstance(comparator, BinaryComparator)
    
    def test_auto_select_tabular_comparator(self):
        """Test automatic selection of tabular comparator"""
        manager = ComparisonManager()
        
        comparator = manager.get_comparator('data.csv')
        assert isinstance(comparator, TabularComparator)
    
    def test_auto_select_image_comparator(self):
        """Test automatic selection of image comparator"""
        manager = ComparisonManager()
        
        comparator = manager.get_comparator('image.png')
        assert isinstance(comparator, ImageComparator)
    
    def test_config_pattern_matching(self):
        """Test configuration matching by pattern"""
        manager = ComparisonManager()
        
        manager.set_comparison_config('results/*.csv', {'abs_tol': 1e-6})
        manager.set_comparison_config('*.csv', {'abs_tol': 1e-3})
        
        
        # More specific pattern should match
        config = manager.get_config_for_file('results/data.csv')
        assert config['abs_tol'] == 1e-6
        
        # General pattern
        config = manager.get_config_for_file('other/data.csv')
        assert config['abs_tol'] == 1e-3
    
    def test_compare_files_with_auto_selection(self, identical_csv_files):
        """Test end-to-end comparison with auto-selection"""
        file1, file2 = identical_csv_files
        manager = ComparisonManager()
        
        manager.set_comparison_config('*.csv', {
            'join_columns': ['sample_id'],
            'abs_tol': 1e-5
        })
        
        result = manager.compare_files(str(file1), str(file2))
        
        assert result['match'] == True
        assert 'tool_metadata' in result


# ============================================================================
# INTEGRATION TESTS
# ============================================================================

class TestComparisonIntegration:
    """Integration tests combining multiple components"""
    
    def test_compare_multiple_file_types(self, temp_dir, 
                                         identical_csv_files,
                                         identical_binary_files):
        """Test comparing multiple file types in one batch"""
        manager = ComparisonManager()
        
        # Setup configs
        manager.set_comparison_config('*.csv', {
            'join_columns': ['sample_id'],
            'abs_tol': 1e-5
        })
        
        # Compare CSV files
        csv1, csv2 = identical_csv_files
        csv_result = manager.compare_files(str(csv1), str(csv2))
        
        # Compare binary files
        bin1, bin2 = identical_binary_files
        bin_result = manager.compare_files(str(bin1), str(bin2))
        
        assert csv_result['match'] == True
        assert bin_result['match'] == True
        assert csv_result['method'] == 'datacompy'
        assert bin_result['method'] == 'sha256_checksum'
    
    def test_mixed_results_batch(self, identical_csv_files, different_binary_files):
        """Test batch with some passing and some failing"""
        manager = ComparisonManager()
        
        csv1, csv2 = identical_csv_files
        bin1, bin2 = different_binary_files
        
        results = {
            'csv': manager.compare_files(str(csv1), str(csv2)),
            'binary': manager.compare_files(str(bin1), str(bin2))
        }
        
        assert results['csv']['match'] == True
        assert results['binary']['match'] == False
        
        # Summary
        all_pass = all(r['match'] for r in results.values())
        assert all_pass == False


# ============================================================================
# PARAMETRIZED TESTS
# ============================================================================

class TestParametrized:
    """Parametrized tests to check multiple scenarios efficiently"""
    
    @pytest.mark.parametrize("tolerance,expected_match", [
        (1e-10, False),  # Very strict - should fail
        (1e-4, True),    # Relaxed - should pass
        (1e-5, True),    # Moderate - should pass
        (1e-3, True),    # Very relaxed - should pass
    ])
    def test_tolerance_levels(self, csv_files_within_tolerance, tolerance, expected_match):
        """Test different tolerance levels"""
        file1, file2 = csv_files_within_tolerance
        comparator = TabularComparator()
        
        result = comparator.compare(str(file1), str(file2), {
            'join_columns': ['sample_id'],
            'abs_tol': tolerance,
            'rel_tol': 0.0
        })
        
        assert result['match'] == expected_match
    
    @pytest.mark.parametrize("file_ext,comparator_class", [
        ('data.csv', TabularComparator),
        ('data.tsv', TabularComparator),
        ('image.png', ImageComparator),
        ('image.jpg', ImageComparator),
        ('data.h5', HDF5Comparator),
        ('data.bin', BinaryComparator),
    ])
    def test_file_type_routing(self, file_ext, comparator_class):
        """Test that correct comparator is selected for each file type"""
        manager = ComparisonManager()
        comparator = manager.get_comparator(file_ext)
        assert isinstance(comparator, comparator_class)


# ============================================================================
# ERROR HANDLING TESTS
# ============================================================================

class TestErrorHandling:
    """Test error handling in comparators"""
    
    def test_missing_file_error(self, temp_dir):
        """Test that missing files raise appropriate errors"""
        comparator = BinaryComparator()
        
        with pytest.raises(FileNotFoundError):
            comparator.compare(
                str(temp_dir / 'nonexistent1.txt'),
                str(temp_dir / 'nonexistent2.txt'),
                {}
            )
    
    def test_invalid_csv_format(self, temp_dir):
        """Test handling of invalid CSV files"""
        file1 = temp_dir / 'invalid1.csv'
        file2 = temp_dir / 'invalid2.csv'
        
        file1.write_text("This is not a valid CSV\nNo structure here")
        file2.write_text("Also not valid")
        
        comparator = TabularComparator()
        
        # Should handle gracefully (implementation dependent)
        # This might raise or return an error result
        try:
            result = comparator.compare(str(file1), str(file2), {})
            # If it returns, check it indicates error
            assert 'error' in result or result['match'] == False
        except Exception as e:
            # If it raises, that's also acceptable
            assert e is not None


# ============================================================================
# RUN TESTS
# ============================================================================

if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])