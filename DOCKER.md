# Docker usage

Run these commands from the **ComparisonTool repository**. The images package the checker only; the collaborator's runner remains responsible for producing workflow results.

## Build and test

```bash
docker build --target test -t workflow-comparison:test .
docker build --target release -t workflow-comparison:0.3.0 .
```

The test target installs the built wheel in a clean Linux image and runs the test suite. The release target excludes tests and build dependencies. Both stages use a digest-pinned Python 3.12 base and hash-verified Python dependency locks. Default runtime user: UID/GID `10001:10001`.

The lockfiles were resolved for Linux/Python 3.12. Local Docker validation uses Linux ARM64 on this Mac. The Docker CI job targets Linux AMD64; cross-platform success must be verified by that job before release. No images are pushed by CI.

## Run the bundled example

```bash
mkdir -p reports
docker run --rm --network none --read-only --tmpfs /tmp \
  --user "$(id -u):$(id -g)" \
  --mount "type=bind,src=$(pwd)/examples,dst=/inputs,readonly" \
  --mount "type=bind,src=$(pwd)/reports,dst=/reports" \
  workflow-comparison:0.3.0 directory /inputs/run1 /inputs/run2 \
  --config /inputs/comparison.yml --output /reports/comparison.json \
  --html-output /reports/comparison.html
```

For your own completed runs, bind-mount their directories read-only and pass the corresponding container paths. Use `--subdir outputs` when results are nested under `outputs/`. Reports must be outside both input runs.

Add `--crate --include-files --output /reports/comparison.zip` to carry input files in an RO-Crate. Without `--include-files`, the crate contains logical run IDs and hashes, not machine-specific `file://` locations. In JSON, `run1_path`/`run2_path` are relative to their run roots. Embedded crates add `metadata.runs.run1.root = "run1/"` (and `run2/`), so readers can resolve files after relocation.

This image includes the `all` format extra: tables/Excel/Parquet, images, HDF5, FASTA/BAM/VCF and NumPy/JSON. Custom comparison programs must be mounted/installed inside the container with their own dependencies; host executable paths do not automatically work there.

## Outputs, updates and verification

Inputs are read-only, the container root is read-only and `/tmp` is writable. `--user` maps the current host UID/GID so report files remain writable by the host user. Ensure the reports directory exists and is writable. Exit codes from the checker are preserved: 0 PASS, 1 failed/incomplete assessment, 2 execution/input error.

Refresh dependency locks deliberately, then rebuild/test:

```bash
./scripts/update-locks.sh
```

Update the pinned Python digest in both `Dockerfile` and the lock-update script together. Normal image builds do not resolve newer Python versions; they verify package hashes in `requirements.lock`. `requirements-build.lock` includes setuptools, wheel and pytest explicitly.

The image smoke test can run with no network and read-only input mounts. Image build and dependency updates need network access. Publishing images and adding workflow execution are outside this change.
