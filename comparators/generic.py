import subprocess
from typing import Dict, Any

from .base import FileComparator


class GenericComparator(FileComparator):
    """User-defined comparison"""

    def can_compare(self, file_path: str) -> bool:
        return False

    def compare(self, file1: str, file2: str, config: Dict) -> Dict[str, Any]:
        comp_tool = config.get('user_comparison')

        if not comp_tool:
            return {
                'match': False,
                'method': 'user_defined',
                'verdict': 'FAIL',
                'reason': 'No user_comparison tool specified in config'
            }

        result, detail = self.run(comp_tool, file1, file2)

        return {
            'match': result,
            'method': 'user_defined',
            'verdict': 'PASS' if result else 'FAIL',
            'reason': detail
        }

    def get_tool_metadata(self) -> Dict[str, Any]:
        return {
            '@type': 'SoftwareApplication',
            'name': 'User Comparator',
            'version': 'x',
            'applicationCategory': 'User-defined comparison'
        }

    def run(self, tool: str, file1: str, file2: str) -> tuple[bool, str | None]:
        """
        Execute the user-provided comparison tool as a subprocess.
        
        The tool is expected to exit with code 0 for a match, non-zero for a mismatch.
        Any output to stdout/stderr is captured and surfaced as the failure reason.
        """
        try:
            proc = subprocess.run(
                [tool, file1, file2],
                capture_output=True,
                text=True,
                shell=True
            )
            success = proc.returncode == 0
            detail = (proc.stdout or proc.stderr).strip() or f"Tool exited with code {proc.returncode}"
            return success, None if success else detail

        except FileNotFoundError:
            return False, f"Comparison tool not found: '{tool}'"
        except PermissionError:
            return False, f"Permission denied executing: '{tool}'"
        except Exception as e:
            return False, f"Unexpected error running tool: {e}"