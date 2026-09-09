"""Compare NumPy arrays without unpickling object arrays."""
import numpy as np
from .base import FileComparator
from .array_values import array_difference


class NumpyComparator(FileComparator):
    def can_compare(self, path):
        return path.lower().endswith(('.npy', '.npz'))

    def compare(self, file1, file2, config):
        def read(path):
            loaded = np.load(path, allow_pickle=False)
            if isinstance(loaded, np.lib.npyio.NpzFile):
                try:
                    if len(loaded.files) != len(set(loaded.files)):
                        raise ValueError('Duplicate array names in NPZ archive')
                    return {key: loaded[key] for key in loaded.files}
                finally:
                    loaded.close()
            return {'array': loaded}
        arrays1, arrays2 = read(file1), read(file2)
        atol, rtol = float(config.get('atol', 0)), float(config.get('rtol', 0))
        equal_nan, check_dtype = config.get('equal_nan', False), config.get('check_dtype', True)
        differences = []
        for key in sorted(arrays1.keys() | arrays2.keys()):
            if key not in arrays1 or key not in arrays2:
                differences.append(f'{key}: array missing')
                continue
            difference = array_difference(arrays1[key], arrays2[key], atol=atol, rtol=rtol,
                                          equal_nan=equal_nan, check_dtype=check_dtype)
            if difference:
                differences.append(f'{key}: {difference}')
        return {'match': not differences, 'verdict': 'FAIL' if differences else 'PASS', 'method': 'numpy_arrays',
                'configuration': {'atol': atol, 'rtol': rtol, 'equal_nan': equal_nan, 'check_dtype': check_dtype},
                'metrics': {'arrays_compared': len(arrays1.keys() & arrays2.keys()), 'differences': len(differences)},
                'differences': differences, 'reason': '; '.join(differences[:20]) if differences else None}

    def get_tool_metadata(self):
        return {'@type': 'SoftwareApplication', 'name': 'NumPy Array Comparator', 'version': np.__version__}
