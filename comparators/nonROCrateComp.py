import json
import numpy as np
from datetime import datetime, timezone
from pathlib import Path
from .manager import ComparisonManager, FileComparator
from .file_resolver import OutputFileResolver
from .NumpyEncoder import NumpyEncoder

from typing import Dict, Optional


class DirectoryRunComparator:
    """Compare workflow run outputs stored as plain directories (no RO-Crate)"""

    def __init__(self, comparison_manager: ComparisonManager):
        self.manager = comparison_manager
        self.resolver = OutputFileResolver()

    def compare_runs(
        self,
        run1_path: str,
        run2_path: str,
        config_path: Optional[str] = None,
        subdir: str = "outputs",
        output_path: str = "comparison_result.json", 
        custom: bool = False
    ) -> Dict:
        """Compare all outputs between two workflow run directories"""

        # Resolve file pairs
        files1 = self.resolver.get_files_from_dir(run1_path, subdir)
        files2 = self.resolver.get_files_from_dir(run2_path, subdir)
        pairing = self.resolver.resolve_pairs(files1, files2, config_path)

        pairs = pairing.pairs
        only_in_run1 = list(pairing.only_in_run1)
        only_in_run2 = list(pairing.only_in_run2)

        # Compare each file pair
        comparison_results = []
        all_pass = True

        for label, file1_path, file2_path in pairs:
            result = self.manager.compare_files(file1_path, file2_path, custom = custom)

            comparison_results.append(
                self._build_comparison_entry(label, result, run1_path, run2_path)
            )

            if not result['match']:
                all_pass = False

        # Build summary
        summary = {
            'metadata': {
                'run1': run1_path,
                'run2': run2_path,
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'config': config_path
            },
            'overall_match': all_pass and len(only_in_run1) == 0 and len(only_in_run2) == 0,
            'files_compared': len(pairs),
            'files_matching': sum(1 for r in comparison_results if r['match']),
            'files_differing': sum(1 for r in comparison_results if not r['match']),
            'files_only_in_run1': only_in_run1,
            'files_only_in_run2': only_in_run2,
            'comparisons': comparison_results
        }

        # Write JSON output
        Path(output_path).write_text(json.dumps(summary, indent=2, cls=NumpyEncoder))

        return summary

    # ------------------------------------------------------------------
    # Output building helpers
    # ------------------------------------------------------------------

    def _build_comparison_entry(
        self,
        label: str,
        result: Dict,
        run1_path: str,
        run2_path: str
    ) -> Dict:
        """Build a plain dict describing a single file comparison"""

        entry = {
            'filename': label,
            'run1_path': str(Path(run1_path) / label),
            'run2_path': str(Path(run2_path) / label),
            'match': result['match'],
            'comparator': result.get('tool_metadata', {}),
        }

        if result.get('reason'):
            entry['reason'] = result['reason']

        if 'configuration' in result:
            entry['configuration'] = result['configuration']

        if 'metrics' in result:
            entry['metrics'] = result['metrics']
        elif 'summary' in result:
            entry['summary'] = {k: str(v) for k, v in result['summary'].items()}

        return entry