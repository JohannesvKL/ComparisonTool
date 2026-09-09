"""Strict validation for comparison policy and expected output declarations."""
import math
from pathlib import Path, PurePosixPath
import yaml


class UniqueKeyLoader(yaml.SafeLoader):
    pass


def _mapping(loader, node, deep=False):
    result = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if not isinstance(key, str):
            raise ValueError('YAML mapping keys must be strings.')
        if key in result:
            raise ValueError(f'Duplicate YAML key: {key}')
        result[key] = loader.construct_object(value_node, deep=deep)
    return result


UniqueKeyLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _mapping)

SETTINGS = {
    'binary': set(),
    'tabular': {'join_columns', 'abs_tol', 'rel_tol', 'comment', 'skiprows', 'required_columns'},
    'image': {'ssim_threshold', 'win_size'},
    'hdf5': {'rtol', 'atol', 'equal_nan', 'check_dtype', 'check_attributes'},
    'fasta': {'mode', 'case_sensitive', 'check_description'},
    'bam': {'mode', 'sample_size', 'ignore_pg', 'ignore_read_groups', 'check_order'},
    'vcf': {'mode', 'quality_tolerance', 'ignore_filters', 'ignore_info', 'ignore_format', 'sample_subset', 'check_order'},
    'generic': {'user_comparison', 'timeout'},
    'json': {'abs_tol', 'rel_tol'},
    'numpy': {'atol', 'rtol', 'equal_nan', 'check_dtype'},
}
MODES = {'fasta': {'exact', 'unordered', 'content_only'},
         'bam': {'binary', 'header', 'sample', 'full'},
         'vcf': {'positions', 'genotypes', 'full'}}
BOOLS = {'case_sensitive', 'check_description', 'ignore_pg', 'ignore_read_groups',
         'check_order', 'ignore_filters', 'ignore_info', 'ignore_format', 'equal_nan', 'check_dtype', 'check_attributes'}


def relative_path(value, label, allow_dot=False, allow_glob=False):
    if (not isinstance(value, str) or not value or '\\' in value or ':' in value
            or PurePosixPath(value).is_absolute() or '..' in PurePosixPath(value).parts
            or (not allow_dot and value == '.') or '//' in value
            or (not allow_glob and any(c in value for c in '*?[]'))):
        raise ValueError(f'{label} must be a relative POSIX path within a run.')
    normalized = PurePosixPath(value).as_posix()
    if normalized != value.rstrip('/'):
        raise ValueError(f'{label} must be normalized: {normalized}')
    return normalized


def _strings(value, label, nonempty=True):
    if not isinstance(value, list) or (nonempty and not value) or any(not isinstance(v, str) or not v for v in value):
        raise ValueError(f'{label} must be a list of nonempty strings.')
    if len(value) != len(set(value)):
        raise ValueError(f'{label} contains duplicates.')


def validate_settings(kind, settings):
    if not isinstance(kind, str) or kind not in SETTINGS:
        raise ValueError(f'Invalid comparator type {kind!r}; choose from {", ".join(SETTINGS)}.')
    unknown = set(settings) - SETTINGS[kind]
    if unknown:
        raise ValueError(f'Unknown {kind} settings: {", ".join(sorted(unknown))}. Allowed: {", ".join(sorted(SETTINGS[kind])) or "none"}.')
    for key, value in settings.items():
        if key in {'abs_tol', 'rel_tol', 'rtol', 'atol', 'quality_tolerance', 'timeout', 'ssim_threshold'}:
            # YAML 1.1 may parse scientific notation (1e-6) as a string.
            try:
                number = float(value) if not isinstance(value, bool) else float('nan')
            except (TypeError, ValueError, OverflowError):
                number = float('nan')
            if not math.isfinite(number) or number < 0 or (key == 'timeout' and number == 0) or (key == 'ssim_threshold' and number > 1):
                raise ValueError(f'Invalid {key}: use a finite nonnegative number' + (' in [0, 1].' if key == 'ssim_threshold' else ' (positive for timeout).'))
            settings[key] = number
        elif key in BOOLS and type(value) is not bool:
            raise ValueError(f'{key} must be true or false.')
        elif key in {'sample_size', 'win_size'}:
            if type(value) is not int or value < 1 or (key == 'win_size' and (value < 3 or value % 2 == 0)):
                raise ValueError(f'{key} must be a positive integer; win_size must be odd and at least 3.')
        elif key == 'mode' and (not isinstance(value, str) or value not in MODES[kind]):
            raise ValueError(f'Invalid {kind} mode: {value!r}.')
        elif key in {'required_columns', 'sample_subset'}:
            _strings(value, key)
        elif key == 'join_columns':
            if not isinstance(value, str):
                _strings(value, key)
            elif not value:
                raise ValueError('join_columns must not be empty.')
        elif key == 'comment' and value is not None and (not isinstance(value, str) or len(value) != 1):
            raise ValueError('comment must be one character or null.')
        elif key == 'skiprows':
            if not (type(value) is int and value >= 0) and not (isinstance(value, list) and all(type(v) is int and v >= 0 for v in value)):
                raise ValueError('skiprows must be a nonnegative integer or a list of nonnegative row indices.')
    if kind == 'generic':
        command = settings.get('user_comparison')
        if isinstance(command, str):
            if not command:
                raise ValueError('user_comparison cannot be empty.')
        else:
            if not isinstance(command, list) or not command or any(not isinstance(v, str) or not v for v in command):
                raise ValueError('user_comparison must be an executable or a nonempty argument list.')
    return settings


def required_for(config, side):
    required = config.get('required_outputs', [])
    return required.get(side, []) if isinstance(required, dict) else required


def load_config(path):
    try:
        config = yaml.load(Path(path).read_text(encoding='utf-8'), Loader=UniqueKeyLoader)
    except yaml.YAMLError as exc:
        raise ValueError(f'Invalid YAML in {path}: {exc}') from exc
    if not isinstance(config, dict):
        raise ValueError("Configuration must be a YAML mapping (use 'comparators: {}' for defaults).")
    unknown = set(config) - {'schema_version', 'comparators', 'file_pairs', 'exclude', 'exclude_extensions', 'required_outputs'}
    if unknown:
        raise ValueError(f'Unknown configuration keys: {", ".join(sorted(unknown))}.')
    if type(config.get('schema_version', 1)) is not int or config.get('schema_version', 1) != 1:
        raise ValueError('Unsupported configuration schema_version; expected 1.')
    comparators = config.get('comparators', {})
    if not isinstance(comparators, dict):
        raise ValueError('comparators must map file patterns to settings.')
    for pattern, entry in comparators.items():
        relative_path(pattern, 'Comparator pattern', allow_glob=True)
        if not isinstance(entry, dict):
            raise ValueError('Each comparator requires a settings mapping.')
        settings = {k: v for k, v in entry.items() if k != 'type'}
        validate_settings(entry.get('type'), settings)
        entry.update(settings)
    for key in ('exclude', 'exclude_extensions'):
        _strings(config.get(key, []), key, nonempty=False)
    for path_value in config.get('exclude', []):
        relative_path(path_value, 'Exclusion')
    for extension in config.get('exclude_extensions', []):
        if '/' in extension or '\\' in extension or any(c in extension for c in '*?[]'):
            raise ValueError('exclude_extensions expects literal extensions, not paths or patterns.')
    required = config.get('required_outputs', [])
    if isinstance(required, dict):
        if set(required) - {'run1', 'run2'}:
            raise ValueError('required_outputs mapping accepts only run1 and run2.')
    for side in ('run1', 'run2'):
        paths = required_for(config, side)
        _strings(paths, 'required_outputs', nonempty=False)
        for item in paths:
            relative_path(item, 'Required output')
            excluded_path = any(item == p or item.startswith(p.rstrip('/') + '/') for p in config.get('exclude', []))
            excluded_ext = Path(item).suffix.lower() in {'.' + e.lstrip('.').lower() for e in config.get('exclude_extensions', [])}
            if excluded_path or excluded_ext:
                raise ValueError(f'Required output cannot also be excluded: {item}')
    pairs = config.get('file_pairs', [])
    if not isinstance(pairs, list):
        raise ValueError('file_pairs must be a list of run1/run2 mappings.')
    seen = {'run1': set(), 'run2': set()}
    for pair in pairs:
        if not isinstance(pair, dict) or set(pair) != {'run1', 'run2'}:
            raise ValueError('Each file pair must contain run1 and run2.')
        for side in seen:
            relative_path(pair[side], side + ' file-pair path')
            if pair[side] in seen[side]:
                raise ValueError(f'Duplicate {side} file in explicit pairs: {pair[side]}')
            seen[side].add(pair[side])
    return config
