import hashlib
from typing import Dict, Any
from .base import FileComparator


class BinaryComparator(FileComparator):
    """Checksum-based binary comparison"""
    
    def can_compare(self, file_path: str) -> bool:
        # Can compare any file
        return True
    
    def compare(self, file1: str, file2: str, config: Dict) -> Dict[str, Any]:
        hash1 = self._compute_sha256(file1)
        hash2 = self._compute_sha256(file2)
        
        return {
            'match': hash1 == hash2,
            'method': 'sha256_checksum',
            'file1_hash': hash1,
            'file2_hash': hash2,
            'verdict': 'PASS' if hash1 == hash2 else 'FAIL',
            'reason': None if hash1 == hash2 else 'Checksums differ'
        }
    
    def get_tool_metadata(self) -> Dict[str, Any]:
        return {
            '@type': 'SoftwareApplication',
            'name': 'SHA256 Checksum',
            'version': 'hashlib',
            'applicationCategory': 'Binary comparison'
        }
    
    def _compute_sha256(self, filepath: str) -> str:
        sha256_hash = hashlib.sha256()
        with open(filepath, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()