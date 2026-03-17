from typing import List, Dict, Any, Optional
import fnmatch
import yaml
from pathlib import Path
from .base import FileComparator
from .binary import BinaryComparator
from .tabular import TabularComparator
from .image import ImageComparator
from .hdf5 import HDF5Comparator
from .bioinfo import FastaComparator, BamComparator, VcfComparator
from .generic import GenericComparator


class ComparisonManager:
    """Manages multiple comparators and selects the right one"""
    
    def __init__(self, create_crates: bool = False, crate_output_dir: str = None):
        """
        Initialize comparison manager
        
        Args:
            create_crates: Whether to automatically create RO-Crates
            crate_output_dir: Directory for RO-Crate output
        """
        self.comparators: List[FileComparator] = [
            TabularComparator(),
            ImageComparator(),
            HDF5Comparator(),
            FastaComparator(),
            BamComparator(),
            VcfComparator(), 
            BinaryComparator(),  # Fallback
            GenericComparator(), 
        ]
        self.comparison_configs = {}
        self.create_crates = create_crates
        self.crate_output_dir = crate_output_dir
        
        # Initialize crate manager if needed
        if create_crates:
            from rocrate import CrateManager
            self.crate_manager = CrateManager(crate_output_dir or "./comparison-crates")
        else:
            self.crate_manager = None
    
    @classmethod
    def from_config(cls, config_path: str) -> 'ComparisonManager':
        """
        Construct a ComparisonManager from a YAML config file.

        Expected format:
            comparators:
              "*.csv":
                type: tabular
                tolerance: 1e-6
                check_column_order: false
              "*.png":
                type: image
                method: pixel
                tolerance: 0.01
              "*.bam":
                type: bam
              "*.vcf":
                type: vcf

        Supported types: tabular, image, hdf5, fasta, bam, vcf, binary
        Any file patterns not listed will fall back to the default comparator order.
        """
        # Map config type names to comparator classes
        TYPE_MAP = {
            'tabular': TabularComparator,
            'image':   ImageComparator,
            'hdf5':    HDF5Comparator,
            'fasta':   FastaComparator,
            'bam':     BamComparator,
            'vcf':     VcfComparator,
            'binary':  BinaryComparator,
            'generic': GenericComparator, 
        }

        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)

        instance = cls()

        for pattern, settings in config.get('comparators', {}).items():
            settings = settings or {}
            comparator_type = settings.pop('type', None)

            if comparator_type is None:
                raise ValueError(f"Missing 'type' for pattern '{pattern}' in {config_path}")
            if comparator_type not in TYPE_MAP:
                raise ValueError(
                    f"Unknown comparator type '{comparator_type}' for pattern '{pattern}'. "
                    f"Valid types are: {', '.join(TYPE_MAP)}"
                )

            # Any remaining settings become the per-pattern comparison config
            if settings:
                instance.set_comparison_config(pattern, settings)

        return instance

    def register_comparator(self, comparator: FileComparator, priority: int = -1):
        """Register a new comparator"""
        if priority < 0:
            self.comparators.append(comparator)
        else:
            self.comparators.insert(priority, comparator)

    def get_comparator(self, filepath: str) -> Optional[FileComparator]:
        """
        Return the first comparator that can handle the given file,
        or None if no match is found.
        """
        for comparator in self.comparators:
            if comparator.can_compare(filepath):
                return comparator
        return None
    
    def set_comparison_config(self, pattern: str, config: Dict):
        """Set configuration for files matching pattern"""
        self.comparison_configs[pattern] = config
    
    def get_config_for_file(self, filepath: str) -> Dict:
        """Get configuration for a specific file"""
        for pattern, config in self.comparison_configs.items():
            if fnmatch.fnmatch(filepath, pattern):
                return config
        return {}
    
    def compare_files(self, file1: str, file2: str, 
                     config: Dict = None,
                     metadata: Dict[str, Any] = None, 
                     custom: bool = False) -> Dict[str, Any]:
        """
        Compare two files using appropriate comparator
        
        Args:
            file1: First file path
            file2: Second file path
            config: Optional configuration override
            metadata: Optional metadata for RO-Crate (creator, description, etc.)
        
        Returns:
            Comparison result dictionary
        """
        # Get config
        if config is None:
            config = self.get_config_for_file(file1)
        
        #Handling for manual case 
        if custom: 
            try:
                comparator = GenericComparator()
                result = comparator.compare(file1, file2, config)
            except Exception as e:
                    return {
                        'match': False,
                        'method': comparator.__class__.__name__,
                        'verdict': 'ERROR',
                        'reason': f'{type(e).__name__}: {e}',
                        'tool_metadata': comparator.get_tool_metadata()
                    }
        
            result['tool_metadata'] = comparator.get_tool_metadata()
                
            # Create RO-Crate if requested
            if self.create_crates and self.crate_manager:
                crate = self.crate_manager.create_comparison_crate(
                    file1, file2,
                    result['method'],
                    result,
                    config,
                    metadata
                )
                
                crate_dir = self.crate_manager.save_crate(
                    crate,
                    include_files=True,
                    file_paths=[file1, file2]
                )
                
                result['crate_path'] = str(crate_dir)
            
            return result

        # Find appropriate comparator
        for comparator in self.comparators:
            if comparator.can_compare(file1):
                try:
                    result = comparator.compare(file1, file2, config)
                except Exception as e:
                    return {
                        'match': False,
                        'method': comparator.__class__.__name__,
                        'verdict': 'ERROR',
                        'reason': f'{type(e).__name__}: {e}',
                        'tool_metadata': comparator.get_tool_metadata()
                    }

                # Add tool metadata
                result['tool_metadata'] = comparator.get_tool_metadata()
                
                # Create RO-Crate if requested
                if self.create_crates and self.crate_manager:
                    crate = self.crate_manager.create_comparison_crate(
                        file1, file2,
                        result['method'],
                        result,
                        config,
                        metadata
                    )
                    
                    crate_dir = self.crate_manager.save_crate(
                        crate,
                        include_files=True,
                        file_paths=[file1, file2]
                    )
                    
                    result['crate_path'] = str(crate_dir)
                
                return result
        
        # No comparator found
        return {
            'match': False,
            'method': 'none',
            'verdict': 'ERROR',
            'reason': f'No comparator found for file: {file1}'
        }
    
    def batch_compare(self, file_pairs: List[tuple],
                     metadata: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """
        Compare multiple file pairs
        
        Args:
            file_pairs: List of (file1, file2) tuples
            metadata: Optional metadata for all comparisons
        
        Returns:
            List of comparison results
        """
        if self.create_crates and self.crate_manager:
            return self.crate_manager.batch_compare(
                file_pairs,
                self,
                create_crates=True,
                save_crates=True
            )
        else:
            return [self.compare_files(f1, f2, metadata=metadata) 
                    for f1, f2 in file_pairs]