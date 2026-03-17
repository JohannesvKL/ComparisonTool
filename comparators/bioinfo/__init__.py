"""
Bioinformatics-specific file comparators
"""

from .fasta import FastaComparator
from .bam import BamComparator
from .vcf import VcfComparator

__all__ = [
    'FastaComparator',
    'BamComparator',
    'VcfComparator',
]