# Configuration and result guide

## Version 0.3 changes

Unknown/duplicate YAML keys and unsupported comparator settings are rejected. Tolerances must be finite and nonnegative; booleans and mode names are checked. Legacy example configs may need policy review.

`required_outputs: [predictions.csv, metrics.json]` requires those paths in **both** run scan directories, including when absent from both. For different filenames, use `required_outputs: {run1: [old.csv], run2: [new.csv]}` alongside `file_pairs`. Required outputs cannot also be excluded. Tabular `required_columns` checks column presence independently of equality.

Reports declare `schema_version: "1.0"`. Each comparison's `run1_path` and `run2_path` is relative to its own run root, including the selected subdirectory. `metadata.runs` contains logical IDs and input artifact hashes. Embedded crates give each run a root prefix (`run1/`, `run2/`); nonembedded runs have `root: null` and must be supplied separately. Generated reports no longer depend on absolute host/container input paths. Explicit paths or other values supplied inside custom configuration/runner metadata are preserved.

Optional `--manifest-path metadata/run.json` reads runner metadata from each run root. It requires `schema_version: 1` and status `completed`, `running` or `failed`; noncompleted runs fail the assessment. Other metadata is preserved as supplied, not independently verified. The collaborator's runner remains outside this tool's scope.

`--html-output report.html` writes a standalone report. Reports must live outside both run directories. Output symlinks are rejected to keep artifact paths self-contained.

Additional formats:

| Type | Settings | Behavior |
|---|---|---|
| `json` | `abs_tol`, `rel_tol`, both default 0 | Object key order is ignored; list order matters. Integer values remain exact. JSON NaN/Infinity and duplicate keys are errors. |
| `numpy` | `atol`, `rtol`, both 0; `equal_nan: false`; `check_dtype: true` | `.npy`/`.npz` shapes and arrays are compared; integers/booleans are exact. Object/structured arrays are unsupported. |
| `tabular` | Existing table settings plus `required_columns` | Also handles `.parquet`, requiring the `parquet` extra (included in the Docker image). |

JSON/NumPy/HDF5 floating-point tolerance uses `abs(a-b) <= atol + rtol * max(abs(a), abs(b))`. `type: binary` remains available for byte-level comparison of any format. These defaults change automatic JSON routing from version 0.2; explicitly select binary when retaining an old policy. See [Scientific formats and Python output contract](SCIENTIFIC_FORMATS.md) for the full coverage matrix, HDF5 migration notes, limitations and a runnable example.

## YAML example

```yaml
comparators:
  "tables/*.tsv":
    type: tabular
    join_columns: [gene_id]
    abs_tol: 0.0001
    rel_tol: 0.01
    comment: "#"
  "*.png":
    type: image
    ssim_threshold: 0.99
  "*.bam":
    type: bam
    mode: full
  "*.json":
    type: binary
file_pairs:
  - run1: tables/old-name.tsv
    run2: tables/new-name.tsv
exclude:
  - .DS_Store
  - temporary/
exclude_extensions: [log, tmp]
```

`comparators: {}` enables the default format routing. Empty/non-mapping YAML is rejected. Comparator entries require `type`. **The first matching pattern wins**, in YAML order, for both type and settings; put specific patterns before broad patterns. Patterns match the run1 path relative to `--subdir`, case-sensitively. `*.csv` also matches nested paths using Python's fnmatch rules. Files with no matching rule use the first format comparator that recognizes their extension, with binary equality as fallback.

Files are automatically paired by the same relative path. `file_pairs` handles renamed outputs and must be one-to-one. Missing explicitly named files produce an error. `exclude` matches exact paths or directory prefixes, not wildcard globs. Extension exclusions are case-insensitive and may omit the dot. Explicit pairs bypass extension exclusions, but cannot reference path-excluded files.

## Comparator settings

| `type` | Main settings/defaults | Assessment |
|---|---|---|
| `tabular` | `join_columns`: first column; `abs_tol`: `1e-5`; `rel_tol`: `0.01`; optional `required_columns`; CSV/TSV `comment`/`skiprows`, XLSX `skiprows` | DataComPy row/key comparison for CSV, TSV, XLSX and Parquet, including explicit cross-format pairs. |
| `image` | `ssim_threshold`: `0.95`; optional `win_size` | SSIM for PNG/JPG/JPEG/TIFF; equal dimensions required. Very small images use pixel equality. |
| `hdf5` | `rtol`: `1e-5`; `atol`: `1e-8`; `equal_nan`: false; `check_dtype`: true; `check_attributes`: true | Dataset/group presence, numeric/string/scalar values, shapes, dtypes and attributes; requires a self-contained tree. |
| `fasta` | `mode`: `unordered`; alternatives `exact`, `content_only` | Sequence agreement with different ordering/identity policies. |
| `bam` | `mode`: `sample`; alternatives `binary`, `header`, `full`; `sample_size`: `10000` | Headers and selected alignments. Sampling uses the first N records and cannot establish full-file equality. |
| `vcf` | `mode`: `genotypes`; alternatives `positions`, `full` | Variant-position, genotype or fuller record comparison. |
| `binary` | None | SHA-256 equality for any file type. |
| `generic` | `user_comparison`: required; `timeout`: `60` seconds | Run a custom executable/argument list. |

These are the main controls, not every specialist bioinformatics setting. Further options are documented in the respective comparator's `compare` method. A tabular rule should use `abs_tol`/`rel_tol`, and an image rule `ssim_threshold`; a generic `tolerance` field is not interchangeable with them.

## Custom comparison

```yaml
comparators:
  "*.json":
    type: generic
    user_comparison: [python3, /absolute/path/to/compare_json.py]
    timeout: 30
```

The tool appends the two resolved file paths, so the program receives `COMMAND [OPTIONS] FILE1 FILE2`. A string value denotes one executable path; use a YAML list for interpreter/arguments. No shell expansion, pipes or redirection are performed. Relative executable/script paths resolve from the current working directory; absolute paths are clearer for saved configurations.

Program exit codes: **0 = match, 1 = mismatch, any other code = execution error**. Timeout, a missing executable and permission failures are errors. Captured stdout/stderr is included as the reason on failure. `--custom` forces this path for every pair, requiring applicable `user_comparison` settings for every file.

## Reading results

- `verdict`: `PASS`, `FAIL`, `ERROR` or `NOT_CHECKED`.
- `overall_match`: true only when at least one pair was compared, all pairs passed, and no unmatched files remain.
- `files_compared`, `files_matching`, `files_differing`, `files_errored`: pair counts. Errors are separate from differences.
- `files_only_in_run1` / `files_only_in_run2`: non-excluded unmatched files; these fail the overall comparison.
- `comparisons`: run-relative paths, comparator metadata, verdict, method, settings and available detailed metrics/reports/hashes.
- `metadata`: run locations, timestamp, config path and selected subdirectory.

ERROR takes precedence over FAIL. Empty comparisons (including exclusions removing everything) are NOT_CHECKED unless unmatched files establish a failure. A missing scan directory is an input error. The JSON/RO-Crate report preserves these distinctions.

Historical reports used `files_differing` for both mismatches and tool errors. In version 0.2, use `files_differing + files_errored` for the old combined count. Static analysis and AI-quality JSON from DocumentationTool have a different schema; retain both reports alongside the recorded workflow/input/environment metadata rather than merging overlapping keys.
