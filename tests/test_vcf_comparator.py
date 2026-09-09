import pytest
import tempfile
from pathlib import Path
from comparators.bioinfo import VcfComparator


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def identical_vcf_files(temp_dir):
    """Create two identical VCF files"""
    vcf_content = """##fileformat=VCFv4.2
##contig=<ID=chr1,length=248956422>
##contig=<ID=chr2,length=242193529>
##INFO=<ID=DP,Number=1,Type=Integer,Description="Total Depth">
##INFO=<ID=AF,Number=A,Type=Float,Description="Allele Frequency">
##FORMAT=<ID=GT,Number=1,Type=String,Description="Genotype">
##FORMAT=<ID=DP,Number=1,Type=Integer,Description="Read Depth">
#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\tFORMAT\tsample1\tsample2
chr1\t100\t.\tA\tG\t30.0\tPASS\tDP=50;AF=0.5\tGT:DP\t0/1:25\t0/0:25
chr1\t200\t.\tC\tT\t40.0\tPASS\tDP=60;AF=0.33\tGT:DP\t0/1:30\t0/1:30
chr2\t150\t.\tG\tA\t50.0\tPASS\tDP=70;AF=0.25\tGT:DP\t0/0:35\t0/1:35
"""
    
    file1 = temp_dir / 'variants1.vcf'
    file2 = temp_dir / 'variants2.vcf'
    
    file1.write_text(vcf_content)
    file2.write_text(vcf_content)
    
    return file1, file2


@pytest.fixture
def different_positions_vcf(temp_dir):
    """Create VCF files with different variant positions"""
    vcf1_content = """##fileformat=VCFv4.2
##contig=<ID=chr1,length=248956422>
##INFO=<ID=DP,Number=1,Type=Integer,Description="Total Depth">
##FORMAT=<ID=GT,Number=1,Type=String,Description="Genotype">
#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\tFORMAT\tsample1
chr1\t100\t.\tA\tG\t30.0\tPASS\tDP=50\tGT\t0/1
chr1\t200\t.\tC\tT\t40.0\tPASS\tDP=60\tGT\t0/1
"""
    
    vcf2_content = """##fileformat=VCFv4.2
##contig=<ID=chr1,length=248956422>
##INFO=<ID=DP,Number=1,Type=Integer,Description="Total Depth">
##FORMAT=<ID=GT,Number=1,Type=String,Description="Genotype">
#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\tFORMAT\tsample1
chr1\t100\t.\tA\tG\t30.0\tPASS\tDP=50\tGT\t0/1
chr1\t300\t.\tG\tA\t50.0\tPASS\tDP=70\tGT\t0/1
"""
    
    file1 = temp_dir / 'variants1.vcf'
    file2 = temp_dir / 'variants2.vcf'
    
    file1.write_text(vcf1_content)
    file2.write_text(vcf2_content)
    
    return file1, file2


@pytest.fixture
def different_genotypes_vcf(temp_dir):
    """Create VCF files with same positions but different genotypes"""
    vcf1_content = """##fileformat=VCFv4.2
##contig=<ID=chr1,length=248956422>
##INFO=<ID=DP,Number=1,Type=Integer,Description="Total Depth">
##FORMAT=<ID=GT,Number=1,Type=String,Description="Genotype">
#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\tFORMAT\tsample1
chr1\t100\t.\tA\tG\t30.0\tPASS\tDP=50\tGT\t0/1
chr1\t200\t.\tC\tT\t40.0\tPASS\tDP=60\tGT\t1/1
"""
    
    vcf2_content = """##fileformat=VCFv4.2
##contig=<ID=chr1,length=248956422>
##INFO=<ID=DP,Number=1,Type=Integer,Description="Total Depth">
##FORMAT=<ID=GT,Number=1,Type=String,Description="Genotype">
#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\tFORMAT\tsample1
chr1\t100\t.\tA\tG\t30.0\tPASS\tDP=50\tGT\t0/1
chr1\t200\t.\tC\tT\t40.0\tPASS\tDP=60\tGT\t0/1
"""
    
    file1 = temp_dir / 'variants1.vcf'
    file2 = temp_dir / 'variants2.vcf'
    
    file1.write_text(vcf1_content)
    file2.write_text(vcf2_content)
    
    return file1, file2


@pytest.fixture
def different_quality_vcf(temp_dir):
    """Create VCF files with different quality scores"""
    vcf1_content = """##fileformat=VCFv4.2
##contig=<ID=chr1,length=248956422>
##INFO=<ID=DP,Number=1,Type=Integer,Description="Total Depth">
##FORMAT=<ID=GT,Number=1,Type=String,Description="Genotype">
#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\tFORMAT\tsample1
chr1\t100\t.\tA\tG\t30.0\tPASS\tDP=50\tGT\t0/1
chr1\t200\t.\tC\tT\t40.0\tPASS\tDP=60\tGT\t0/1
"""
    
    vcf2_content = """##fileformat=VCFv4.2
##contig=<ID=chr1,length=248956422>
##INFO=<ID=DP,Number=1,Type=Integer,Description="Total Depth">
##FORMAT=<ID=GT,Number=1,Type=String,Description="Genotype">
#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\tFORMAT\tsample1
chr1\t100\t.\tA\tG\t30.5\tPASS\tDP=50\tGT\t0/1
chr1\t200\t.\tC\tT\t45.0\tPASS\tDP=60\tGT\t0/1
"""
    
    file1 = temp_dir / 'variants1.vcf'
    file2 = temp_dir / 'variants2.vcf'
    
    file1.write_text(vcf1_content)
    file2.write_text(vcf2_content)
    
    return file1, file2


@pytest.fixture
def multi_sample_vcf(temp_dir):
    """Create multi-sample VCF files"""
    vcf_content = """##fileformat=VCFv4.2
##contig=<ID=chr1,length=248956422>
##INFO=<ID=DP,Number=1,Type=Integer,Description="Total Depth">
##FORMAT=<ID=GT,Number=1,Type=String,Description="Genotype">
#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\tFORMAT\tsample1\tsample2\tsample3
chr1\t100\t.\tA\tG\t30.0\tPASS\tDP=50\tGT\t0/1\t0/0\t1/1
chr1\t200\t.\tC\tT\t40.0\tPASS\tDP=60\tGT\t0/1\t0/1\t0/0
"""
    
    file1 = temp_dir / 'multisample1.vcf'
    file2 = temp_dir / 'multisample2.vcf'
    
    file1.write_text(vcf_content)
    file2.write_text(vcf_content)
    
    return file1, file2


# ============================================================================
# TEST CLASS
# ============================================================================

class TestVcfComparator:
    """Test suite for VCF file comparison"""
    
    def test_can_compare_vcf_extensions(self):
        """Test VCF file extension detection"""
        comparator = VcfComparator()
        
        assert comparator.can_compare('variants.vcf') == True
        assert comparator.can_compare('variants.vcf.gz') == True
        assert comparator.can_compare('variants.bcf') == True
        assert comparator.can_compare('sequences.fasta') == False
    
    def test_identical_vcf_positions_mode(self, identical_vcf_files):
        """Test identical VCF files in positions mode"""
        file1, file2 = identical_vcf_files
        comparator = VcfComparator()
        
        result = comparator.compare(str(file1), str(file2), {'mode': 'positions'})
        
        assert result['match'] == True
        assert result['verdict'] == 'PASS'
        assert result['mode'] == 'positions'
        assert result['summary']['variants_only_in_file1'] == 0
        assert result['summary']['variants_only_in_file2'] == 0
    
    def test_identical_vcf_genotypes_mode(self, identical_vcf_files):
        """Test identical VCF files in genotypes mode"""
        file1, file2 = identical_vcf_files
        comparator = VcfComparator()
        
        result = comparator.compare(str(file1), str(file2), {'mode': 'genotypes'})
        
        assert result['match'] == True
        assert result['verdict'] == 'PASS'
        assert result['mode'] == 'genotypes'
        assert result['summary']['genotype_differences'] == 0
    
    def test_identical_vcf_full_mode(self, identical_vcf_files):
        """Test identical VCF files in full mode"""
        file1, file2 = identical_vcf_files
        comparator = VcfComparator()
        
        result = comparator.compare(str(file1), str(file2), {'mode': 'full'})
        
        assert result['match'] == True
        assert result['verdict'] == 'PASS'
        assert result['mode'] == 'full'
    
    def test_different_positions(self, different_positions_vcf):
        """Test VCF files with different variant positions"""
        file1, file2 = different_positions_vcf
        comparator = VcfComparator()
        
        result = comparator.compare(str(file1), str(file2), {'mode': 'positions'})
        
        assert result['match'] == False
        assert result['verdict'] == 'FAIL'
        assert result['summary']['variants_only_in_file1'] == 1  # chr1:200
        assert result['summary']['variants_only_in_file2'] == 1  # chr1:300
    
    def test_different_genotypes(self, different_genotypes_vcf):
        """Test VCF files with different genotypes"""
        file1, file2 = different_genotypes_vcf
        comparator = VcfComparator()
        
        result = comparator.compare(str(file1), str(file2), {'mode': 'genotypes'})
        
        assert result['match'] == False
        assert result['verdict'] == 'FAIL'
        assert result['summary']['genotype_differences'] > 0
    
    def test_quality_tolerance(self, different_quality_vcf):
        """Test quality score tolerance"""
        file1, file2 = different_quality_vcf
        comparator = VcfComparator()
        
        # Strict tolerance - should fail
        result = comparator.compare(str(file1), str(file2), {
            'mode': 'genotypes',
            'quality_tolerance': 0.001
        })
        assert result['summary']['quality_differences'] > 0
        
        # Relaxed tolerance - should pass on quality
        result = comparator.compare(str(file1), str(file2), {
            'mode': 'genotypes',
            'quality_tolerance': 0.2  # 20% tolerance
        })
        assert result['summary']['quality_differences'] == 0
    
    def test_multi_sample_comparison(self, multi_sample_vcf):
        """Test multi-sample VCF comparison"""
        file1, file2 = multi_sample_vcf
        comparator = VcfComparator()
        
        result = comparator.compare(str(file1), str(file2), {'mode': 'genotypes'})
        
        assert result['match'] == True
        assert result['verdict'] == 'PASS'
        assert 'sample1' in result['summary']['samples_compared']
        assert 'sample2' in result['summary']['samples_compared']
        assert 'sample3' in result['summary']['samples_compared']
    
    def test_sample_subset(self, multi_sample_vcf):
        """Test comparing only a subset of samples"""
        file1, file2 = multi_sample_vcf
        comparator = VcfComparator()
        
        result = comparator.compare(str(file1), str(file2), {
            'mode': 'genotypes',
            'sample_subset': ['sample1', 'sample2']
        })
        
        assert result['match'] == True
        assert len(result['summary']['samples_compared']) == 2
    
    def test_ignore_info_fields(self, identical_vcf_files):
        """Test ignoring INFO fields"""
        file1, file2 = identical_vcf_files
        comparator = VcfComparator()
        
        result = comparator.compare(str(file1), str(file2), {
            'mode': 'full',
            'ignore_info': True
        })
        
        assert result['match'] == True
        assert result['configuration']['ignore_info'] == True
    
    def test_tool_metadata(self):
        """Test tool metadata generation"""
        comparator = VcfComparator()
        metadata = comparator.get_tool_metadata()
        
        assert metadata['@type'] == 'SoftwareApplication'
        assert 'VCF Comparator' in metadata['name']
        assert 'version' in metadata


# ============================================================================
# PARAMETRIZED TESTS
# ============================================================================

class TestVcfParametrized:
    """Parametrized tests for VCF comparison"""
    
    @pytest.mark.parametrize("mode", ['positions', 'genotypes', 'full'])
    def test_all_modes_identical_files(self, identical_vcf_files, mode):
        """Test all comparison modes with identical files"""
        file1, file2 = identical_vcf_files
        comparator = VcfComparator()
        
        result = comparator.compare(str(file1), str(file2), {'mode': mode})
        
        assert result['match'] == True
        assert result['verdict'] == 'PASS'
        assert result['mode'] == mode
    
    @pytest.mark.parametrize("tolerance,expected_diffs", [
        (0.001, 2),  # Strict - both quality differences detected
        (0.05, 1),   # Medium - only the larger difference detected
        (0.2, 0),    # Relaxed - no differences
    ])
    def test_quality_tolerance_levels(self, different_quality_vcf, tolerance, expected_diffs):
        """Test different quality tolerance levels"""
        file1, file2 = different_quality_vcf
        comparator = VcfComparator()
        
        result = comparator.compare(str(file1), str(file2), {
            'mode': 'genotypes',
            'quality_tolerance': tolerance
        })
        
        assert result['summary']['quality_differences'] == expected_diffs


# ============================================================================
# INTEGRATION TESTS
# ============================================================================

class TestVcfIntegration:
    """Integration tests for VCF comparator"""
    
    def test_vcf_in_comparison_manager(self, identical_vcf_files):
        """Test VCF comparator integration with ComparisonManager"""
        from comparators.manager import ComparisonManager
        
        file1, file2 = identical_vcf_files
        manager = ComparisonManager()
        
        # Set config for VCF files
        manager.set_comparison_config('*.vcf', {
            'mode': 'genotypes',
            'quality_tolerance': 0.01
        })
        
        result = manager.compare_files(str(file1), str(file2))
        
        assert result['match'] == True
        assert result['method'] == 'vcf_comparison'
    
    def test_multiple_bioinfo_types(self, identical_vcf_files, temp_dir):
        """Test handling multiple bioinformatics file types together"""
        from comparators.manager import ComparisonManager
        
        # Create a FASTA file too
        fasta_content = ">seq1\nATCG\n"
        fasta1 = temp_dir / 'seq1.fasta'
        fasta2 = temp_dir / 'seq2.fasta'
        fasta1.write_text(fasta_content)
        fasta2.write_text(fasta_content)
        
        manager = ComparisonManager()
        
        # Configure both types
        manager.set_comparison_config('*.vcf', {'mode': 'positions'})
        manager.set_comparison_config('*.fasta', {'mode': 'unordered'})
        
        # Test VCF
        vcf1, vcf2 = identical_vcf_files
        result = manager.compare_files(str(vcf1), str(vcf2))
        assert result['method'] == 'vcf_comparison'
        assert result['match'] == True
        
        # Test FASTA
        result = manager.compare_files(str(fasta1), str(fasta2))
        assert result['method'] == 'fasta_comparison'
        assert result['match'] == True