# Easy to add a new comparator!
from ComparatorBeta import FileComparator
from typing import Dict, Any

class JSONComparator(FileComparator):
    """Compare JSON files with tolerance for floats"""
    
    def can_compare(self, file_path: str) -> bool:
        return file_path.endswith('.json')
    
    def compare(self, file1: str, file2: str, config: Dict) -> Dict[str, Any]:
        import json
        
        with open(file1) as f:
            data1 = json.load(f)
        with open(file2) as f:
            data2 = json.load(f)
        
        # Compare with tolerance for numeric values
        differences = self._deep_compare(data1, data2, config.get('tolerance', 1e-6))
        
        return {
            'match': len(differences) == 0,
            'method': 'json_comparison',
            'differences': differences,
            'verdict': 'PASS' if len(differences) == 0 else 'FAIL',
            'reason': None if len(differences) == 0 else f'{len(differences)} differences found'
        }
    
    def get_tool_metadata(self) -> Dict[str, Any]:
        return {
            '@type': 'SoftwareApplication',
            'name': 'JSON Comparator',
            'applicationCategory': 'JSON comparison'
        }
    
    def _deep_compare(self, obj1, obj2, tolerance, path=''):
        # Implementation of deep comparison with tolerance
        pass
