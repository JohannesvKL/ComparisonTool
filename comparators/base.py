from abc import ABC, abstractmethod
from typing import Dict, Any

class FileComparator(ABC):
    """Base class for all file comparators"""
    
    @abstractmethod
    def can_compare(self, file_path: str) -> bool:
        """Check if this comparator can handle this file type"""
        pass
    
    @abstractmethod
    def compare(self, file1: str, file2: str, config: Dict) -> Dict[str, Any]:
        """Compare two files and return structured results"""
        pass
    
    @abstractmethod
    def get_tool_metadata(self) -> Dict[str, Any]:
        """Return metadata about the comparison tool for RO-Crate"""
        pass
    
    def get_comparison_type(self) -> str:
        """Return the Schema.org action type for this comparison"""
        return "AssessAction"