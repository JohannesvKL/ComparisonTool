import json
from pathlib import Path
import sys

from click.testing import CliRunner
import pytest

from comparators.comparison_cli import compare
from comparators.manager import ComparisonManager
from comparators.nonROCrateComp import DirectoryRunComparator


@pytest.fixture
def runs(tmp_path):
    a, b = tmp_path / 'run 1', tmp_path / 'run 2'
    a.mkdir()
    b.mkdir()
    config = tmp_path / 'config.yml'
    config.write_text('comparators: {}\n')
    return a, b, config


def invoke(runs, *options):
    a, b, config = runs
    return CliRunner().invoke(compare, ['directory', str(a), str(b), '-c', str(config), *map(str, options)])


def test_explicit_binary_type_overrides_csv(runs, tmp_path):
    a, b, config = runs
    # Numerically identical tables with differing textual representations.
    (a / 'data.csv').write_text('id,value\nx,1.0\n')
    (b / 'data.csv').write_text('id,value\nx,1.00\n')
    config.write_text('comparators:\n  "*.csv":\n    type: binary\n')
    out = tmp_path / 'result.json'
    result = invoke(runs, '-o', out)
    assert result.exit_code == 1, result.output
    report = json.loads(out.read_text())
    assert report['comparisons'][0]['method'] == 'sha256_checksum'
    assert report['verdict'] == 'FAIL'


def test_relative_patterns_and_actual_renamed_paths(runs, tmp_path):
    a, b, config = runs
    for root in (a, b):
        (root / 'outputs' / 'tables').mkdir(parents=True)
    f1 = a / 'outputs/tables/old.csv'
    f2 = b / 'outputs/tables/new.csv'
    f1.write_text('id,value\nx,1.0\n')
    f2.write_text('id,value\nx,1.00\n')
    config.write_text('comparators:\n  "tables/*.csv":\n    type: binary\nfile_pairs:\n  - run1: tables/old.csv\n    run2: tables/new.csv\n')
    out = tmp_path / 'report.json'
    proc = invoke(runs, '-s', 'outputs', '-o', out)
    assert proc.exit_code == 1
    entry = json.loads(out.read_text())['comparisons'][0]
    assert entry['run1_path'] == 'outputs/tables/old.csv'
    assert entry['run2_path'] == 'outputs/tables/new.csv'
    assert entry['method'] == 'sha256_checksum'
    assert 'file1_hash' in entry


def test_empty_runs_are_not_checked(runs, tmp_path):
    out = tmp_path / 'report.json'
    result = invoke(runs, '-o', out)
    assert result.exit_code == 1
    report = json.loads(out.read_text())
    assert report['verdict'] == 'NOT_CHECKED'
    assert not report['overall_match']


def test_excluding_everything_does_not_pass(runs, tmp_path):
    a, b, config = runs
    for root in (a, b):
        (root / 'debug.log').write_text('log')
    config.write_text('comparators: {}\nexclude_extensions: [log]\n')
    proc = invoke(runs, '-o', tmp_path / 'report.json')
    assert proc.exit_code == 1
    assert 'NOT_CHECKED' in proc.output


@pytest.mark.parametrize('dry', [False, True])
def test_missing_subdirectory_is_error(runs, tmp_path, dry):
    opts = ['--dry-run'] if dry else ['-o', str(tmp_path / 'result.json')]
    proc = invoke(runs, '-s', 'missing', *opts)
    assert proc.exit_code == 2
    assert 'Output directory does not exist' in proc.output


@pytest.mark.parametrize('config_text', ['[]', 'comparators: []', 'comparators: {"*.csv": {type: unknown}}',
                                       'file_pairs: [{run1: a}]', 'exclude: "*.txt"',
                                       'comparators: [broken',
                                       'file_pairs: [{run1: a, run2: b}, {run1: c, run2: b}]'])
def test_invalid_config_fails_cleanly_in_dry_run(runs, config_text):
    runs[2].write_text(config_text)
    proc = invoke(runs, '--dry-run')
    assert proc.exit_code == 2
    assert 'Invalid config' in proc.output


def test_custom_command_receives_both_files_without_shell(runs, tmp_path):
    a, b, config = runs
    for root in (a, b):
        (root / 'data ; literal.bin').write_bytes(b'hello')
    script = tmp_path / 'my comparator.py'
    script.write_text('import sys\nfrom pathlib import Path\nassert len(sys.argv) == 3\nsys.exit(0 if Path(sys.argv[1]).read_bytes() == Path(sys.argv[2]).read_bytes() else 1)\n')
    import yaml
    config.write_text(yaml.safe_dump({'comparators': {'*.bin': {'type': 'generic', 'user_comparison': [sys.executable, str(script)]}}}))
    out = tmp_path / 'result.json'
    proc = invoke(runs, '-o', out)
    assert proc.exit_code == 0, proc.output
    assert json.loads(out.read_text())['comparisons'][0]['method'] == 'user_defined'


@pytest.mark.parametrize('failure', ['exit', 'missing', 'timeout'])
def test_custom_execution_errors_remain_errors(runs, tmp_path, failure):
    a, b, config = runs
    for root in (a, b):
        (root / 'data.bin').write_bytes(b'hello')
    command = [sys.executable, '-c', 'raise SystemExit(3)']
    if failure == 'missing':
        command = [str(tmp_path / 'missing-tool')]
    elif failure == 'timeout':
        command = [sys.executable, '-c', 'import time; time.sleep(5)']
    import yaml
    config.write_text(yaml.safe_dump({'comparators': {'*.bin': {'type': 'generic', 'user_comparison': command, 'timeout': 0.05}}}))
    out = tmp_path / 'result.json'
    proc = invoke(runs, '-o', out)
    assert proc.exit_code == 2, proc.output
    report = json.loads(out.read_text())
    assert report['verdict'] == 'ERROR'
    assert report['files_errored'] == 1
    assert report['files_differing'] == 0


def test_unmatched_file_causes_failure(runs, tmp_path):
    (runs[0] / 'one.bin').write_bytes(b'hello')
    out = tmp_path / 'result.json'
    assert invoke(runs, '-o', out).exit_code == 1
    assert json.loads(out.read_text())['files_only_in_run1'] == ['one.bin']


def test_explicit_pair_bypasses_extension_exclusion(runs, tmp_path):
    a, b, config = runs
    (a / 'one.log').write_text('same')
    (b / 'two.log').write_text('same')
    config.write_text('comparators: {}\nexclude_extensions: [log]\nfile_pairs:\n  - run1: one.log\n    run2: two.log\n')
    assert invoke(runs, '-o', tmp_path / 'result.json').exit_code == 0


def test_crate_output_write_failure_is_error(runs, tmp_path):
    for root in runs[:2]:
        (root / 'data.bin').write_bytes(b'hello')
    proc = invoke(runs, '--crate', '-o', tmp_path / 'missing' / 'out.zip')
    assert proc.exit_code == 2
