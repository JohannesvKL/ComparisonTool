# Scientific outputs and comparison policy

ComparisonTool consumes **completed output files**. A Python script needs no special function signature, import hook or notebook wrapper. Its runner writes a run directory, and the checker compares that directory with another completed run. Execution, timing, environment capture and benchmarking remain the runner's responsibility.

## Supported formats

| Output | Comparator | Content checked | Dependencies |
|---|---|---|---|
| `.json` | `json` | Nested objects, ordered lists, scalar values; object key order/whitespace ignored | Core installation |
| `.npy`, `.npz` | `numpy` | Array names, shape, dtype and values; NPZ key order/compression ignored | Core NumPy |
| `.h5`, `.hdf5` | `hdf5` | Group/dataset paths, empty groups, shapes, dtype, values, and root/group/dataset attributes | `pip install '.[hdf5]'` |
| `.parquet` | `tabular` | Scalar columns and rows joined by keys; file compression/row order ignored | `pip install '.[parquet]'` |
| `.csv`, `.tsv`, `.xlsx` | `tabular` | Same table comparison; explicit pairs may mix table formats | Core; `.[excel]` for XLSX |

`pip install '.[all]'` and the Docker image include all these dependencies. Extension detection for these formats is case-insensitive. YAML patterns remain case-sensitive. A matching YAML rule takes priority over automatic format detection. Use `type: binary` if byte-for-byte equality is the intended policy.

## Numerical policy

JSON, NumPy and HDF5 use the symmetric rule:

```text
abs(a - b) <= absolute_tolerance + relative_tolerance * max(abs(a), abs(b))
```

| Comparator | Absolute tolerance | Relative tolerance | Additional defaults |
|---|---|---|---|
| JSON | `abs_tol: 0` | `rel_tol: 0` | Integer-to-integer comparisons are exact |
| NumPy | `atol: 0` | `rtol: 0` | `check_dtype: true`, `equal_nan: false` |
| HDF5 | `atol: 1e-8` | `rtol: 1e-5` | `check_dtype: true`, `equal_nan: false`, `check_attributes: true` |
| Tables | `abs_tol: 1e-5` | `rel_tol: 0.01` | `join_columns`: first column; no required columns unless declared |

Choose tolerances in the units of the output. HDF5 tolerances apply to floating attributes as well as datasets. Integer and boolean arrays are compared exactly, even with nonzero tolerances. Disabling dtype checks permits integer width changes and integer/float comparison without rounding large integer IDs. Booleans remain distinct from numbers. JSON numbers retain their decimal precision when evaluating tolerances; duplicate keys, malformed JSON and NaN/Infinity are errors.

NumPy/HDF5 floating and complex arrays compare infinities only when equal. NaNs fail by default; `equal_nan: true` allows paired NaNs. For complex values, a NaN in either component marks the entire value as NaN. Strings are exact. NumPy datetime/timedelta arrays are exact, and NaT is unequal (the `equal_nan` switch applies to floating/complex values).

Tables retain DataComPy's semantics: relative tolerance is scaled to the second table's value, and paired missing values compare equal. Table tolerances can therefore differ from array/JSON verdicts at their boundaries. Explicitly select stable, unique, non-null `join_columns`; the tool does not enforce uniqueness/non-nullness as a separate schema rule. Put required column names in `required_columns` so a column missing from both runs still fails. Keep identifiers as columns rather than only in a Parquet index. Nested Parquet list/struct columns are outside the supported contract; export them as separate scalar tables/arrays or use a custom comparator.

CSV/TSV support `comment` and `skiprows`; XLSX supports `skiprows` and reads the first sheet. Parquet rejects `skiprows` and non-null `comment`; Excel rejects non-null `comment`, so unsupported reader settings cannot silently change the intended policy.

## HDF5 coverage and boundaries

Numeric and complex datasets, scalar datasets, fixed/variable-length strings, zero-length arrays and null dataspaces are supported. Null dataspaces and zero-length arrays are distinct. Compression, chunk layout and object insertion order are ignored. Attribute names, values and dtypes are checked, including units and root/group metadata. Dtype checks include HDF5 string encoding and enum metadata. Set `check_attributes: false` only when ignoring all attributes is an intentional scientific policy.

This expands the previous numeric-only behavior: metadata changes, dtype changes and missing empty groups can now fail. HDF5 floating tolerance is now symmetric, and integer values are exact. Preserve any intended earlier policy explicitly in YAML and review these changes before comparing against historical verdicts.

The supported HDF5 structure is a self-contained tree. Soft/external links, hard-link aliases/cycles, virtual datasets, external raw storage, named datatypes, compound/opaque values, object references and variable-length numeric/ragged data produce **ERROR** instead of an incomplete PASS. Materialize linked data and export compound fields as separate datasets/tables. NumPy object/pickled and structured arrays also produce ERROR; loading never enables pickle.

Datasets/arrays are loaded into memory; this version does not stream large arrays or guarantee bounded memory for large compressed files. An empty array, empty NPZ archive or empty HDF5 tree may match another with the same schema. File/column presence checks do not assert a minimum sample count, array size or dataset list. Those richer scientific schema checks remain future work.

HDF5 handling uses the documented [h5py group/link API](https://docs.h5py.org/en/stable/high/group.html) and [dataset API](https://docs.h5py.org/en/stable/high/dataset.html).

## Contract for Python-produced outputs

```text
run-001/
  outputs/
    metrics.json
    values.npy
    arrays.npz
    data.h5
    table.parquet
  metadata/
    run.json                 # optional runner manifest
```

Write stable filenames under `outputs/`, use the same array/dataset names and shapes across comparable runs, and retain consistent units/dtypes. Write machine-readable metrics to files; console output alone is not a result contract. Keep logs, timestamps and transient files outside `outputs/` or explicitly exclude them. The runner should finish and close all output files before invoking the checker.

Use `required_outputs` in the comparison YAML to detect outputs absent from either or both runs. Paths and pairing rules are relative to `--subdir outputs`. For renamed or cross-format tables, supply explicit `file_pairs`. JSON has no per-field tolerance settings in this version: separate metrics with different policies into separate files.

Optional `metadata/run.json` has this minimum content:

```json
{"schema_version": 1, "status": "completed"}
```

Pass `--manifest-path metadata/run.json` to check it. `running` and `failed` statuses fail the assessment; other metadata is retained as supplied. The checker does not independently prove that the runner completed or that recorded performance measurements are valid. See [usage.md](usage.md) for report fields, pairing, exclusions and exit codes.

## Try the synthetic Python example

[create_fixture.py](examples/scientific/create_fixture.py) generates two small completed-run fixtures containing JSON, NPY, NPZ, HDF5 and Parquet, plus manifests and a strictly validated configuration. It does not execute or benchmark a workflow. The destination must not already exist.

From this repository, after installing `.[all]`:

```bash
python examples/scientific/create_fixture.py /tmp/comparison-scientific-example
compare directory /tmp/comparison-scientific-example/reference \
  /tmp/comparison-scientific-example/rerun --subdir outputs \
  --config /tmp/comparison-scientific-example/comparison.yml \
  --manifest-path metadata/run.json \
  --output /tmp/scientific-report.json --html-output /tmp/scientific-report.html
```

Expected: five matching pairs, overall PASS. The rerun has small floating differences accepted by its explicitly declared tolerances. Tests also change one array beyond tolerance and assert FAIL. All output paths in reports remain relative, so moving the runs does not change their comparison identities. For container mounts and offline execution, see [DOCKER.md](DOCKER.md).
