"""Exercise the supported CLI/ComparisonCrateWriter integration."""
import json
import zipfile
import pytest
from click.testing import CliRunner
from comparators.comparison_cli import compare


@pytest.mark.parametrize('embed', [False, True])
def test_crate_contains_results_config_and_run_provenance(tmp_path, monkeypatch, embed):
    monkeypatch.chdir(tmp_path)
    a, b = tmp_path / 'a', tmp_path / 'b'
    a.mkdir()
    b.mkdir()
    for root in (a, b):
        (root / 'data.bin').write_bytes(b'hello')
    config = tmp_path / 'config.yml'
    config.write_text('comparators: {}\n')
    output = tmp_path / 'comparison.zip'
    args = ['directory', str(a), str(b), '-c', str(config), '--crate', '-o', str(output)]
    if embed:
        args += ['--include-files']
    result = CliRunner().invoke(compare, args)
    assert result.exit_code == 0, result.output
    assert not (tmp_path / 'comparison_result.json').exists()
    with zipfile.ZipFile(output) as archive:
        assert archive.testzip() is None
        report = json.loads(archive.read('comparison_result.json'))
        assert report['verdict'] == 'PASS'
        assert archive.read('config.yml') == config.read_bytes()
        graph = json.loads(archive.read('ro-crate-metadata.json'))['@graph']
        root = next(e for e in graph if e['@id'] == './')
        assert len(root['mentions']) == 3
        assert ('run1/data.bin' in archive.namelist()) == embed
        assert ('run2/data.bin' in archive.namelist()) == embed


def test_empty_crate_preserves_incomplete_verdict(tmp_path):
    a, b = tmp_path / 'a', tmp_path / 'b'
    a.mkdir()
    b.mkdir()
    config = tmp_path / 'config.yml'
    config.write_text('comparators: {}\n')
    output = tmp_path / 'comparison.zip'
    result = CliRunner().invoke(compare, ['directory', str(a), str(b), '-c', str(config), '--crate', '-o', str(output)])
    assert result.exit_code == 1
    with zipfile.ZipFile(output) as archive:
        graph = json.loads(archive.read('ro-crate-metadata.json'))['@graph']
        assert next(e for e in graph if e['@id'] == '#overall-comparison')['value'] == 'NOT_CHECKED'
