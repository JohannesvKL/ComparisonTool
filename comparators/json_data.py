"""Semantic JSON comparison: unordered object keys, ordered arrays, numeric tolerances."""
from decimal import Decimal
from fractions import Fraction
import json
from .base import FileComparator


class JsonComparator(FileComparator):
    def can_compare(self, path):
        return path.lower().endswith('.json')

    def compare(self, file1, file2, config):
        def invalid(value):
            raise ValueError(f'Non-standard JSON constant: {value}')
        def unique(items):
            result = {}
            for key, value in items:
                if key in result:
                    raise ValueError(f'Duplicate JSON key: {key}')
                result[key] = value
            return result
        def read(path):
            with open(path, encoding='utf-8') as handle:
                return json.load(handle, parse_float=Decimal, parse_constant=invalid, object_pairs_hook=unique)
        left, right = read(file1), read(file2)
        atol, rtol = Fraction(str(config.get('abs_tol', 0))), Fraction(str(config.get('rel_tol', 0)))
        differences = []
        total = 0
        def differ(path, reason):
            nonlocal total
            total += 1
            if len(differences) < 20:
                differences.append({'path': path or '/', 'reason': reason})
        def walk(a, b, path=''):
            if isinstance(a, (int, Decimal)) and not isinstance(a, bool) and isinstance(b, (int, Decimal)) and not isinstance(b, bool):
                # Integers stay exact; avoid floating conversion of large identifiers.
                # Fractions also preserve decimals beyond Decimal's default
                # arithmetic precision when evaluating the tolerance boundary.
                equal = a == b if isinstance(a, int) and isinstance(b, int) else abs(Fraction(a) - Fraction(b)) <= atol + rtol * max(abs(Fraction(a)), abs(Fraction(b)))
                if not equal:
                    differ(path, 'Numeric values differ')
            elif type(a) is not type(b):
                differ(path, 'JSON types differ')
            elif isinstance(a, dict):
                for key in sorted(a.keys() | b.keys()):
                    child = path + '/' + key.replace('~', '~0').replace('/', '~1')
                    if key not in a or key not in b:
                        differ(child, 'Key missing from one output')
                    else:
                        walk(a[key], b[key], child)
            elif isinstance(a, list):
                if len(a) != len(b):
                    differ(path, 'Array lengths differ')
                for index, (x, y) in enumerate(zip(a, b)):
                    walk(x, y, path + '/' + str(index))
            elif a != b:
                differ(path, 'Values differ')
        walk(left, right)
        return {'match': total == 0, 'verdict': 'PASS' if not total else 'FAIL', 'method': 'semantic_json',
                'configuration': {'abs_tol': float(atol), 'rel_tol': float(rtol)},
                'metrics': {'differences': total}, 'differences': differences,
                'reason': None if not total else f'{total} JSON differences (up to 20 shown)'}

    def get_tool_metadata(self):
        return {'@type': 'SoftwareApplication', 'name': 'Semantic JSON Comparator', 'version': '1'}
