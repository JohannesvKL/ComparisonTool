"""Select comparators by explicit configuration, then by format."""
import fnmatch
from .base import FileComparator
from .binary import BinaryComparator
from .tabular import TabularComparator
from .image import ImageComparator
from .hdf5 import HDF5Comparator
from .bioinfo import FastaComparator, BamComparator, VcfComparator
from .generic import GenericComparator
from .config import load_config, validate_settings
from .json_data import JsonComparator
from .numpy_data import NumpyComparator

TYPE_MAP = {
    'tabular': TabularComparator, 'image': ImageComparator, 'hdf5': HDF5Comparator,
    'fasta': FastaComparator, 'bam': BamComparator, 'vcf': VcfComparator,
    'binary': BinaryComparator, 'generic': GenericComparator,
    'json': JsonComparator, 'numpy': NumpyComparator,
}


class ComparisonManager:
    def __init__(self, create_crates=False, crate_output_dir=None):
        if create_crates or crate_output_dir is not None:
            raise ValueError('Per-file crate management is unsupported; use compare directory --crate or ComparisonCrateWriter.')
        self.comparators = [TabularComparator(), ImageComparator(), HDF5Comparator(),
                            FastaComparator(), BamComparator(), VcfComparator(), JsonComparator(), NumpyComparator(), BinaryComparator()]
        self.comparison_configs = {}
        self.comparator_types = {}

    @classmethod
    def from_config(cls, config_path):
        config = load_config(config_path)
        instance = cls()
        for pattern, entry in config.get('comparators', {}).items():
            settings = dict(entry)
            kind = settings.pop('type', None)
            if not isinstance(kind, str) or kind not in TYPE_MAP:
                raise ValueError(f"Invalid comparator type {kind!r} for {pattern!r}; choose from {', '.join(TYPE_MAP)}.")
            if kind == 'generic' and not settings.get('user_comparison'):
                raise ValueError(f"Generic comparator for {pattern!r} requires user_comparison.")
            instance.comparator_types[pattern] = TYPE_MAP[kind]()
            instance.set_comparison_config(pattern, settings)
        return instance

    def register_comparator(self, comparator, priority=-1):
        if priority < 0:
            # New comparators must precede the binary catch-all.
            priority = next((i for i, c in enumerate(self.comparators) if isinstance(c, BinaryComparator)), len(self.comparators))
        self.comparators.insert(priority, comparator)

    def get_comparator(self, filepath):
        for pattern, comparator in self.comparator_types.items():
            if fnmatch.fnmatchcase(str(filepath), pattern):
                return comparator
        return next((c for c in self.comparators if c.can_compare(str(filepath))), None)

    def set_comparison_config(self, pattern, config):
        self.comparison_configs[pattern] = dict(config)

    def get_config_for_file(self, filepath):
        for pattern, config in self.comparison_configs.items():
            if fnmatch.fnmatchcase(str(filepath), pattern):
                return dict(config)
        return {}

    def compare_files(self, file1, file2, config=None, metadata=None, custom=False, lookup_path=None):
        """lookup_path is the run1 path relative to the scan directory for YAML matching."""
        lookup_path = lookup_path or str(file1)
        config = self.get_config_for_file(lookup_path) if config is None else config
        comparator = GenericComparator() if custom else self.get_comparator(lookup_path)
        if comparator is None:
            return {'match': False, 'method': 'none', 'verdict': 'ERROR',
                    'reason': f'No comparator found for {file1}', 'tool_metadata': {}}
        try:
            kind = next((k for k, cls in TYPE_MAP.items() if type(comparator) is cls), None)
            if kind:
                config = validate_settings(kind, dict(config))
            result = comparator.compare(str(file1), str(file2), config)
        except Exception as exc:
            result = {'match': False, 'method': type(comparator).__name__, 'verdict': 'ERROR',
                      'reason': f'{type(exc).__name__}: {exc}'}
        try:
            result['tool_metadata'] = comparator.get_tool_metadata()
        except Exception:
            result['tool_metadata'] = {'name': type(comparator).__name__}
        result.setdefault('verdict', 'PASS' if result['match'] else 'FAIL')
        result.setdefault('configuration', config)
        return result

    def batch_compare(self, file_pairs, metadata=None):
        return [self.compare_files(f1, f2, metadata=metadata) for f1, f2 in file_pairs]
