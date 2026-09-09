"""Standalone, escaped HTML report with native expandable details."""
from html import escape
import json
from pathlib import Path
from .NumpyEncoder import NumpyEncoder


def write_html(summary, output):
    def esc(value):
        return escape(str(value), quote=True)
    def details(value):
        return '<pre>' + esc(json.dumps(value, indent=2, cls=NumpyEncoder, ensure_ascii=False)) + '</pre>'
    rows = []
    for entry in summary['comparisons']:
        rows.append('<tr><td>' + esc(entry['run1_path']) + '<br><small>↔ ' + esc(entry['run2_path']) + '</small></td><td>'
                    + esc(entry['verdict']) + '</td><td>' + esc(entry.get('method', '')) + '</td><td>'
                    + esc(entry.get('reason') or '') + '<details><summary>Details</summary>' + details(entry) + '</details></td></tr>')
    coverage = {key: summary.get(key) for key in ('missing_required_outputs', 'files_only_in_run1', 'files_only_in_run2', 'excluded_files', 'incomplete_runs')}
    html = '''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Workflow output comparison</title><style>
body{font:16px/1.5 system-ui,sans-serif;max-width:1150px;margin:40px auto;padding:0 24px;color:#182c36;background:#f8fafb}
h1{margin-bottom:4px}small{color:#536875}table{border-collapse:collapse;width:100%;background:white}td,th{text-align:left;padding:12px;border-bottom:1px solid #dce4e8;vertical-align:top;overflow-wrap:anywhere}
pre{white-space:pre-wrap;overflow-wrap:anywhere;background:#eef3f6;padding:16px;font-size:13px}summary{cursor:pointer;color:#165978}section{margin:28px 0}.status{font-size:24px;font-weight:700}
</style><h1>Workflow output comparison</h1>'''
    html += '<small>' + esc(summary['metadata']['timestamp']) + ' · report schema ' + esc(summary['schema_version']) + '</small>'
    html += '<section><div class="status">' + esc(summary['verdict']) + '</div><p>' + esc(summary['files_matching']) + ' / ' + esc(summary['files_compared']) + ' pairs match · ' + esc(summary['files_differing']) + ' differ · ' + esc(summary['files_errored']) + ' errors</p><p>' + esc(summary.get('reason') or '') + '</p></section>'
    html += '<section><h2>Compared outputs</h2><p>Paths are relative to their respective run roots.</p><table><thead><tr><th>Outputs</th><th>Status</th><th>Method</th><th>Findings</th></tr></thead><tbody>' + ''.join(rows) + '</tbody></table></section>'
    html += '<section><h2>Coverage and completeness</h2>' + details(coverage) + '</section><section><details><summary>Configuration, software and input provenance</summary>' + details(summary['metadata']) + '</details></section></html>'
    Path(output).write_text(html, encoding='utf-8')
