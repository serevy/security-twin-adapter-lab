#!/usr/bin/env python3
"""Generate only four explicitly selected static files; no repository-wide publishing."""
import argparse
import json
from pathlib import Path
from string import Template

from evidence import REPOSITORY, SCENARIOS, read_json, validate

ROOT = Path(__file__).resolve().parents[1]


def badge(status):
    return f'<span class="badge {status.lower()}">{status.replace("_", " ")}</span>'


def render(snapshot):
    data = validate(snapshot)
    status, values, src = data['status'], data['checks'], data['source']
    passed = sum(v == 'PASS' for v in values.values())
    repo = f'https://github.com/{REPOSITORY}'
    if src:
        run_url = f"{repo}/actions/runs/{src['run_id']}"
        commit_url = f"{repo}/commit/{src['head_sha']}"
        kind = 'Public artifact'
        provenance = f'''<dl class="provenance">
          <dt>Evidence source</dt><dd>{kind} · {src['evidence_id']}</dd>
          <dt>Workflow run</dt><dd><a href="{run_url}">#{src['run_id']} ↗</a></dd>
          <dt>Tested commit</dt><dd><a href="{commit_url}"><code>{src['head_sha'][:12]}</code> ↗</a></dd>
          <dt>Run updated (UTC)</dt><dd><time datetime="{src['updated_at']}">{src['updated_at']}</time></dd>
          <dt>Workflow outcome</dt><dd>{src['conclusion']}</dd>
        </dl>'''
        headline = 'Published synthetic evidence'
        detail = 'This is the latest published snapshot, not a live status feed. The tested commit and source run identify exactly what was verified.'
    else:
        provenance = '<p>No runtime evidence has been published in this snapshot. Bootstrap does not establish compatibility.</p>'
        headline = 'Bootstrap · awaiting evidence'
        detail = 'The public contract is a draft. Runtime checks remain NOT RUN until public evidence is imported and reviewed.'
    rows = ''.join(f'<tr><th scope="row">{label}</th><td>{badge(values[key])}</td></tr>'
                   for key, label in SCENARIOS.items())
    recovery = ''.join(f'<li><span>{label}</span>{badge(values[key])}</li>' for key, label in (
        ('explicit_rollback', 'Explicit rollback'), ('automatic_expiry', 'Automatic expiry'),
        ('partial_failure_visibility', 'Partial-failure visibility'), ('verified_clean_recovery', 'Verified clean recovery')))
    failure_note = ('<p class="notice">Execution failure: ' + ', '.join(data['execution_failures']) + '.</p>') if data['execution_failures'] else ''
    template = Template((ROOT / 'portal/index.html').read_text())
    return template.substitute(repo=repo, headline=headline, detail=detail, aggregate=badge(status),
                               passed=passed, total=len(values), provenance=provenance, rows=rows,
                               recovery=recovery, failure_note=failure_note)


def build(input_path, output):
    data = validate(read_json(input_path.read_bytes()))
    # Refuse a nonempty target: a stale log/source file must never hitchhike into Pages.
    if output.exists() and any(output.iterdir()):
        raise ValueError('Output directory must be empty')
    output.mkdir(parents=True, exist_ok=True)
    (output / 'index.html').write_text(render(data))
    (output / 'style.css').write_text((ROOT / 'portal/style.css').read_text())
    (output / 'result.json').write_text(json.dumps(data, indent=2) + '\n')
    (output / '.nojekyll').touch()
    return data


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', type=Path, default=ROOT / 'results/latest.json')
    parser.add_argument('--output', type=Path, default=ROOT / '_site')
    args = parser.parse_args()
    result = build(args.input, args.output)
    print(f"Portal built: {result['status']}; only index.html, style.css, result.json, .nojekyll")


if __name__ == '__main__':
    main()
