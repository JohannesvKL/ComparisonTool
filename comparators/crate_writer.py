import json
import warnings
import tempfile
from pathlib import Path
from datetime import datetime, timezone
from rocrate.rocrate import ROCrate
from rocrate.model.contextentity import ContextEntity
from .NumpyEncoder import NumpyEncoder

from typing import Dict


class ComparisonCrateWriter:
    """
    Packages a completed directory comparison into an RO-Crate zip.

    Takes the summary dict produced by DirectoryRunComparator.compare_runs
    and writes it into a crate alongside the config file and references to
    the input run directories.

    The detailed per-file comparison results are stored in comparison_result.json
    inside the crate. The ro-crate-metadata.json contains only high-level
    provenance: the overall result, run references, and the tools used.
    """

    def write(
        self,
        summary: Dict,
        run1_path: str,
        run2_path: str,
        config_path: str,
        output_path: str = 'comparison.crate.zip',
        include_files: bool = False
    ):
        """
        Build and write the comparison RO-Crate zip.

        Args:
            summary:        Result dict from DirectoryRunComparator.compare_runs
            run1_path:      Path to the first run directory
            run2_path:      Path to the second run directory
            config_path:    Path to the unified config YAML
            output_path:    Destination path for the output zip
            include_files:  If True, embed the run directories into the crate.
                            If False, reference them as external file:// URIs.
        """
        crate = ROCrate()
        crate.name = "Workflow Run Comparison"
        crate.description = (
            f"Comparison of {run1_path} vs {run2_path} - "
            f"{'PASS' if summary['overall_match'] else 'FAIL'}"
        )

        # -- Input run directories -----------------------------------------
        if include_files:
            run1_entity = crate.add_dataset(
                run1_path,
                dest_path='run1/',
                properties={'name': 'Run 1'}
            )
            run2_entity = crate.add_dataset(
                run2_path,
                dest_path='run2/',
                properties={'name': 'Run 2'}
            )
        else:
            run1_entity = ContextEntity(
                crate,
                identifier=Path(run1_path).resolve().as_uri(),
                properties={'@type': 'Dataset', 'name': 'Run 1'}
            )
            crate.add(run1_entity)
            run2_entity = ContextEntity(
                crate,
                identifier=Path(run2_path).resolve().as_uri(),
                properties={'@type': 'Dataset', 'name': 'Run 2'}
            )
            crate.add(run2_entity)

        # -- Config file (embedded) ----------------------------------------
        config_entity = crate.add_file(
            config_path,
            dest_path='config.yml',
            properties={
                'name': 'Comparison configuration',
                'description': 'Unified comparator and file pairs configuration'
            }
        )

        # -- Result JSON (embedded) ----------------------------------------
        result_json = json.dumps(summary, indent=2, cls=NumpyEncoder)
        with tempfile.NamedTemporaryFile(
            mode='w', suffix='.json', delete=False
        ) as tmp:
            tmp.write(result_json)
            tmp_path = tmp.name

        result_entity = crate.add_file(
            tmp_path,
            dest_path='comparison_result.json',
            properties={
                'name': 'Comparison result',
                'encodingFormat': 'application/json',
                'description': 'Full per-file comparison results'
            }
        )

        # -- Tool entities (one per comparator type used) ------------------
        tool_entities = self._collect_tool_entities(crate, summary)

        # -- Overall summary entity ----------------------------------------
        summary_entity = ContextEntity(
            crate,
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
        crate.add(summary_entity)

        # -- Wire root dataset ---------------------------------------------
        has_part = [
            {'@id': config_entity.id},
            {'@id': result_entity.id},
        ]
        if include_files:
            has_part += [
                {'@id': run1_entity.id},
                {'@id': run2_entity.id},
            ]

        crate.root_dataset['hasPart'] = has_part
        crate.root_dataset['mentions'] = [{'@id': summary_entity.id}]
        crate.root_dataset['instrument'] = [
            {'@id': e.id} for e in tool_entities.values()
        ]
        crate.root_dataset['dateCreated'] = datetime.now(timezone.utc).isoformat()

        with warnings.catch_warnings():
            warnings.filterwarnings(
                'ignore',
                message=".*looks like a data entity but it's not listed in the root dataset's hasPart.*",
                category=UserWarning
            )
            crate.write_zip(output_path)

        Path(tmp_path).unlink(missing_ok=True)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _collect_tool_entities(self, crate: ROCrate, summary: Dict) -> Dict:
        """
        Register one tool ContextEntity per unique comparator used,
        derived from the comparator metadata in each comparison entry.
        Returns a dict of tool_id -> ContextEntity.
        """
        tool_registry = {}

        for entry in summary.get('comparisons', []):
            tool_metadata = entry.get('comparator', {})
            tool_name = tool_metadata.get('name', 'unknown')
            tool_id = f"#tool-{tool_name.lower().replace(' ', '-')}"

            if tool_id not in tool_registry:
                safe_metadata = {
                    k: str(v) if isinstance(v, (list, dict)) else v
                    for k, v in tool_metadata.items()
                }
                tool_entity = ContextEntity(
                    crate,
                    identifier=tool_id,
                    properties=safe_metadata
                )
                crate.add(tool_entity)
                tool_registry[tool_id] = tool_entity

        return tool_registry