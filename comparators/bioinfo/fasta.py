"""
FASTA file comparator using BioPython
"""

from typing import Dict, Any, Set, Tuple
import sys
sys.path.append('..')
from comparators.base import FileComparator


class FastaComparator(FileComparator):
    """
    Compare FASTA sequence files
    
    Supports multiple comparison modes:
    - exact: Sequences must be in same order with identical IDs and sequences
    - unordered: Same sequences but order doesn't matter
    - content_only: Only check if same sequences exist (ignore IDs)
    """
    
    def can_compare(self, file_path: str) -> bool:
        """Check if file is FASTA format"""
        return file_path.endswith(('.fasta', '.fa', '.fna', '.ffn', '.faa', '.frn'))
    
    def compare(self, file1: str, file2: str, config: Dict) -> Dict[str, Any]:
        """
        Compare two FASTA files
        
        Config options:
            mode: 'exact' | 'unordered' | 'content_only' (default: 'unordered')
            case_sensitive: bool (default: False)
            check_description: bool (default: False) - compare sequence descriptions
        """
        try:
            from Bio import SeqIO
        except ImportError:
            return {
                'match': False,
                'method': 'fasta_comparison',
                'verdict': 'ERROR',
                'reason': 'BioPython not installed. Install with: pip install biopython'
            }
        
        # Get configuration
        mode = config.get('mode', 'unordered')
        case_sensitive = config.get('case_sensitive', False)
        check_description = config.get('check_description', False)
        
        # Parse FASTA files
        try:
            records1 = list(SeqIO.parse(file1, "fasta"))
            records2 = list(SeqIO.parse(file2, "fasta"))
        except Exception as e:
            return {
                'match': False,
                'method': 'fasta_comparison',
                'verdict': 'ERROR',
                'reason': f'Failed to parse FASTA files: {e}'
            }
        
        # Choose comparison method
        if mode == 'exact':
            return self._compare_exact(records1, records2, case_sensitive, check_description)
        elif mode == 'unordered':
            return self._compare_unordered(records1, records2, case_sensitive, check_description)
        elif mode == 'content_only':
            return self._compare_content_only(records1, records2, case_sensitive)
        else:
            return {
                'match': False,
                'method': 'fasta_comparison',
                'verdict': 'ERROR',
                'reason': f"Unknown mode: {mode}. Use 'exact', 'unordered', or 'content_only'"
            }
    
    def _normalize_sequence(self, seq: str, case_sensitive: bool) -> str:
        """Normalize sequence for comparison"""
        return str(seq) if case_sensitive else str(seq).upper()
    
    def _compare_exact(self, records1, records2, case_sensitive: bool, 
                       check_description: bool) -> Dict[str, Any]:
        """Compare sequences in exact order"""
        if len(records1) != len(records2):
            return {
                'match': False,
                'method': 'fasta_comparison',
                'mode': 'exact',
                'summary': {
                    'sequences_file1': len(records1),
                    'sequences_file2': len(records2)
                },
                'verdict': 'FAIL',
                'reason': f'Different number of sequences: {len(records1)} vs {len(records2)}'
            }
        
        differences = []
        for i, (rec1, rec2) in enumerate(zip(records1, records2)):
            # Check ID
            if rec1.id != rec2.id:
                differences.append({
                    'position': i,
                    'type': 'id_mismatch',
                    'file1_id': rec1.id,
                    'file2_id': rec2.id
                })
            
            # Check description if requested
            if check_description and rec1.description != rec2.description:
                differences.append({
                    'position': i,
                    'type': 'description_mismatch',
                    'sequence_id': rec1.id
                })
            
            # Check sequence
            seq1 = self._normalize_sequence(rec1.seq, case_sensitive)
            seq2 = self._normalize_sequence(rec2.seq, case_sensitive)
            
            if seq1 != seq2:
                differences.append({
                    'position': i,
                    'type': 'sequence_mismatch',
                    'sequence_id': rec1.id,
                    'length1': len(seq1),
                    'length2': len(seq2)
                })
        
        match = len(differences) == 0
        
        return {
            'match': match,
            'method': 'fasta_comparison',
            'mode': 'exact',
            'configuration': {
                'case_sensitive': case_sensitive,
                'check_description': check_description
            },
            'summary': {
                'sequences_compared': len(records1),
                'differences_found': len(differences)
            },
            'differences': differences[:10],  # Limit to first 10
            'verdict': 'PASS' if match else 'FAIL',
            'reason': None if match else f'{len(differences)} differences found'
        }
    
    def _compare_unordered(self, records1, records2, case_sensitive: bool,
                          check_description: bool) -> Dict[str, Any]:
        """Compare sequences allowing different order"""
        # Build dictionaries keyed by sequence ID
        seqs1 = {}
        seqs2 = {}
        
        for rec in records1:
            seq = self._normalize_sequence(rec.seq, case_sensitive)
            seqs1[rec.id] = {
                'sequence': seq,
                'description': rec.description,
                'length': len(seq)
            }
        
        for rec in records2:
            seq = self._normalize_sequence(rec.seq, case_sensitive)
            seqs2[rec.id] = {
                'sequence': seq,
                'description': rec.description,
                'length': len(seq)
            }
        
        # Compare sets of IDs
        ids1 = set(seqs1.keys())
        ids2 = set(seqs2.keys())
        
        only_in_1 = ids1 - ids2
        only_in_2 = ids2 - ids1
        common = ids1 & ids2
        
        # Compare sequences for common IDs
        sequence_differences = []
        description_differences = []
        
        for seq_id in common:
            # Check sequences
            if seqs1[seq_id]['sequence'] != seqs2[seq_id]['sequence']:
                sequence_differences.append({
                    'sequence_id': seq_id,
                    'length1': seqs1[seq_id]['length'],
                    'length2': seqs2[seq_id]['length']
                })
            
            # Check descriptions if requested
            if check_description:
                if seqs1[seq_id]['description'] != seqs2[seq_id]['description']:
                    description_differences.append(seq_id)
        
        # Determine if match
        match = (
            len(only_in_1) == 0 and
            len(only_in_2) == 0 and
            len(sequence_differences) == 0 and
            (not check_description or len(description_differences) == 0)
        )
        
        return {
            'match': match,
            'method': 'fasta_comparison',
            'mode': 'unordered',
            'configuration': {
                'case_sensitive': case_sensitive,
                'check_description': check_description
            },
            'summary': {
                'sequences_in_common': len(common),
                'sequences_only_in_file1': len(only_in_1),
                'sequences_only_in_file2': len(only_in_2),
                'sequences_with_different_content': len(sequence_differences),
                'sequences_with_different_descriptions': len(description_differences) if check_description else 0
            },
            'sequences_only_in_file1': list(only_in_1)[:10],  # First 10
            'sequences_only_in_file2': list(only_in_2)[:10],
            'sequence_differences': sequence_differences[:10],
            'verdict': 'PASS' if match else 'FAIL',
            'reason': None if match else self._build_failure_reason(
                only_in_1, only_in_2, sequence_differences, description_differences
            )
        }
    
    def _compare_content_only(self, records1, records2, case_sensitive: bool) -> Dict[str, Any]:
        """Compare only sequence content, ignoring IDs"""
        # Extract just sequences
        seqs1 = set(self._normalize_sequence(rec.seq, case_sensitive) for rec in records1)
        seqs2 = set(self._normalize_sequence(rec.seq, case_sensitive) for rec in records2)
        
        only_in_1 = seqs1 - seqs2
        only_in_2 = seqs2 - seqs1
        common = seqs1 & seqs2
        
        match = len(only_in_1) == 0 and len(only_in_2) == 0
        
        return {
            'match': match,
            'method': 'fasta_comparison',
            'mode': 'content_only',
            'configuration': {
                'case_sensitive': case_sensitive
            },
            'summary': {
                'unique_sequences_in_common': len(common),
                'unique_sequences_only_in_file1': len(only_in_1),
                'unique_sequences_only_in_file2': len(only_in_2),
                'total_records_file1': len(records1),
                'total_records_file2': len(records2)
            },
            'verdict': 'PASS' if match else 'FAIL',
            'reason': None if match else f'{len(only_in_1)} sequences only in file1, {len(only_in_2)} only in file2'
        }
    
    def _build_failure_reason(self, only_in_1, only_in_2, seq_diffs, desc_diffs):
        """Build human-readable failure reason"""
        reasons = []
        if only_in_1:
            reasons.append(f'{len(only_in_1)} sequences only in file1')
        if only_in_2:
            reasons.append(f'{len(only_in_2)} sequences only in file2')
        if seq_diffs:
            reasons.append(f'{len(seq_diffs)} sequences differ')
        if desc_diffs:
            reasons.append(f'{len(desc_diffs)} descriptions differ')
        return ', '.join(reasons)
    
    def get_tool_metadata(self) -> Dict[str, Any]:
        """Return metadata about BioPython"""
        try:
            import Bio
            version = Bio.__version__
        except:
            version = "not installed"
        
        return {
            '@type': 'SoftwareApplication',
            'name': 'BioPython SeqIO',
            'version': version,
            'url': 'https://biopython.org/',
            'applicationCategory': 'Sequence file comparison'
        }