import sys
import json
import click
from pathlib import Path
from .manager import ComparisonManager
from .nonROCrateComp import DirectoryRunComparator
from .provenance import ensure_report_outside_runs


# ------------------------------------------------------------------
# Shared options
# ------------------------------------------------------------------

def shared_options(f):
    """Decorator that applies common options to both subcommands."""
    decorators = [
        click.argument('run1', type=click.Path(exists=True, file_okay=False)),
        click.argument('run2', type=click.Path(exists=True, file_okay=False)),
        click.option(
            '--config', '-c',
            required=True,
            type=click.Path(exists=True, dir_okay=False),
            help='Path to unified configuration YAML (comparators and file pairs).'
        ),
        click.option(
            '--subdir', '-s',
            default='.',
            show_default=True,
            help='Subdirectory within each run to scan for output files.'
        ),
        click.option(
            '--output', '-o',
            default=None,
            help='Path for the comparison result file. Defaults to comparison_result.json or comparison.crate.zip.'
        ),
        click.option(
            '--verbose', '-v',
            is_flag=True,
            default=False,
            help='Print per-file comparison results in addition to the summary.'
        ),
        click.option(
            '--dry-run',
            is_flag=True,
            default=False,
            help='Resolve and list file pairs that would be compared, without running comparisons.'
        ),
        click.option(
            '--crate',
            is_flag=True,
            default=False,
            help='Package the comparison result, config, and run references into an RO-Crate zip.'
        ),
        click.option(
            '--include-files',
            is_flag=True,
            default=False,
            help='When using --crate, embed the run directories into the crate. '
                 'Without this flag runs are identified by logical IDs and artifact hashes.'
        ),
        click.option('--manifest-path', default=None, help='Optional runner manifest path relative to each run root.'),
        click.option('--html-output', type=click.Path(dir_okay=False), help='Also write a standalone HTML report.'),
        click.option(
            '--custom', 
            is_flag=True, 
            default=False, 
            help="Choose whether or not the custom file handling should be prioritized"
        )
    ]
    for decorator in reversed(decorators):
        f = decorator(f)
    return f


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def _build_manager(config: str) -> ComparisonManager:
    try:
        return ComparisonManager.from_config(config)
    except (ValueError, KeyError, OSError) as e:
        raise click.UsageError(f"Invalid config: {e}")


def _dry_run(run1: str, run2: str, config: str, subdir: str):
    """Resolve and print file pairs without comparing."""
    from .file_resolver import OutputFileResolver
    resolver = OutputFileResolver()
    files1 = resolver.get_files_from_dir(run1, subdir)
    files2 = resolver.get_files_from_dir(run2, subdir)
    pairing = resolver.resolve_pairs(files1, files2, config)

    from .config import load_config, required_for
    policy = load_config(config)
    missing = {side: sorted(set(required_for(policy, side)) - files.keys())
               for side, files in [('run1', files1), ('run2', files2)]}
    for side, paths in missing.items():
        if paths:
            click.echo(f"Missing required outputs in {side}: {', '.join(paths)}")

    click.echo(f"\nDry run — {len(pairing.pairs)} pair(s) would be compared:\n")
    for label, f1, f2 in pairing.pairs:
        click.echo(f"  {label}")
        click.echo(f"    run1: {f1}")
        click.echo(f"    run2: {f2}")

    if pairing.only_in_run1:
        click.echo(f"\nOnly in run1 ({len(pairing.only_in_run1)}):")
        for p in pairing.only_in_run1:
            click.echo(f"  {p}")

    if pairing.only_in_run2:
        click.echo(f"\nOnly in run2 ({len(pairing.only_in_run2)}):")
        for p in pairing.only_in_run2:
            click.echo(f"  {p}")

    if any(missing.values()):
        raise click.exceptions.Exit(1)


def _print_summary(summary: dict, verbose: bool):
    """Print a human-readable summary of comparison results."""
    status = click.style(summary.get('verdict', 'PASS' if summary['overall_match'] else 'FAIL'), fg='green' if summary['overall_match'] else 'red')
    click.echo(f"\nResult: {status}")
    click.echo(
        f"  {summary['files_matching']}/{summary['files_compared']} files matched"
        + (f", {summary['files_differing']} differing" if summary['files_differing'] else "")
    )

    if summary.get('files_errored'):
        click.echo(f"  {summary['files_errored']} comparison errors")
    for side, paths in summary.get('missing_required_outputs', {}).items():
        if paths:
            click.echo(f"  Missing required outputs in {side}: {', '.join(paths)}")
    if summary.get('reason'):
        click.echo(f"  {summary['reason']}")

    if summary['files_only_in_run1']:
        click.echo(f"\n  Only in run1: {', '.join(summary['files_only_in_run1'])}")
    if summary['files_only_in_run2']:
        click.echo(f"\n  Only in run2: {', '.join(summary['files_only_in_run2'])}")

    if verbose:
        click.echo("\nPer-file results:")
        for entry in summary['comparisons']:
            filename = entry.get('filename', entry.get('label', ''))
            matched = entry.get('match') or entry.get('result', {}).get('match', False)
            icon = click.style("✓", fg='green') if matched else click.style("✗", fg='red')
            click.echo(f"  {icon}  {filename}")
            if not matched and entry.get('reason'):
                click.echo(f"       reason: {entry['reason']}")
            if verbose and entry.get('metrics'):
                click.echo(f"       metrics: {json.dumps(entry['metrics'])}")


def _exit_on_result(summary: dict):
    """Exit with code 1 if the overall comparison failed."""
    if summary.get('verdict') == 'ERROR':
        sys.exit(2)
    if not summary['overall_match']:
        sys.exit(1)


# ------------------------------------------------------------------
# CLI group and subcommands
# ------------------------------------------------------------------

@click.group()
def compare():
    """Compare outputs between two workflow runs."""
    pass


@compare.command()
@shared_options
def directory(run1, run2, config, subdir, output, verbose, dry_run, crate, include_files, custom, manifest_path, html_output):
    """Compare two workflow run directories."""
    if include_files and not crate:
        raise click.UsageError('--include-files requires --crate.')

    try:
        ensure_report_outside_runs(output or ('comparison.crate.zip' if crate else 'comparison_result.json'), run1, run2)
        ensure_report_outside_runs(html_output, run1, run2)
    except ValueError as e:
        raise click.UsageError(str(e)) from e
    manager = _build_manager(config)
    if dry_run:
        try:
            _dry_run(run1, run2, config, subdir)
        except (OSError, ValueError) as e:
            raise click.UsageError(str(e)) from e
        return
    comparator = DirectoryRunComparator(manager)

    if crate:
        json_path = None
        crate_path = output or 'comparison.crate.zip'
    else:
        json_path = output or 'comparison_result.json'

    click.echo(f"Comparing directory runs:\n  run1: {run1}\n  run2: {run2}")

    try:
        summary = comparator.compare_runs(
            run1, run2,
            config_path=config,
            subdir=subdir,
            output_path=json_path,
            custom=custom, manifest_path=manifest_path
        )
    except (OSError, ValueError) as e:
        raise click.UsageError(str(e)) from e

    if crate:
        from .crate_writer import ComparisonCrateWriter
        writer = ComparisonCrateWriter()
        try:
            writer.write(
                summary=summary,
                run1_path=run1,
                run2_path=run2,
                config_path=config,
                output_path=crate_path,
                include_files=include_files
            )
        except (OSError, ValueError) as e:
            raise click.UsageError(str(e)) from e
        click.echo(f"\nOutput written to: {crate_path}")
    else:
        click.echo(f"\nOutput written to: {json_path}")

    if html_output:
        from .html_report import write_html
        try:
            write_html(summary, html_output)
        except OSError as e:
            raise click.UsageError(str(e)) from e
    _print_summary(summary, verbose)
    _exit_on_result(summary)


if __name__ == '__main__':
    compare()