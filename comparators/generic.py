"""Run a custom comparison program without shell interpretation."""
import subprocess
from .base import FileComparator


class GenericComparator(FileComparator):
    def can_compare(self, file_path):
        return False

    def compare(self, file1, file2, config):
        command = config.get('user_comparison')
        if isinstance(command, str):
            command = [command]
        if not isinstance(command, list) or not command or any(not isinstance(v, str) or not v for v in command):
            raise ValueError('user_comparison must be an executable path or a list of command arguments.')
        timeout = float(config.get('timeout', 60))
        if timeout <= 0:
            raise ValueError('Custom comparator timeout must be positive.')
        process = subprocess.run([*command, str(file1), str(file2)], capture_output=True,
                                 text=True, timeout=timeout, check=False)
        verdict = 'PASS' if process.returncode == 0 else 'FAIL' if process.returncode == 1 else 'ERROR'
        return {'match': verdict == 'PASS', 'method': 'user_defined', 'verdict': verdict,
                'reason': None if verdict == 'PASS' else (process.stdout or process.stderr).strip() or f'Tool exited with code {process.returncode}',
                'configuration': {'user_comparison': command, 'timeout': timeout}}

    def get_tool_metadata(self):
        return {'@type': 'SoftwareApplication', 'name': 'User Comparator',
                'applicationCategory': 'User-defined comparison'}
