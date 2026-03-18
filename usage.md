Some guidelines for using the tool are provided below. 

## Flags

There are a variety of different flags available to set for the tool, set them with '--' before the flag.

## Options

| Flag | Short | Required | Default | Description |
|-----------------|-------|----------|---------|-------------|
| `config` | `-c` | ✅ | — | Path to unified configuration YAML (comparators and file pairs). |
| `subdir` | `-s` | | `.` | Subdirectory within each run to scan for output files. |
| `output` | `-o` | | `comparison_result.json` / `comparison.crate.zip` | Path for the comparison result file. |
| `verbose` | `-v` | | `false` | Print per-file comparison results in addition to the summary. |
| `dry-run` | | | `false` | Resolve and list file pairs that would be compared, without running comparisons. |
| `crate` | | | `false` | Package the comparison result, config, and run references into an RO-Crate zip. |
| `include-files` | | | `false` | When using `--crate`, embed the run directories into the crate. Without this flag, runs are referenced as external URIs. |
| `custom` | | | `false` | Prioritize custom file handling. |


## Config 

## Config Structure

The config is divided into several sections:

---

**`comparators`**
Defines the comparison types used for different file patterns. This is where tolerances for differences between file pairs can be given, as well as your own comparison scripts.

**`file_pairs`**
Denotes files with different names between runs that should be matched together for the comparison.

**`exclude`**
Denotes files that should be ignored in the comparison, for example configs or timestamps that differ between runs.

**`exclude_extensions`**
Denotes entire file types that should be ignored in the comparison. This can include time-stamped file types or ones for which a reasonable comparison metric doesn't exist (yet).

---

Examples for these config files are available in `comparators` as `.yml` files.
