"""Scientific output contracts: semantic matches, schema changes and explicit errors."""
import io
import zipfile

import numpy as np
import pandas as pd
import pytest

from comparators.config import validate_settings
from comparators.manager import ComparisonManager


def compare(a, b, **settings):
    return ComparisonManager().compare_files(a, b, settings)


@pytest.mark.parametrize('kind,settings', [
    ('json', {'abs_tol': True}), ('numpy', {'rtol': 10**1000}),
    ('hdf5', {'check_attributes': 'false'}), ('numpy', {'equal_nan': 1}),
    ('hdf5', {'check_dtype': None}), ('json', {'rel_tol': 'nan'}),
    ('numpy', {'atol': -1}), ('json', {'rel_tol': float('inf')}),
    ('tabular', {'required_columns': ['id', 'id']}),
    ('tabular', {'skiprows': [True]}), ('hdf5', {'tolerance': 1}),
])
def test_strict_scientific_settings(kind, settings):
    with pytest.raises(ValueError):
        validate_settings(kind, settings)


def test_scientific_notation_settings_normalized():
    assert validate_settings('numpy', {'rtol': '1e-8', 'equal_nan': False}) == {
        'rtol': 1e-8, 'equal_nan': False}


@pytest.mark.parametrize('left,right,settings,verdict', [
    ('{"a":1,"b":[2,3]}', '{"b":[2,3],"a":1}', {}, 'PASS'),
    ('[1,2]', '[2,1]', {}, 'FAIL'),
    ('true', '1', {}, 'FAIL'),
    ('{"a":null}', '{}', {}, 'FAIL'),
    ('{"a":1,"a":1}', '{}', {}, 'ERROR'),
    ('Infinity', 'Infinity', {}, 'ERROR'),
    ('{broken', '{}', {}, 'ERROR'),
    ('1.00000000000000000000000000001', '1.0', {}, 'FAIL'),
    # This boundary was rounded to a match by Decimal's default precision.
    ('1.00000000000000000000000000001', '0.0', {'abs_tol': 1}, 'FAIL'),
    ('1.0', '1.00001', {'abs_tol': .001}, 'PASS'),
    ('9007199254740993', '9007199254740992', {'abs_tol': 10}, 'FAIL'),
])
def test_json_semantics(tmp_path, left, right, settings, verdict):
    a, b = tmp_path / 'a.json', tmp_path / 'b.json'
    a.write_text(left)
    b.write_text(right)
    assert compare(a, b, **settings)['verdict'] == verdict


def test_json_difference_paths_are_escaped_and_bounded(tmp_path):
    a, b = tmp_path / 'a.json', tmp_path / 'b.json'
    a.write_text('{"a/b~":1}')
    b.write_text('{"a/b~":2}')
    assert compare(a, b)['differences'][0]['path'] == '/a~1b~0'
    a.write_text(str([0] * 30))
    b.write_text(str([1] * 30))
    result = compare(a, b)
    assert result['metrics']['differences'] == 30
    assert len(result['differences']) == 20


@pytest.mark.parametrize('left,right,settings,verdict', [
    (np.array([2**63], 'u8'), np.array([2**63-1], 'i8'), {'check_dtype': False}, 'FAIL'),
    (np.array([2**53+1], 'i8'), np.array([2**53], 'f8'), {'check_dtype': False}, 'FAIL'),
    (np.array([2**53+1], 'i8'), np.array([2**53], 'f8'), {'check_dtype': False, 'atol': 1}, 'PASS'),
    (np.array([1], 'i4'), np.array([1], 'i8'), {}, 'FAIL'),
    (np.array([1], 'i4'), np.array([1], 'i8'), {'check_dtype': False}, 'PASS'),
    (np.array([1], 'i8'), np.array([2], 'i8'), {'atol': 100}, 'FAIL'),
    (np.array([True]), np.array([1]), {'check_dtype': False}, 'FAIL'),
    (np.array([1e308]), np.array([-1e308]), {'rtol': 1.9}, 'FAIL'),
    (np.array([1e308]), np.array([-1e308]), {'rtol': 2}, 'PASS'),
    (np.array([np.inf]), np.array([np.inf]), {}, 'PASS'),
    (np.array([np.inf]), np.array([-np.inf]), {'rtol': 100}, 'FAIL'),
    (np.array([np.nan]), np.array([np.nan]), {}, 'FAIL'),
    (np.array([np.nan]), np.array([np.nan]), {'equal_nan': True}, 'PASS'),
    (np.array([1+2j]), np.array([1+2.00001j]), {'atol': .001}, 'PASS'),
    (np.array(['alpha']), np.array(['beta']), {}, 'FAIL'),
    (np.array('alpha'), np.array('alpha'), {}, 'PASS'),
    (np.empty((0, 3)), np.empty((0, 3)), {}, 'PASS'),
    (np.empty((0, 3)), np.empty((0, 4)), {}, 'FAIL'),
    (np.array([(1,)], dtype=[('id', 'i4')]), np.array([(1,)], dtype=[('id', 'i4')]), {}, 'ERROR'),
])
def test_numpy_values(tmp_path, left, right, settings, verdict):
    a, b = tmp_path / 'a.npy', tmp_path / 'b.npy'
    np.save(a, left)
    np.save(b, right)
    assert compare(a, b, **settings)['verdict'] == verdict
    assert compare(b, a, **settings)['verdict'] == verdict


def test_npz_keys_compression_and_duplicates(tmp_path):
    a, b = tmp_path / 'a.npz', tmp_path / 'b.npz'
    np.savez(a, ids=np.array([1, 2]), values=np.array([3., 4.]))
    np.savez_compressed(b, values=np.array([3., 4.]), ids=np.array([1, 2]))
    assert compare(a, b)['verdict'] == 'PASS'
    np.savez(b, ids=np.array([1, 2]))
    assert compare(a, b)['verdict'] == 'FAIL'
    buffer = io.BytesIO()
    np.save(buffer, [1, 2])
    with zipfile.ZipFile(b, 'w') as archive:
        archive.writestr('ids.npy', buffer.getvalue())
        with pytest.warns(UserWarning, match='Duplicate name'):
            archive.writestr('ids.npy', buffer.getvalue())
    assert compare(a, b)['verdict'] == 'ERROR'


@pytest.fixture
def h5_pair(tmp_path):
    h5py = pytest.importorskip('h5py')
    a, b = tmp_path / 'a.h5', tmp_path / 'b.h5'
    for path in (a, b):
        with h5py.File(path, 'w') as f:
            f.attrs['experiment'] = 'test'
            group = f.create_group('measurements')
            group.attrs['version'] = 1
            data = group.create_dataset('values', data=[1., 2.])
            data.attrs['units'] = 'seconds'
            f.create_dataset('scalar', data=2.)
            f.create_dataset('labels', data=['alpha', 'beta'], dtype=h5py.string_dtype('utf-8'))
            f.create_dataset('fixed', data=np.array([b'a', b'b']))
            f.create_dataset('empty', shape=(0, 3), dtype='f8')
            f.create_dataset('null', dtype='f8')
            f.create_group('empty_group')
    return h5py, a, b


def test_hdf5_strings_scalars_null_empty_and_attributes(h5_pair):
    _, a, b = h5_pair
    result = compare(a, b)
    assert result['verdict'] == 'PASS', result
    assert result['summary']['datasets_compared'] == 6
    assert result['summary']['attributes_compared'] == 3


@pytest.mark.parametrize('location', ['/', 'measurements', 'measurements/values'])
def test_hdf5_attribute_changes_and_opt_out(h5_pair, location):
    h5py, a, b = h5_pair
    with h5py.File(b, 'a') as f:
        f[location].attrs['additional'] = 'metadata'
    assert compare(a, b)['verdict'] == 'FAIL'
    assert compare(a, b, check_attributes=False)['verdict'] == 'PASS'


def test_hdf5_changed_units(h5_pair):
    h5py, a, b = h5_pair
    with h5py.File(b, 'a') as f:
        f['measurements/values'].attrs['units'] = 'milliseconds'
    result = compare(a, b)
    assert result['verdict'] == 'FAIL'
    assert any('units' in item for item in result['differences'])


@pytest.mark.parametrize('change', ['labels', 'scalar', 'empty_group', 'null', 'dtype', 'shape'])
def test_hdf5_content_and_schema_changes(h5_pair, change):
    h5py, a, b = h5_pair
    with h5py.File(b, 'a') as f:
        if change == 'labels':
            f['labels'][0] = 'changed'
        elif change == 'scalar':
            f['scalar'][()] = 3.
        elif change == 'empty_group':
            del f['empty_group']
        elif change == 'null':
            del f['null']
            f.create_dataset('null', shape=(0,), dtype='f8')
        else:
            del f['scalar']
            f.create_dataset('scalar', data=2 if change == 'dtype' else [2.])
    assert compare(a, b)['verdict'] == 'FAIL'


def test_hdf5_tolerance_nan_and_dtype(h5_pair):
    h5py, a, b = h5_pair
    with h5py.File(b, 'a') as f:
        f['scalar'][()] = 2.000001
    assert compare(a, b)['verdict'] == 'PASS'
    assert compare(a, b, atol=0, rtol=0)['verdict'] == 'FAIL'
    for path in (a, b):
        with h5py.File(path, 'a') as f:
            f['scalar'][()] = np.nan
    assert compare(a, b)['verdict'] == 'FAIL'
    assert compare(a, b, equal_nan=True)['verdict'] == 'PASS'
    for path, dtype in ((a, 'i4'), (b, 'i8')):
        with h5py.File(path, 'a') as f:
            del f['scalar']
            f.create_dataset('scalar', data=np.array(2, dtype=dtype))
    assert compare(a, b)['verdict'] == 'FAIL'
    assert compare(a, b, check_dtype=False)['verdict'] == 'PASS'


@pytest.mark.parametrize('kind', ['soft', 'external', 'cycle', 'alias', 'external_data', 'virtual', 'compound', 'reference', 'ragged'])
def test_hdf5_unsupported_data_is_error(h5_pair, kind):
    h5py, a, b = h5_pair
    with h5py.File(b, 'a') as f:
        if kind == 'soft':
            f['linked'] = h5py.SoftLink('/missing')
        elif kind == 'external':
            f['linked'] = h5py.ExternalLink('missing.h5', '/values')
        elif kind == 'cycle':
            f['loop'] = f
        elif kind == 'alias':
            f['alias'] = f['scalar']
        elif kind == 'external_data':
            f.create_dataset('external_data', (1,), dtype='f8', external=[('missing.raw', 0, 8)])
        elif kind == 'virtual':
            layout = h5py.VirtualLayout(shape=(1,), dtype='f8')
            layout[:] = h5py.VirtualSource('missing.h5', '/values', shape=(1,))
            f.create_virtual_dataset('virtual', layout)
        elif kind == 'compound':
            f.create_dataset('compound', data=np.array([(1,)], dtype=[('id', 'i4')]))
        elif kind == 'reference':
            f.create_dataset('reference', (1,), dtype=h5py.ref_dtype)
        else:
            f.create_dataset('ragged', (1,), dtype=h5py.vlen_dtype(np.dtype('f8')))
    result = compare(a, b)
    assert result['verdict'] == 'ERROR', result
    assert 'unsupported' in result['reason']


def test_parquet_semantics_and_cross_format(tmp_path):
    pytest.importorskip('pyarrow')
    a, b, csv = tmp_path / 'a.parquet', tmp_path / 'b.parquet', tmp_path / 'a.csv'
    frame = pd.DataFrame({'id': ['a', 'b'], 'value': [1., 2.], 'optional': [3., np.nan]})
    frame.to_parquet(a, index=False, compression=None)
    frame.iloc[::-1].to_parquet(b, index=False, compression='gzip')
    frame.to_csv(csv, index=False)
    settings = {'join_columns': ['id'], 'required_columns': ['id', 'value'], 'abs_tol': 0, 'rel_tol': 0}
    assert compare(a, b, **settings)['verdict'] == 'PASS'
    assert compare(csv, b, **settings)['verdict'] == 'PASS'
    assert compare(b, csv, **settings)['verdict'] == 'PASS'
    frame.loc[0, 'value'] += .001
    frame.to_parquet(b, index=False)
    assert compare(a, b, **settings)['verdict'] == 'FAIL'
    assert compare(a, b, **dict(settings, abs_tol=.01))['verdict'] == 'PASS'
    assert compare(a, b, required_columns=['missing'])['verdict'] == 'FAIL'
    assert compare(a, b, skiprows=1)['verdict'] == 'ERROR'


def test_cross_csv_tsv_and_case_insensitive_routing(tmp_path):
    a, b = tmp_path / 'A.CSV', tmp_path / 'B.TSV'
    a.write_text('id,value\na,1\n')
    b.write_text('id\tvalue\na\t1\n')
    assert compare(a, b)['verdict'] == 'PASS'


def test_python_produced_run_fixture_through_cli(tmp_path):
    pytest.importorskip('pyarrow')
    pytest.importorskip('h5py')
    import json
    from pathlib import Path
    import runpy
    from click.testing import CliRunner
    from comparators.comparison_cli import compare as cli

    create = runpy.run_path(str(Path(__file__).parents[1] / 'examples/scientific/create_fixture.py'))['create_fixture']
    root = tmp_path / 'example'
    create(root)
    report = tmp_path / 'report.json'
    args = ['directory', str(root / 'reference'), str(root / 'rerun'),
            '--subdir', 'outputs', '--config', str(root / 'comparison.yml'),
            '--manifest-path', 'metadata/run.json', '--output', str(report)]
    result = CliRunner().invoke(cli, args)
    assert result.exit_code == 0, result.output
    payload = json.loads(report.read_text())
    assert payload['files_matching'] == 5
    assert payload['verdict'] == 'PASS'
    assert str(tmp_path) not in report.read_text()
    np.save(root / 'rerun/outputs/values.npy', np.array([9., 9., 9.]))
    result = CliRunner().invoke(cli, args)
    assert result.exit_code == 1, result.output
    payload = json.loads(report.read_text())
    assert payload['files_differing'] == 1
    assert payload['files_errored'] == 0


def test_hdf5_compression_is_ignored(h5_pair):
    h5py, a, b = h5_pair
    with h5py.File(b, 'a') as f:
        del f['measurements/values']
        f.create_dataset('measurements/values', data=[1., 2.], compression='gzip').attrs['units'] = 'seconds'
    assert compare(a, b)['verdict'] == 'PASS'


def test_hdf5_enum_metadata_and_reference_attributes(h5_pair):
    h5py, a, b = h5_pair
    for path, label in ((a, 'yes'), (b, 'no')):
        with h5py.File(path, 'a') as f:
            f.create_dataset('enum', data=[1], dtype=h5py.enum_dtype({label: 1}, basetype='i4'))
    assert compare(a, b)['verdict'] == 'FAIL'
    assert compare(a, b, check_dtype=False)['verdict'] == 'PASS'
    for path in (a, b):
        with h5py.File(path, 'a') as f:
            f.attrs.create('refs', np.empty(0, dtype=h5py.ref_dtype))
    assert compare(a, b)['verdict'] == 'ERROR'
    assert compare(a, b, check_attributes=False, check_dtype=False)['verdict'] == 'PASS'
