import json
from pathlib import Path
import shutil
import zipfile
import numpy as np
import pytest
from click.testing import CliRunner
from comparators.comparison_cli import compare
from comparators.config import load_config
from comparators.manager import ComparisonManager
from comparators.nonROCrateComp import DirectoryRunComparator


@pytest.mark.parametrize('text', [
    'comparators: {"*.csv": {type: tabular, tolerance: 1}}',
    'comparators: {"*.csv": {type: tabular, abs_tol: -.inf}}',
    'comparators: {"*.png": {type: image, ssim_threshold: 2}}',
    'comparators: {"*.bam": {type: bam, sample_size: 0}}',
    'comparators: {"*.bam": {type: bam, mode: []}}',
    'comparators: {"*.bam": {type: bam, check_order: 1}}',
    'comparators: {}\ncomparators: {}',
    'required_outputs: ["../outside.csv"]',
    'required_outputs: [a.csv]\nexclude: [a.csv]',
    'required_outputs: [a.log]\nexclude_extensions: [log]',
    'required_output: [a.csv]',
])
def test_strict_config_rejects_unsafe_or_ignored_policy(tmp_path, text):
    path = tmp_path / 'config.yml'
    path.write_text(text)
    with pytest.raises(ValueError):
        load_config(path)


def runs(tmp_path):
    a, b = tmp_path / 'a', tmp_path / 'b'
    for root in (a, b):
        (root / 'outputs').mkdir(parents=True)
        (root / 'outputs/data.csv').write_text('id,x\na,1\n')
    config = tmp_path / 'comparison.yml'
    config.write_text('comparators: {}\nrequired_outputs: [data.csv, missing.csv]\n')
    return a, b, config


def test_missing_in_both_runs_is_failure(tmp_path):
    a, b, config = runs(tmp_path)
    summary = DirectoryRunComparator(ComparisonManager.from_config(config)).compare_runs(a, b, config, output_path=None)
    assert summary['files_matching'] == 1
    assert summary['verdict'] == 'FAIL'
    assert summary['missing_required_outputs'] == {'run1': ['missing.csv'], 'run2': ['missing.csv']}


def test_dry_run_checks_required_outputs(tmp_path):
    a, b, config = runs(tmp_path)
    result = CliRunner().invoke(compare, ['directory', str(a), str(b), '-s', 'outputs', '-c', str(config), '--dry-run'])
    assert result.exit_code == 1
    assert 'missing.csv' in result.output


def test_relocation_and_embedded_crate_paths(tmp_path):
    a, b, config = runs(tmp_path)
    config.write_text('comparators: {}\nrequired_outputs: [data.csv]\n')
    output = tmp_path / 'report.zip'
    result = CliRunner().invoke(compare, ['directory', str(a), str(b), '-s', 'outputs', '-c', str(config), '--crate', '--include-files', '-o', str(output)])
    assert result.exit_code == 0, result.output
    with zipfile.ZipFile(output) as archive:
        text = archive.read('comparison_result.json').decode()
        assert str(tmp_path) not in text
        report = json.loads(text)
        for side in ('run1', 'run2'):
            root = report['metadata']['runs'][side]['root']
            path = report['comparisons'][0][side + '_path']
            assert archive.read(root + path) == b'id,x\na,1\n'
            assert len(report['metadata']['runs'][side]['artifacts'][0]['sha256']) == 64
    moved = tmp_path / 'relocated'
    shutil.copytree(a, moved)
    first = DirectoryRunComparator(ComparisonManager()).compare_runs(a, b, output_path=None)
    second = DirectoryRunComparator(ComparisonManager()).compare_runs(moved, b, output_path=None)
    assert first['comparisons'] == second['comparisons']
    assert first['metadata']['runs'] == second['metadata']['runs']


def test_runner_manifest_and_html(tmp_path):
    a, b, config = runs(tmp_path)
    config.write_text('comparators: {}')
    for root in (a, b):
        (root / 'metadata').mkdir()
        (root / 'metadata/run.json').write_text(json.dumps({'schema_version': 1, 'status': 'completed', 'parameters': {'note': '<script>alert(1)</script>'}}))
    (b / 'metadata/run.json').write_text('{"schema_version":1,"status":"failed"}')
    output = tmp_path / 'report.json'
    html = tmp_path / 'report.html'
    result = CliRunner().invoke(compare, ['directory', str(a), str(b), '-s', 'outputs', '-c', str(config), '--manifest-path', 'metadata/run.json', '--html-output', str(html), '-o', str(output)])
    assert result.exit_code == 1, result.output
    assert json.loads(output.read_text())['incomplete_runs'] == ['run2']
    assert '<script>' not in html.read_text()
    assert '&lt;script&gt;' in html.read_text()


def test_json_semantic_and_precision(tmp_path):
    a, b = tmp_path / 'a.json', tmp_path / 'b.json'
    a.write_text('{"n": 1.0, "id": 9007199254740993}')
    b.write_text('{"id":9007199254740993,"n":1.00001}')
    manager = ComparisonManager()
    assert manager.compare_files(a, b, {'abs_tol': 0.0001})['match']
    b.write_text('{"id":9007199254740992,"n":1.0}')
    assert not manager.compare_files(a, b, {'abs_tol': 1000})['match']
    b.write_text('{"n": NaN}')
    assert manager.compare_files(a, b)['verdict'] == 'ERROR'


@pytest.mark.parametrize('extension', ['npy', 'npz'])
def test_numpy_tolerances_shape_and_nan(tmp_path, extension):
    a, b = tmp_path / ('a.' + extension), tmp_path / ('b.' + extension)
    def save(path, values):
        if extension == 'npy':
            np.save(path, values)
        else:
            np.savez(path, values=values)
    save(a, np.array([1., np.nan]))
    save(b, np.array([1.00001, np.nan]))
    manager = ComparisonManager()
    assert manager.compare_files(a, b, {'atol': .001, 'equal_nan': True})['match']
    assert not manager.compare_files(a, b, {'atol': .001})['match']
    save(b, np.array([[1., np.nan]]))
    assert not manager.compare_files(a, b, {'atol': .001, 'equal_nan': True})['match']


def test_numpy_object_is_error_without_unpickling(tmp_path):
    path = tmp_path / 'object.npy'
    np.save(path, np.array([{'value': 1}], dtype=object))
    assert ComparisonManager().compare_files(path, path)['verdict'] == 'ERROR'


def test_missing_required_columns_in_both_tables(tmp_path):
    path = tmp_path / 'data.csv'
    path.write_text('id,x\na,1\n')
    result = ComparisonManager().compare_files(path, path, {'required_columns': ['id', 'missing']})
    assert result['verdict'] == 'FAIL'
