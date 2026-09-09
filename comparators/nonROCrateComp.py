"""Compare completed run outputs and emit portable results."""
import json
from datetime import datetime, timezone
from pathlib import Path
from .file_resolver import OutputFileResolver
from .config import load_config, required_for
from .provenance import artifact, software, sha256, read_manifest, portable_strings, ensure_report_outside_runs
from .NumpyEncoder import NumpyEncoder


class DirectoryRunComparator:
    def __init__(self, comparison_manager):
        self.manager = comparison_manager
        self.resolver = OutputFileResolver()

    def compare_runs(self, run1_path, run2_path, config_path=None, subdir='outputs',
                     output_path='comparison_result.json', custom=False, manifest_path=None):
        ensure_report_outside_runs(output_path, run1_path, run2_path)
        roots = {'run1': Path(run1_path).resolve(), 'run2': Path(run2_path).resolve()}
        config = load_config(config_path) if config_path else {}
        files = {side: self.resolver.get_files_from_dir(str(root), subdir) for side, root in roots.items()}
        pairing = self.resolver.resolve_pairs(files['run1'], files['run2'], config_path)
        missing = {side: sorted(set(required_for(config, side)) - files[side].keys()) for side in roots}
        results = []
        for label, path1, path2 in pairing.pairs:
            result = self.manager.compare_files(path1, path2, custom=custom, lookup_path=label)
            entry = portable_strings(dict(result), {str(root): side for side, root in roots.items()})
            entry['filename'] = label
            entry['run1_path'] = Path(path1).relative_to(roots['run1']).as_posix()
            entry['run2_path'] = Path(path2).relative_to(roots['run2']).as_posix()
            entry['comparator'] = entry.pop('tool_metadata', {})
            results.append(entry)
        covered = {
            'run1': {str(Path(p1)) for _, p1, _ in pairing.pairs},
            'run2': {str(Path(p2)) for _, _, p2 in pairing.pairs},
        }
        unmatched = {'run1': pairing.only_in_run1, 'run2': pairing.only_in_run2}
        run_metadata, excluded = {}, {}
        for side, root in roots.items():
            included = covered[side] | {files[side][name] for name in unmatched[side]}
            excluded[side] = [name for name, path in files[side].items() if path not in included]
            run_metadata[side] = {
                'id': side, 'storage': 'external', 'root': None,
                'artifacts': [artifact(path, root) for path in sorted(included)],
            }
            manifest = read_manifest(root, manifest_path)
            if manifest:
                run_metadata[side]['manifest'] = manifest
        incomplete_runs = [side for side, data in run_metadata.items()
                           if data.get('manifest', {}).get('content', {}).get('status', 'completed') != 'completed']
        errors = sum(r['verdict'] == 'ERROR' for r in results)
        differences = sum(r['verdict'] == 'FAIL' for r in results)
        verdict = ('ERROR' if errors else 'FAIL' if differences or any(missing.values()) or any(unmatched.values()) or incomplete_runs
                   else 'NOT_CHECKED' if not results else 'PASS')
        reasons = []
        if not results:
            reasons.append('No file pairs were compared.')
        if any(missing.values()):
            reasons.append('Required outputs are missing.')
        if incomplete_runs:
            reasons.append('Runner manifests do not mark all runs completed.')
        summary = {
            'schema_version': '1.0',
            'metadata': {
                'timestamp': datetime.now(timezone.utc).isoformat(), 'path_base': 'run_root',
                'subdir': Path(subdir).as_posix(), 'runs': run_metadata, 'software': software(),
                'config': {'schema_version': config.get('schema_version', 1), 'sha256': sha256(config_path) if config_path else None,
                           'content': config},
            },
            'overall_match': verdict == 'PASS', 'verdict': verdict,
            'reason': ' '.join(reasons) or None,
            'files_compared': len(results), 'files_matching': sum(r['match'] for r in results),
            'files_differing': differences, 'files_errored': errors,
            'files_only_in_run1': unmatched['run1'], 'files_only_in_run2': unmatched['run2'],
            'missing_required_outputs': missing, 'excluded_files': excluded,
            'incomplete_runs': incomplete_runs, 'comparisons': results,
        }
        if output_path is not None:
            Path(output_path).write_text(json.dumps(summary, indent=2, cls=NumpyEncoder, allow_nan=False), encoding='utf-8')
        return summary
