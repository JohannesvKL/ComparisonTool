"""Compare self-contained HDF5 trees, datasets and scientific metadata."""
from .base import FileComparator
from .array_values import array_difference


class HDF5Comparator(FileComparator):
    def can_compare(self, file_path):
        return file_path.lower().endswith(('.h5', '.hdf5'))

    @staticmethod
    def _objects(root):
        import h5py
        objects, seen = {}, set()

        def visit(obj, path):
            address = h5py.h5o.get_info(obj.id).addr
            if address in seen:
                raise ValueError(f'{path}: hard-link aliases/cycles are unsupported; export a tree.')
            seen.add(address)
            objects[path] = obj
            if isinstance(obj, h5py.Group):
                for name in sorted(obj):
                    child = path.rstrip('/') + '/' + name
                    if not isinstance(obj.get(name, getlink=True), h5py.HardLink):
                        raise ValueError(f'{child}: soft/external links are unsupported; export self-contained data.')
                    visit(obj[name], child)
            elif isinstance(obj, h5py.Dataset):
                if obj.is_virtual or obj.external:
                    raise ValueError(f'{path}: virtual/external datasets are unsupported; materialize the data.')
                if obj.dtype.fields or obj.dtype.kind == 'V' or (
                    obj.dtype.kind == 'O' and h5py.check_string_dtype(obj.dtype) is None
                ):
                    raise ValueError(f'{path}: compound, opaque, reference and ragged numeric datasets are unsupported.')
            else:
                raise ValueError(f'{path}: named HDF5 datatypes are unsupported.')

        visit(root, '/')
        return objects

    def compare(self, file1, file2, config):
        import h5py
        settings = {'rtol': float(config.get('rtol', 1e-5)),
                    'atol': float(config.get('atol', 1e-8)),
                    'equal_nan': config.get('equal_nan', False),
                    'check_dtype': config.get('check_dtype', True),
                    'check_attributes': config.get('check_attributes', True)}
        differences, datasets_compared, attributes_compared = [], 0, 0
        value_settings = {k: v for k, v in settings.items() if k != 'check_attributes'}

        def values(a, b, path):
            if isinstance(a, h5py.Empty) or isinstance(b, h5py.Empty):
                if not (isinstance(a, h5py.Empty) and isinstance(b, h5py.Empty)):
                    differences.append(f'{path}: null dataspace differs')
                elif settings['check_dtype'] and a.dtype != b.dtype:
                    differences.append(f'{path}: dtype differs: {a.dtype} vs {b.dtype}')
                return
            difference = array_difference(a, b, string_objects=True, **value_settings)
            if difference:
                differences.append(f'{path}: {difference}')

        with h5py.File(file1, 'r') as f1, h5py.File(file2, 'r') as f2:
            left, right = self._objects(f1), self._objects(f2)
            for path in sorted(left.keys() | right.keys()):
                if path not in left or path not in right:
                    differences.append(f'{path}: object missing from one output')
                    continue
                a, b = left[path], right[path]
                if type(a) is not type(b):
                    differences.append(f'{path}: group/dataset type differs')
                    continue
                if isinstance(a, h5py.Dataset):
                    datasets_compared += 1
                    # String encoding and enum labels are part of the schema;
                    # plain NumPy dtype equality ignores this HDF5 metadata.
                    if settings['check_dtype'] and (
                        a.dtype != b.dtype or a.dtype.metadata != b.dtype.metadata
                    ):
                        differences.append(f'{path}: dtype differs: {a.dtype} vs {b.dtype} (including HDF5 metadata)')
                    elif a.shape != b.shape:
                        differences.append(f'{path}: shape differs: {a.shape} vs {b.shape}')
                    else:
                        values(a[()], b[()], path)
                if settings['check_attributes']:
                    for key in sorted(a.attrs.keys() | b.attrs.keys()):
                        label = f'{path} attribute {key!r}'
                        if key not in a.attrs or key not in b.attrs:
                            differences.append(f'{label}: missing from one output')
                        else:
                            attributes_compared += 1
                            for attrs in (a.attrs, b.attrs):
                                dtype = attrs.get_id(key).dtype
                                if dtype.fields or dtype.kind == 'V' or (
                                    dtype.kind == 'O' and h5py.check_string_dtype(dtype) is None
                                ):
                                    raise ValueError(f'{label}: compound, opaque, reference and ragged numeric attributes are unsupported.')
                            if settings['check_dtype'] and (
                                a.attrs.get_id(key).dtype != b.attrs.get_id(key).dtype or
                                a.attrs.get_id(key).dtype.metadata != b.attrs.get_id(key).dtype.metadata
                            ):
                                differences.append(f'{label}: dtype differs (including HDF5 metadata)')
                            else:
                                values(a.attrs[key], b.attrs[key], label)
        return {'match': not differences, 'method': 'hdf5_comparison',
                'configuration': settings,
                'summary': {'datasets_compared': datasets_compared,
                            'attributes_compared': attributes_compared,
                            'differences_found': len(differences)},
                'differences': differences, 'verdict': 'FAIL' if differences else 'PASS',
                'reason': f'{len(differences)} differences found' if differences else None}

    def get_tool_metadata(self):
        import h5py
        return {'@type': 'SoftwareApplication', 'name': 'h5py', 'version': h5py.__version__,
                'url': 'https://www.h5py.org/', 'applicationCategory': 'HDF5 comparison'}
