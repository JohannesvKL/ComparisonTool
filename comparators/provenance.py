"""Portable artifact identity and optional runner-supplied metadata."""
import hashlib
import json
import platform
from importlib import metadata
from pathlib import Path
from .config import relative_path


def sha256(path):
    digest = hashlib.sha256()
    with open(path, 'rb') as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def software():
    from . import __version__
    dependencies = {}
    for package in ('numpy', 'pandas', 'datacompy', 'rocrate', 'PyYAML', 'scikit-image', 'h5py', 'biopython', 'pysam', 'pyarrow'):
        try:
            dependencies[package] = metadata.version(package)
        except metadata.PackageNotFoundError:
            pass
    return {'name': 'ComparisonTool', 'version': __version__, 'python': platform.python_version(),
            'system': platform.system(), 'architecture': platform.machine(), 'dependencies': dependencies}


def artifact(path, root):
    return {'path': Path(path).relative_to(root).as_posix(), 'size_bytes': Path(path).stat().st_size, 'sha256': sha256(path)}


def read_manifest(root, relative):
    if relative is None:
        return None
    relative_path(relative, 'Manifest path')
    path = Path(root) / relative
    if path.resolve().is_relative_to(Path(root).resolve()) is False:
        raise ValueError('Runner manifest must stay within the run directory.')
    with open(path, encoding='utf-8') as handle:
        result = json.load(handle)
    if not isinstance(result, dict) or type(result.get('schema_version')) is not int or result['schema_version'] != 1:
        raise ValueError('Runner manifest requires schema_version: 1.')
    if result.get('status') not in ('completed', 'failed', 'running'):
        raise ValueError('Runner manifest status must be completed, failed or running.')
    return {'path': relative, 'sha256': sha256(path), 'content': result}


def portable_strings(value, roots):
    """Remove known input-root locations from comparator-generated diagnostics."""
    if isinstance(value, str):
        for root, identifier in sorted(roots.items(), key=lambda x: len(x[0]), reverse=True):
            value = value.replace(root + '/', identifier + '/').replace(root, identifier)
        return value
    if isinstance(value, dict):
        return {k: portable_strings(v, roots) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [portable_strings(v, roots) for v in value]
    return value


def ensure_report_outside_runs(output, *roots):
    if output is not None and any(Path(output).resolve().is_relative_to(Path(root).resolve()) for root in roots):
        raise ValueError('Write reports outside both run directories to avoid comparing reports or packaging the archive into itself.')
