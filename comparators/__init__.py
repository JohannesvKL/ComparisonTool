from .base import FileComparator
from .binary import BinaryComparator
from .tabular import TabularComparator
from .image import ImageComparator
from .hdf5 import HDF5Comparator
from .manager import ComparisonManager
from .comparison_cli import compare
from .generic import GenericComparator

# Bioinformatics comparators
from .bioinfo import (
    FastaComparator,
    BamComparator,
    VcfComparator,
)

__version__ = "0.1.0"

__all__ = [
    'FileComparator',
    'BinaryComparator',
    'TabularComparator',
    'ImageComparator',
    'HDF5Comparator',
    'ComparisonManager',
    'FastaComparator',
    'BamComparator',
    'VcfComparator',
    'GenericComparator'
]