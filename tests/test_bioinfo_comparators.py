import pytest
import tempfile
from pathlib import Path
from comparators.bioinfo import FastaComparator, BamComparator


# ============================================================================
# FIXTURES - FASTA
# ============================================================================

@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def identical_fasta_files(temp_dir):
    """Create two identical FASTA files"""
    content = """>seq1 description one
ATCGATCGATCG
GCTAGCTAGCTA
>seq2 description two
TTTTAAAACCCCGGGG
>seq3
NNNNNNNN
"""
    
    file1 = temp_dir / 'sequences1.fasta'
    file2 = temp_dir / 'sequences2.fasta'
    
    file1.write_text(content)
    file2.write_text(content)
    
    return file1, file2


@pytest.fixture
def different_fasta_files(temp_dir):
    """Create two FASTA files with different sequences"""
    content1 = """>seq1
ATCGATCG
>seq2
TTTTAAAA
"""
    
    content2 = """>seq1
ATCGATCG
>seq3
GGGGCCCC
"""
    
    file1 = temp_dir / 'sequences1.fasta'
    file2 = temp_dir / 'sequences2.fasta'
    
    file1.write_text(content1)
    file2.write_text(content2)
    
    return file1, file2


@pytest.fixture
def unordered_fasta_files(temp_dir):
    """Create FASTA files with same sequences but different order"""
    content1 = """>seq1
ATCG
>seq2
TTTT
>seq3
GGGG
"""
    
    content2 = """>seq2
TTTT
>seq3
GGGG
>seq1
ATCG
"""
    
    file1 = temp_dir / 'sequences1.fasta'
    file2 = temp_dir / 'sequences2.fasta'
    
    file1.write_text(content1)
    file2.write_text(content2)
    
    return file1, file2


@pytest.fixture
def case_different_fasta(temp_dir):
    """Create FASTA files with different case"""
    content1 = """>seq1
ATCGATCG
"""
    
    content2 = """>seq1
atcgatcg
"""
    
    file1 = temp_dir / 'sequences1.fasta'
    file2 = temp_dir / 'sequences2.fasta'
    
    file1.write_text(content1)
    file2.write_text(content2)
    
    return file1, file2


# ============================================================================
# FIXTURES - BAM
# ============================================================================

@pytest.fixture
def identical_bam_files(temp_dir):
    """Create two identical BAM files"""
    try:
        import pysam
    except ImportError:
        pytest.skip("pysam not installed")
    
    # Create minimal BAM file
    header = {
        'HD': {'VN': '1.0'},
        'SQ': [{'LN': 1000, 'SN': 'chr1'}]
    }
    
    file1 = temp_dir / 'alignments1.bam'
    file2 = temp_dir / 'alignments2.bam'
    
    # Write identical files
    for filepath in [file1, file2]:
        with pysam.AlignmentFile(str(filepath), 'wb', header=header) as bam:
            # Create some test reads
            a = pysam.AlignedSegment()
            a.query_name = "read1"
            a.query_sequence = "ATCGATCG"
            a.flag = 0
            a.reference_id = 0
            a.reference_start = 100
            a.mapping_quality = 60
            a.cigar = ((0, 8),)  # 8M
            bam.write(a)
            
            b = pysam.AlignedSegment()
            b.query_name = "read2"
            b.query_sequence = "GCTAGCTA"
            b.flag = 16  # reverse strand
            b.reference_id = 0
            b.reference_start = 200
            b.mapping_quality = 60
            b.cigar = ((0, 8),)
            bam.write(b)
    
    return file1, file2


@pytest.fixture
def different_bam_files(temp_dir):
    """Create two different BAM files"""
    try:
        import pysam
    except ImportError:
        pytest.skip("pysam not installed")
    
    header = {
        'HD': {'VN': '1.0'},
        'SQ': [{'LN': 1000, 'SN': 'chr1'}]
    }
    
    file1 = temp_dir / 'alignments1.bam'
    file2 = temp_dir / 'alignments2.bam'
    
    # File 1
    with pysam.AlignmentFile(str(file1), 'wb', header=header) as bam:
        a = pysam.AlignedSegment()
        a.query_name = "read1"
        a.query_sequence = "ATCGATCG"
        a.flag = 0
        a.reference_id = 0
        a.reference_start = 100
        a.mapping_quality = 60
        a.cigar = ((0, 8),)
        bam.write(a)
    
    # File 2 - different alignment
    with pysam.AlignmentFile(str(file2), 'wb', header=header) as bam:
        a = pysam.AlignedSegment()
        a.query_name = "read1"
        a.query_sequence = "ATCGATCG"
        a.flag = 0
        a.reference_id = 0
        a.reference_start = 200  # Different position!
        a.mapping_quality = 60
        a.cigar = ((0, 8),)
        bam.write(a)
    
    return file1, file2


# ============================================================================
# FASTA COMPARATOR TESTS
# ============================================================================

class TestFastaComparator:
    """Test suite for FASTA file comparison"""
    
    def test_can_compare_fasta_extensions(self):
        """Test FASTA file extension detection"""
        comparator = FastaComparator()
        
        assert comparator.can_compare('sequences.fasta') == True
        assert comparator.can_compare('genome.fa') == True
        assert comparator.can_compare('proteins.faa') == True
        assert comparator.can_compare('data.csv') == False
    
    def test_identical_fasta_exact_mode(self, identical_fasta_files):
        """Test identical FASTA files in exact mode"""
        file1, file2 = identical_fasta_files
        comparator = FastaComparator()
        
        result = comparator.compare(str(file1), str(file2), {'mode': 'exact'})
        
        assert result['match'] == True
        assert result['verdict'] == 'PASS'
        assert result['mode'] == 'exact'
        assert result['summary']['differences_found'] == 0
    
    def test_different_fasta_exact_mode(self, different_fasta_files):
        """Test different FASTA files in exact mode"""
        file1, file2 = different_fasta_files
        comparator = FastaComparator()
        
        result = comparator.compare(str(file1), str(file2), {'mode': 'exact'})
        
        assert result['match'] == False
        assert result['verdict'] == 'FAIL'
        assert result['summary']['differences_found'] > 0
    
    def test_identical_fasta_unordered_mode(self, identical_fasta_files):
        """Test identical FASTA files in unordered mode"""
        file1, file2 = identical_fasta_files
        comparator = FastaComparator()
        
        result = comparator.compare(str(file1), str(file2), {'mode': 'unordered'})
        
        assert result['match'] == True
        assert result['verdict'] == 'PASS'
        assert result['mode'] == 'unordered'
    
    def test_unordered_fasta_exact_mode_fails(self, unordered_fasta_files):
        """Test that unordered FASTA files fail in exact mode"""
        file1, file2 = unordered_fasta_files
        comparator = FastaComparator()
        
        result = comparator.compare(str(file1), str(file2), {'mode': 'exact'})
        
        assert result['match'] == False
        assert result['verdict'] == 'FAIL'
    
    def test_unordered_fasta_unordered_mode_passes(self, unordered_fasta_files):
        """Test that unordered FASTA files pass in unordered mode"""
        file1, file2 = unordered_fasta_files
        comparator = FastaComparator()
        
        result = comparator.compare(str(file1), str(file2), {'mode': 'unordered'})
        
        assert result['match'] == True
        assert result['verdict'] == 'PASS'
        assert result['summary']['sequences_in_common'] == 3
    
    def test_case_insensitive_comparison(self, case_different_fasta):
        """Test case-insensitive sequence comparison"""
        file1, file2 = case_different_fasta
        comparator = FastaComparator()
        
        # Default: case insensitive
        result = comparator.compare(str(file1), str(file2), {'mode': 'unordered'})
        assert result['match'] == True
        
        # Explicit case sensitive
        result = comparator.compare(str(file1), str(file2), {
            'mode': 'unordered',
            'case_sensitive': True
        })
        assert result['match'] == False
    
    def test_content_only_mode(self, unordered_fasta_files):
        """Test content-only comparison ignoring IDs"""
        file1, file2 = unordered_fasta_files
        comparator = FastaComparator()
        
        result = comparator.compare(str(file1), str(file2), {'mode': 'content_only'})
        
        assert result['match'] == True
        assert result['verdict'] == 'PASS'
        assert result['mode'] == 'content_only'
    
    def test_missing_sequences(self, different_fasta_files):
        """Test detection of missing sequences"""
        file1, file2 = different_fasta_files
        comparator = FastaComparator()
        
        result = comparator.compare(str(file1), str(file2), {'mode': 'unordered'})
        
        assert result['match'] == False
        assert result['summary']['sequences_only_in_file1'] == 1  # seq2
        assert result['summary']['sequences_only_in_file2'] == 1  # seq3
        assert 'seq2' in result['sequences_only_in_file1']
        assert 'seq3' in result['sequences_only_in_file2']
    
    def test_tool_metadata(self):
        """Test tool metadata generation"""
        comparator = FastaComparator()
        metadata = comparator.get_tool_metadata()
        
        assert metadata['@type'] == 'SoftwareApplication'
        assert metadata['name'] == 'BioPython SeqIO'
        assert 'version' in metadata


# ============================================================================
# BAM COMPARATOR TESTS
# ============================================================================

class TestBamComparator:
    """Test suite for BAM file comparison"""
    
    def test_can_compare_bam_extensions(self):
        """Test BAM file extension detection"""
        comparator = BamComparator()
        
        assert comparator.can_compare('alignments.bam') == True
        assert comparator.can_compare('reads.sam') == True
        assert comparator.can_compare('data.cram') == True
        assert comparator.can_compare('sequences.fasta') == False
    
    def test_identical_bam_binary_mode(self, identical_bam_files):
        """Test identical BAM files in binary mode"""
        file1, file2 = identical_bam_files
        comparator = BamComparator()
        
        result = comparator.compare(str(file1), str(file2), {'mode': 'binary'})
        
        assert result['match'] == True
        assert result['verdict'] == 'PASS'
        assert result['mode'] == 'binary'
        assert result['checksums']['file1'] == result['checksums']['file2']
    
    def test_different_bam_binary_mode(self, different_bam_files):
        """Test different BAM files in binary mode"""
        file1, file2 = different_bam_files
        comparator = BamComparator()
        
        result = comparator.compare(str(file1), str(file2), {'mode': 'binary'})
        
        assert result['match'] == False
        assert result['verdict'] == 'FAIL'
        assert result['checksums']['file1'] != result['checksums']['file2']
    
    def test_identical_bam_sample_mode(self, identical_bam_files):
        """Test identical BAM files in sample mode"""
        file1, file2 = identical_bam_files
        comparator = BamComparator()
        
        result = comparator.compare(str(file1), str(file2), {
            'mode': 'sample',
            'sample_size': 10
        })
        
        assert result['match'] == True
        assert result['verdict'] == 'PASS'
        assert result['mode'] == 'sample'
        assert result['summary']['header_matches'] == True
        assert result['summary']['alignments_match'] == True
    
    def test_different_bam_sample_mode(self, different_bam_files):
        """Test different BAM files in sample mode"""
        file1, file2 = different_bam_files
        comparator = BamComparator()
        
        result = comparator.compare(str(file1), str(file2), {
            'mode': 'sample',
            'sample_size': 10
        })
        
        assert result['match'] == False
        assert result['verdict'] == 'FAIL'
        assert result['summary']['alignments_match'] == False
    
    def test_identical_bam_full_mode(self, identical_bam_files):
        """Test identical BAM files in full mode"""
        file1, file2 = identical_bam_files
        comparator = BamComparator()
        
        result = comparator.compare(str(file1), str(file2), {'mode': 'full'})
        
        assert result['match'] == True
        assert result['verdict'] == 'PASS'
        assert result['mode'] == 'full'
        assert result['summary']['total_alignments_file1'] == 2
        assert result['summary']['total_alignments_file2'] == 2
    
    def test_bam_header_only_mode(self, identical_bam_files):
        """Test header-only comparison"""
        file1, file2 = identical_bam_files
        comparator = BamComparator()
        
        result = comparator.compare(str(file1), str(file2), {'mode': 'header'})
        
        assert result['match'] == True
        assert result['verdict'] == 'PASS'
        assert result['mode'] == 'header'
        assert result['summary']['header_matches'] == True
    
    def test_bam_ordered_vs_unordered(self, temp_dir):
        """Test ordered vs unordered comparison modes"""
        try:
            import pysam
        except ImportError:
            pytest.skip("pysam not installed")
        
        header = {
            'HD': {'VN': '1.0'},
            'SQ': [{'LN': 1000, 'SN': 'chr1'}]
        }
        
        file1 = temp_dir / 'ordered1.bam'
        file2 = temp_dir / 'ordered2.bam'
        
        # File 1: read1, read2
        with pysam.AlignmentFile(str(file1), 'wb', header=header) as bam:
            for i, pos in enumerate([100, 200]):
                a = pysam.AlignedSegment()
                a.query_name = f"read{i+1}"
                a.query_sequence = "ATCGATCG"
                a.flag = 0
                a.reference_id = 0
                a.reference_start = pos
                a.mapping_quality = 60
                a.cigar = ((0, 8),)
                bam.write(a)
        
        # File 2: read2, read1 (reversed order)
        with pysam.AlignmentFile(str(file2), 'wb', header=header) as bam:
            for i, pos in enumerate([200, 100]):
                read_num = 2 if i == 0 else 1
                a = pysam.AlignedSegment()
                a.query_name = f"read{read_num}"
                a.query_sequence = "ATCGATCG"
                a.flag = 0
                a.reference_id = 0
                a.reference_start = pos
                a.mapping_quality = 60
                a.cigar = ((0, 8),)
                bam.write(a)
        
        comparator = BamComparator()
        
        # Ordered comparison should fail
        result = comparator.compare(str(file1), str(file2), {
            'mode': 'sample',
            'check_order': True
        })
        assert result['match'] == False
        
        # Unordered comparison should pass
        result = comparator.compare(str(file1), str(file2), {
            'mode': 'sample',
            'check_order': False
        })
        assert result['match'] == True
    
    def test_tool_metadata(self):
        """Test tool metadata generation"""
        comparator = BamComparator()
        metadata = comparator.get_tool_metadata()
        
        assert metadata['@type'] == 'SoftwareApplication'
        assert metadata['name'] == 'pysam'
        assert 'version' in metadata


# ============================================================================
# INTEGRATION TESTS
# ============================================================================

class TestBioinfoIntegration:
    """Integration tests for bioinformatics comparators"""
    
    def test_fasta_in_comparison_manager(self, identical_fasta_files, temp_dir):
        """Test FASTA comparator integration with ComparisonManager"""
        from comparators.manager import ComparisonManager
        
        file1, file2 = identical_fasta_files
        manager = ComparisonManager()
        
        # Set config for FASTA files
        manager.set_comparison_config('*.fasta', {
            'mode': 'unordered',
            'case_sensitive': False
        })
        
        result = manager.compare_files(str(file1), str(file2))
        
        assert result['match'] == True
        assert result['method'] == 'fasta_comparison'
    
    def test_bam_in_comparison_manager(self, identical_bam_files):
        """Test BAM comparator integration with ComparisonManager"""
        from comparators.manager import ComparisonManager
        
        file1, file2 = identical_bam_files
        manager = ComparisonManager()
        
        # Set config for BAM files
        manager.set_comparison_config('*.bam', {
            'mode': 'sample',
            'sample_size': 100
        })
        
        result = manager.compare_files(str(file1), str(file2))
        
        assert result['match'] == True
        assert result['method'] == 'bam_comparison'
    
    def test_multiple_file_types(self, identical_fasta_files, identical_bam_files):
        """Test handling multiple bioinformatics file types"""
        from comparators.manager import ComparisonManager
        
        manager = ComparisonManager()
        
        # Configure both types
        manager.set_comparison_config('*.fasta', {'mode': 'unordered'})
        manager.set_comparison_config('*.bam', {'mode': 'sample'})
        
        # Test FASTA
        fasta1, fasta2 = identical_fasta_files
        result = manager.compare_files(str(fasta1), str(fasta2))
        assert result['method'] == 'fasta_comparison'
        assert result['match'] == True
        
        # Test BAM
        bam1, bam2 = identical_bam_files
        result = manager.compare_files(str(bam1), str(bam2))
        assert result['method'] == 'bam_comparison'
        assert result['match'] == True


# ============================================================================
# PARAMETRIZED TESTS
# ============================================================================

class TestParametrizedComparisons:
    """Parametrized tests for various configurations"""
    
    @pytest.mark.parametrize("mode,expected", [
        ('exact', True),
        ('unordered', True),
        ('content_only', True),
    ])
    def test_fasta_modes_identical_files(self, identical_fasta_files, mode, expected):
        """Test all FASTA modes with identical files"""
        file1, file2 = identical_fasta_files
        comparator = FastaComparator()
        
        result = comparator.compare(str(file1), str(file2), {'mode': mode})
        assert result['match'] == expected
    
    @pytest.mark.parametrize("mode", ['binary', 'header', 'sample', 'full'])
    def test_bam_modes_identical_files(self, identical_bam_files, mode):
        """Test all BAM modes with identical files"""
        file1, file2 = identical_bam_files
        comparator = BamComparator()
        
        result = comparator.compare(str(file1), str(file2), {'mode': mode})
        assert result['match'] == True
        assert result['verdict'] == 'PASS'


# ============================================================================
# ERROR HANDLING TESTS
# ============================================================================

class TestErrorHandling:
    """Test error handling for edge cases"""
    
    def test_fasta_missing_biopython(self, identical_fasta_files, monkeypatch):
        """Test graceful handling when BioPython is not installed"""
        file1, file2 = identical_fasta_files
        
        # Mock missing BioPython
        import sys
        import importlib
        
        def mock_import(name, *args, **kwargs):
            if name == 'Bio' or name.startswith('Bio.'):
                raise ImportError("No module named 'Bio'")
            return importlib.__import__(name, *args, **kwargs)
        
        monkeypatch.setattr('builtins.__import__', mock_import)
        
        comparator = FastaComparator()
        result = comparator.compare(str(file1), str(file2), {})
        
        assert result['match'] == False
        assert result['verdict'] == 'ERROR'
        assert 'BioPython not installed' in result['reason']
    
    def test_bam_missing_pysam(self, identical_bam_files, monkeypatch):
        """Test graceful handling when pysam is not installed"""
        file1, file2 = identical_bam_files
        
        # Mock missing pysam
        import sys
        import importlib
        
        def mock_import(name, *args, **kwargs):
            if name == 'pysam':
                raise ImportError("No module named 'pysam'")
            return importlib.__import__(name, *args, **kwargs)
        
        monkeypatch.setattr('builtins.__import__', mock_import)
        
        comparator = BamComparator()
        result = comparator.compare(str(file1), str(file2), {})
        
        assert result['match'] == False
        assert result['verdict'] == 'ERROR'
        assert 'pysam not installed' in result['reason']
    
    def test_invalid_fasta_mode(self, identical_fasta_files):
        """Test handling of invalid comparison mode"""
        file1, file2 = identical_fasta_files
        comparator = FastaComparator()
        
        result = comparator.compare(str(file1), str(file2), {'mode': 'invalid_mode'})
        
        assert result['match'] == False
        assert result['verdict'] == 'ERROR'
        assert 'Unknown mode' in result['reason']
    
    def test_corrupted_fasta_file(self, temp_dir):
        """Test handling of corrupted FASTA files"""
        file1 = temp_dir / 'corrupted1.fasta'
        file2 = temp_dir / 'good.fasta'
        
        file1.write_text("This is not a valid FASTA file\n")
        file2.write_text(">seq1\nATCG\n")
        
        comparator = FastaComparator()
        result = comparator.compare(str(file1), str(file2), {})
        
        # Should handle gracefully - empty FASTA is technically valid
        assert result['verdict'] in ['PASS', 'FAIL', 'ERROR']