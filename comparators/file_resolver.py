import yaml
from pathlib import Path
from typing import Dict, List, NamedTuple, Optional, Tuple


class PairingResult(NamedTuple):
    """Resolved file pairs and unmatched files from two runs."""
    pairs: List[Tuple[str, str, str]]   # (label, file1_path, file2_path)
    only_in_run1: List[str]             # paths with no run2 counterpart
    only_in_run2: List[str]             # paths with no run1 counterpart


class OutputFileResolver:
    """
    Resolves output files for comparison from two run sources.

    Supports two discovery strategies:
      - Directory scan: recursively find all files under a subdirectory
      - RO-Crate metadata: find files declared as outputs in crate actions

    These can be combined with config-based explicit pairing to handle
    cases where filenames differ between runs (e.g. due to timestamps).
    """

    # ------------------------------------------------------------------
    # Single-crate/directory discovery
    # ------------------------------------------------------------------

    def get_files_from_dir(self, base_path: str, subdir: str = "outputs") -> Dict[str, str]:
        """
        Recursively scan a subdirectory for output files.
        Returns a dict mapping relative path (from subdir) -> absolute path.
        Works with any plain directory, no RO-Crate required.
        """
        output_files = {}
        scan_path = Path(base_path) / subdir

        if not scan_path.exists():
            return output_files

        for file_path in scan_path.rglob("*"):
            if file_path.is_file():
                relative = str(file_path.relative_to(scan_path))
                output_files[relative] = str(file_path)

        return output_files

    def get_files_from_crate(self, crate, subdir: str = "outputs") -> Dict[str, str]:
        """
        Extract output files by scanning a subdirectory of an RO-Crate.
        Thin wrapper around get_files_from_dir using the crate's source path.
        Returns a dict mapping relative path (from subdir) -> absolute path.
        """
        return self.get_files_from_dir(str(crate.source), subdir)

    def get_files_from_crate_metadata(self, crate) -> Dict[str, str]:
        """
        Extract output files by parsing RO-Crate metadata.
        Looks for File entities declared as results of CreateAction or
        OrganizeAction entities within the crate.
        Returns a dict mapping relative entity id -> local source path.
        """
        output_files = {}

        for entity in crate.get_entities():
            if entity.type in ('CreateAction', 'OrganizeAction'):
                results = entity.get('result', [])
                if not isinstance(results, list):
                    results = [results]
                for r in results:
                    ref_id = r.id if hasattr(r, 'id') else r.get('@id')
                    if ref_id:
                        target = crate.dereference(ref_id)
                        if target and target.type == 'File' and target.source:
                            output_files[target.id] = target.source

        return output_files

    # ------------------------------------------------------------------
    # Config-based pairing
    # ------------------------------------------------------------------

    def load_file_pairs_from_config(self, config_path: str) -> Tuple[Dict[str, str], List[str], List[str]]:
        """
        Load explicit file pairings and exclusions from a YAML config file.

        Expected format:
            file_pairs:
              - run1: "result_2024-01-15.csv"
                run2: "result_2024-02-20.csv"
            exclude:
              - "debug.log"
              - "tmp/"
            exclude_extensions:
              - ".log"
              - ".tmp"

        Path exclusions are matched as exact relative paths or path prefixes.
        Extension exclusions are matched case-insensitively against each file's
        suffix; a leading dot is optional (e.g. "log" and ".log" are equivalent).

        Both exclusion types apply to auto-matched files. Explicit file_pairs
        bypass extension exclusions but are still blocked by path exclusions,
        which raise a ValueError to surface likely config mistakes.

        Returns a tuple of:
          - dict mapping run1 relative path -> run2 relative path
          - list of path exclusion patterns
          - list of normalised extension exclusions (each starts with '.')
        """
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)

        pairs = {}
        for pair in config.get('file_pairs', []):
            pairs[pair['run1']] = pair['run2']

        excludes = config.get('exclude', [])

        exclude_extensions = [
            ext if ext.startswith('.') else f'.{ext}'
            for ext in config.get('exclude_extensions', [])
        ]

        return pairs, excludes, exclude_extensions

    @staticmethod
    def _is_excluded(path: str, excludes: List[str], exclude_extensions: List[str] = []) -> bool:
        """
        Return True if a relative path matches any exclusion rule.

        Path patterns are matched as exact paths or directory prefixes
        (e.g. "tmp/" excludes everything under tmp/).

        Extension patterns are matched case-insensitively against the file's
        suffix (e.g. ".log" excludes "run.log" and "RUN.LOG").
        """
        for pattern in excludes:
            if path == pattern or path.startswith(pattern.rstrip('/') + '/'):
                return True
        if exclude_extensions:
            suffix = Path(path).suffix.lower()
            if suffix in {ext.lower() for ext in exclude_extensions}:
                return True
        return False

    def resolve_pairs(
        self,
        files1: Dict[str, str],
        files2: Dict[str, str],
        config_path: Optional[str] = None
    ) -> PairingResult:
        """
        Resolve file pairs from two dicts of {relative_path: absolute_path}.

        If a config is provided, explicit pairs are applied first. Remaining
        files with matching names are then paired automatically. Files that
        cannot be paired in either direction are reported as unmatched.

        Exclusions defined in the config are applied before pairing: excluded
        files are silently dropped and will not appear in pairs or unmatched
        lists. Explicit pairs referencing an excluded path raise a ValueError
        to surface likely config mistakes. Explicit pairs bypass extension
        exclusions — a file named in file_pairs is always compared regardless
        of its type; only path-based exclusions block explicit pairs.

        This method is source-agnostic: pass in dicts from get_files_from_dir,
        get_files_from_crate, get_files_from_crate_metadata, or any other source.
        """
        resolved = []
        covered1 = set()
        covered2 = set()
        excludes: List[str] = []
        exclude_extensions: List[str] = []

        # Apply explicit pairs from config first
        if config_path:
            explicit, excludes, exclude_extensions = self.load_file_pairs_from_config(config_path)
            for rel1, rel2 in explicit.items():
                if self._is_excluded(rel1, excludes) or self._is_excluded(rel2, excludes):
                    raise ValueError(
                        f"Config file_pair references an excluded path: '{rel1}' -> '{rel2}'. "
                        "Remove it from 'exclude' or from 'file_pairs'."
                    )
                if rel1 not in files1:
                    raise FileNotFoundError(f"Config references missing file in run1: {rel1}")
                if rel2 not in files2:
                    raise FileNotFoundError(f"Config references missing file in run2: {rel2}")

                resolved.append((rel1, files1[rel1], files2[rel2]))
                covered1.add(rel1)
                covered2.add(rel2)

        # Auto-match remaining files by name, skipping excluded paths
        for name in set(files1.keys()) & set(files2.keys()):
            if name not in covered1 and name not in covered2:
                if not self._is_excluded(name, excludes, exclude_extensions):
                    resolved.append((name, files1[name], files2[name]))
                    covered1.add(name)
                    covered2.add(name)

        only_in_run1 = [
            p for p in files1
            if p not in covered1 and not self._is_excluded(p, excludes, exclude_extensions)
        ]
        only_in_run2 = [
            p for p in files2
            if p not in covered2 and not self._is_excluded(p, excludes, exclude_extensions)
        ]

        return PairingResult(pairs=resolved, only_in_run1=only_in_run1, only_in_run2=only_in_run2)