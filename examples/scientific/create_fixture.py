"""Create two tiny, synthetic completed runs for demonstrating the checker.

This is a test-data producer, not a workflow runner. Requires comparators[all].
The destination must not exist; no existing run is overwritten.
"""
import argparse
import json
from pathlib import Path

import h5py
import numpy as np
import pandas as pd


def create_fixture(destination):
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=False)
    for name, delta in [('reference', 0.), ('rerun', 0.000001)]:
        root = destination / name
        outputs = root / 'outputs'
        outputs.mkdir(parents=True)
        (root / 'metadata').mkdir()
        (root / 'metadata/run.json').write_text(json.dumps({
            'schema_version': 1, 'status': 'completed',
            'parameters': {'example': 'synthetic scientific outputs'},
        }), encoding='utf-8')
        values = np.array([1., 2., 3.], dtype='float64') + delta
        ids = np.array([1, 2, 3], dtype='int64')
        np.save(outputs / 'values.npy', values, allow_pickle=False)
        np.savez_compressed(outputs / 'arrays.npz', ids=ids, values=values)
        pd.DataFrame({'id': ids, 'value': values}).to_parquet(outputs / 'table.parquet', index=False)
        with h5py.File(outputs / 'data.h5', 'w') as f:
            f.create_dataset('values', data=values).attrs['units'] = 'seconds'
            f.create_dataset('ids', data=ids)
            f.attrs['schema_version'] = 1
        (outputs / 'metrics.json').write_text(json.dumps({
            'schema_version': 1, 'count': 3, 'mean': float(values.mean())
        }, allow_nan=False), encoding='utf-8')
    (destination / 'comparison.yml').write_text('''schema_version: 1
required_outputs: [values.npy, arrays.npz, table.parquet, data.h5, metrics.json]
comparators:
  "*.npy": {type: numpy, atol: 0.00001, rtol: 0, check_dtype: true}
  "*.npz": {type: numpy, atol: 0.00001, rtol: 0, check_dtype: true}
  "*.parquet": {type: tabular, join_columns: [id], required_columns: [id, value], abs_tol: 0.00001, rel_tol: 0}
  "*.h5": {type: hdf5, atol: 0.00001, rtol: 0, check_attributes: true, check_dtype: true}
  "*.json": {type: json, abs_tol: 0.00001, rel_tol: 0}
''', encoding='utf-8')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('destination', type=Path)
    create_fixture(parser.parse_args().destination)
