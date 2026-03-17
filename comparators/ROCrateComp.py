from rocrate.rocrate import ROCrate
from rocrate.model.contextentity import ContextEntity
from .manager import ComparisonManager, FileComparator
from .file_resolver import OutputFileResolver, PairingResult

from typing import Dict, Optional


class WorkflowRunComparator:
    """Compare entire workflow runs with multiple file types"""

    def __init__(self, comparison_manager: ComparisonManager):
        self.manager = comparison_manager
        self.comparison_crate = None
        self.resolver = OutputFileResolver()

    def compare_runs(
        self,
        crate1_path: str,
        crate2_path: str,
        config_path: Optional[str] = None,
        subdir: str = "outputs", 
        output_path: str = "comparison.crate.zip"
    ) -> Dict:
        """Compare all outputs between two workflow runs"""

        self.comparison_crate = ROCrate()
        self.comparison_crate.name = "Workflow Run Comparison"
        self.comparison_crate.description = "Multi-format comparison of workflow outputs"

        # Load both crates
        crate1 = ROCrate(crate1_path)
        crate2 = ROCrate(crate2_path)

        # Add run crates as dataset references (not files — they are directories)
        run1_entity = ContextEntity(
            self.comparison_crate,
            identifier=crate1_path,
            properties={
                '@type': 'Dataset',
                'name': f'Run 1: {crate1_path}',
            }
        )
        self.comparison_crate.add(run1_entity)

        run2_entity = ContextEntity(
            self.comparison_crate,
            identifier=crate2_path,
            properties={
                '@type': 'Dataset',
                'name': f'Run 2: {crate2_path}',
            }
        )
        self.comparison_crate.add(run2_entity)

        # Resolve file pairs — use config if provided, otherwise fall back to name-matching
        files1 = self.resolver.get_files_from_crate(crate1, subdir)
        files2 = self.resolver.get_files_from_crate(crate2, subdir)
        pairing = self.resolver.resolve_pairs(files1, files2, config_path)

        pairs = pairing.pairs
        only_in_run1 = set(pairing.only_in_run1)
        only_in_run2 = set(pairing.only_in_run2)

        # Compare each file pair
        comparison_results = []
        all_pass = True

        for label, file1_path, file2_path in pairs:
            result = self.manager.compare_files(file1_path, file2_path)
            comparator = self.manager.get_comparator(label)

            action_entity = self._add_comparison_to_crate(
                label, result, comparator,
                run1_entity, run2_entity
            )

            comparison_results.append({
                'filename': label,
                'result': result,
                'action_id': action_entity.id
            })

            if not result['match']:
                all_pass = False

        # Build summary
        summary = {
            'overall_match': all_pass and len(only_in_run1) == 0 and len(only_in_run2) == 0,
            'files_compared': len(pairs),
            'files_matching': sum(1 for r in comparison_results if r['result']['match']),
            'files_differing': sum(1 for r in comparison_results if not r['result']['match']),
            'files_only_in_run1': list(only_in_run1),
            'files_only_in_run2': list(only_in_run2),
            'comparisons': comparison_results
        }

        self._add_summary_to_crate(summary)
        self.comparison_crate.write_zip(output_path)

        return summary

    # ------------------------------------------------------------------
    # RO-Crate writing helpers
    # ------------------------------------------------------------------

    def _add_comparison_to_crate(
        self,
        filename: str,
        result: Dict,
        comparator: FileComparator,
        run1_entity,
        run2_entity
    ) -> ContextEntity:
        """Add a single file comparison as an AssessAction"""

        action_id = f"#comparison-{filename.replace('/', '-').replace('.', '-')}"

        # Add tool entity if not already present
        tool_metadata = result['tool_metadata']
        tool_id = f"#tool-{tool_metadata['name'].lower().replace(' ', '-')}"

        if not self.comparison_crate.dereference(tool_id):
            # Ensure no nested dicts without @id slip through
            safe_metadata = {
                k: str(v) if isinstance(v, (list, dict)) else v
                for k, v in tool_metadata.items()
            }
            tool_entity = ContextEntity(
                self.comparison_crate,
                identifier=tool_id,
                properties=safe_metadata
            )
            self.comparison_crate.add(tool_entity)

        # Create action entity
        action_properties = {
            '@type': 'AssessAction',
            'name': f'Comparison of {filename}',
            'instrument': {'@id': tool_id},
            'object': [
                {'@id': f'{run1_entity.id}#{filename}'},
                {'@id': f'{run2_entity.id}#{filename}'}
            ],
            'actionStatus': 'http://schema.org/CompletedActionStatus',
            'error': result.get('reason')
        }

        # Add configuration as additionalProperty
        if 'configuration' in result:
            action_properties['additionalProperty'] = [
                {
                    '@id': f'{action_id}-config-{key}',
                    '@type': 'PropertyValue',
                    'name': key,
                    'value': str(value) if not isinstance(value, (int, float, bool)) else value
                }
                for key, value in result['configuration'].items()
            ]

        # Add metrics/summary
        if 'metrics' in result:
            action_properties['result'] = [
                {
                    '@id': f'{action_id}-metric-{key}',
                    '@type': 'PropertyValue',
                    'name': key,
                    'value': str(value) if not isinstance(value, (int, float, bool)) else value
                }
                for key, value in result['metrics'].items()
            ]
        elif 'summary' in result:
            action_properties['result'] = [
                {
                    '@id': f'{action_id}-summary-{key}',
                    '@type': 'PropertyValue',
                    'name': key,
                    'value': str(value)
                }
                for key, value in result['summary'].items()
            ]

        action_entity = ContextEntity(
            self.comparison_crate,
            identifier=action_id,
            properties=action_properties
        )
        self.comparison_crate.add(action_entity)

        return action_entity

    def _add_summary_to_crate(self, summary: Dict):
        """Add overall comparison summary"""

        summary_entity = ContextEntity(
            self.comparison_crate,
            identifier='#overall-comparison',
            properties={
                '@type': 'PropertyValue',
                'name': 'Overall Comparison Result',
                'value': 'PASS' if summary['overall_match'] else 'FAIL',
                'description': (
                    f"{summary['files_matching']}/{summary['files_compared']} "
                    f"files matched"
                )
            }
        )
        self.comparison_crate.add(summary_entity)

        # Link from root
        self.comparison_crate.root_dataset['mentions'] = [
            {'@id': summary_entity.id}
        ]