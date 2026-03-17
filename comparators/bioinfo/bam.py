"""
BAM/SAM file comparator using pysam
"""

from typing import Dict, Any, Tuple
import hashlib
import sys
sys.path.append('..')
from comparators.base import FileComparator


class BamComparator(FileComparator):
    """
    Compare BAM/SAM alignment files
    
    Comparison modes:
    - binary: Fast binary comparison (checksums)
    - header: Compare only headers
    - full: Compare headers and all alignments (memory intensive!)
    - sample: Compare headers and sample N alignments
    """
    
    def can_compare(self, file_path: str) -> bool:
        """Check if file is BAM/SAM format"""
        return file_path.endswith(('.bam', '.sam', '.cram'))
    
    def compare(self, file1: str, file2: str, config: Dict) -> Dict[str, Any]:
        """
        Compare two BAM/SAM files
        
        Config options:
            mode: 'binary' | 'header' | 'sample' | 'full' (default: 'sample')
            sample_size: int (default: 10000) - for 'sample' mode
            ignore_pg: bool (default: True) - ignore @PG (program) header lines
            ignore_read_groups: bool (default: False) - ignore @RG lines
            check_order: bool (default: False) - require same order (slower if False)
        """
        try:
            import pysam
        except ImportError:
            return {
                'match': False,
                'method': 'bam_comparison',
                'verdict': 'ERROR',
                'reason': 'pysam not installed. Install with: pip install pysam'
            }
        
        # Get configuration
        mode = config.get('mode', 'sample')
        sample_size = config.get('sample_size', 10000)
        ignore_pg = config.get('ignore_pg', True)
        ignore_read_groups = config.get('ignore_read_groups', False)
        check_order = config.get('check_order', False)
        
        # Binary comparison (fastest)
        if mode == 'binary':
            return self._compare_binary(file1, file2)
        
        # Open BAM files
        try:
            bam1 = pysam.AlignmentFile(file1, 'rb')
            bam2 = pysam.AlignmentFile(file2, 'rb')
        except Exception as e:
            return {
                'match': False,
                'method': 'bam_comparison',
                'verdict': 'ERROR',
                'reason': f'Failed to open BAM files: {e}'
            }
        
        # Compare headers
        header_match, header_info = self._compare_headers(
            bam1.header, bam2.header, ignore_pg, ignore_read_groups
        )
        
        # Depending on mode, compare alignments
        if mode == 'header':
            alignments_match = True
            alignment_info = {'mode': 'header_only'}
        elif mode == 'sample':
            alignments_match, alignment_info = self._compare_sample_alignments(
                bam1, bam2, sample_size, check_order
            )
        elif mode == 'full':
            alignments_match, alignment_info = self._compare_all_alignments(
                bam1, bam2, check_order
            )
        else:
            bam1.close()
            bam2.close()
            return {
                'match': False,
                'method': 'bam_comparison',
                'verdict': 'ERROR',
                'reason': f"Unknown mode: {mode}"
            }
        
        bam1.close()
        bam2.close()
        
        match = header_match and alignments_match
        
        return {
            'match': match,
            'method': 'bam_comparison',
            'mode': mode,
            'configuration': {
                'ignore_pg': ignore_pg,
                'ignore_read_groups': ignore_read_groups,
                'check_order': check_order,
                'sample_size': sample_size if mode == 'sample' else None
            },
            'summary': {
                'header_matches': header_match,
                'alignments_match': alignments_match,
                **header_info,
                **alignment_info
            },
            'verdict': 'PASS' if match else 'FAIL',
            'reason': self._build_failure_reason(header_match, alignments_match, header_info, alignment_info)
        }
    
    def _compare_binary(self, file1: str, file2: str) -> Dict[str, Any]:
        """Fast binary comparison using checksums"""
        hash1 = self._compute_checksum(file1)
        hash2 = self._compute_checksum(file2)
        
        match = hash1 == hash2
        
        return {
            'match': match,
            'method': 'bam_comparison',
            'mode': 'binary',
            'checksums': {
                'file1': hash1,
                'file2': hash2
            },
            'verdict': 'PASS' if match else 'FAIL',
            'reason': None if match else 'Binary content differs'
        }
    
    def _compute_checksum(self, filepath: str) -> str:
        """Compute SHA256 checksum"""
        sha256_hash = hashlib.sha256()
        with open(filepath, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()
    
    def _compare_headers(self, header1, header2, ignore_pg: bool, 
                        ignore_rg: bool) -> Tuple[bool, Dict]:
        """Compare BAM headers"""
        import copy
        
        # Convert to dicts
        h1 = header1.to_dict()
        h2 = header2.to_dict()
        
        # Optionally remove @PG (program) lines
        if ignore_pg:
            h1 = {k: v for k, v in h1.items() if k != 'PG'}
            h2 = {k: v for k, v in h2.items() if k != 'PG'}
        
        # Optionally remove @RG (read group) lines
        if ignore_rg:
            h1 = {k: v for k, v in h1.items() if k != 'RG'}
            h2 = {k: v for k, v in h2.items() if k != 'RG'}
        
        # Compare
        match = h1 == h2
        
        info = {
            'header_pg_ignored': ignore_pg,
            'header_rg_ignored': ignore_rg,
            'header_keys_file1': list(header1.to_dict().keys()),
            'header_keys_file2': list(header2.to_dict().keys())
        }
        
        return match, info
    
    def _compare_sample_alignments(self, bam1, bam2, sample_size: int, 
                                   check_order: bool) -> Tuple[bool, Dict]:
        """Compare a sample of alignments"""
        # Read sample
        alignments1 = []
        alignments2 = []
        
        for i, read in enumerate(bam1):
            if i >= sample_size:
                break
            alignments1.append(self._alignment_signature(read))
        
        for i, read in enumerate(bam2):
            if i >= sample_size:
                break
            alignments2.append(self._alignment_signature(read))
        
        # Compare
        if check_order:
            # Order matters
            match = alignments1 == alignments2
            info = {
                'sample_size': min(len(alignments1), len(alignments2)),
                'alignments_file1': len(alignments1),
                'alignments_file2': len(alignments2),
                'comparison_type': 'ordered'
            }
        else:
            # Order doesn't matter - compare as sets
            set1 = set(alignments1)
            set2 = set(alignments2)
            
            only_in_1 = len(set1 - set2)
            only_in_2 = len(set2 - set1)
            
            match = only_in_1 == 0 and only_in_2 == 0
            
            info = {
                'sample_size': min(len(alignments1), len(alignments2)),
                'unique_alignments_file1': len(set1),
                'unique_alignments_file2': len(set2),
                'alignments_only_in_file1': only_in_1,
                'alignments_only_in_file2': only_in_2,
                'comparison_type': 'unordered'
            }
        
        return match, info
    
    def _compare_all_alignments(self, bam1, bam2, check_order: bool) -> Tuple[bool, Dict]:
        """Compare all alignments (memory intensive!)"""
        # Warning: This loads all alignments into memory
        # For large BAM files, this could use gigabytes of RAM
        
        alignments1 = [self._alignment_signature(read) for read in bam1]
        alignments2 = [self._alignment_signature(read) for read in bam2]
        
        if check_order:
            match = alignments1 == alignments2
            info = {
                'total_alignments_file1': len(alignments1),
                'total_alignments_file2': len(alignments2),
                'comparison_type': 'ordered'
            }
        else:
            set1 = set(alignments1)
            set2 = set(alignments2)
            
            only_in_1 = len(set1 - set2)
            only_in_2 = len(set2 - set1)
            
            match = only_in_1 == 0 and only_in_2 == 0
            
            info = {
                'total_alignments_file1': len(alignments1),
                'total_alignments_file2': len(alignments2),
                'unique_alignments_file1': len(set1),
                'unique_alignments_file2': len(set2),
                'alignments_only_in_file1': only_in_1,
                'alignments_only_in_file2': only_in_2,
                'comparison_type': 'unordered'
            }
        
        return match, info
    
    def _alignment_signature(self, read) -> Tuple:
        """Create hashable signature for an alignment"""
        return (
            read.query_name,
            read.reference_name,
            read.reference_start,
            read.cigarstring,
            read.flag,
            read.mapping_quality,
            read.query_sequence
        )
    
    def _build_failure_reason(self, header_match, alignments_match, 
                             header_info, alignment_info):
        """Build failure reason message"""
        if not header_match and not alignments_match:
            return "Both headers and alignments differ"
        elif not header_match:
            return "Headers differ"
        elif not alignments_match:
            if 'alignments_only_in_file1' in alignment_info:
                return (f"{alignment_info['alignments_only_in_file1']} alignments only in file1, "
                       f"{alignment_info['alignments_only_in_file2']} only in file2")
            else:
                return "Alignments differ"
        return None
    
    def get_tool_metadata(self) -> Dict[str, Any]:
        """Return metadata about pysam"""
        try:
            import pysam
            version = pysam.__version__
        except:
            version = "not installed"
        
        return {
            '@type': 'SoftwareApplication',
            'name': 'pysam',
            'version': version,
            'url': 'https://pysam.readthedocs.io/',
            'applicationCategory': 'BAM/SAM file comparison'
        }