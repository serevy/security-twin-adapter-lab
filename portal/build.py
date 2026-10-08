#!/usr/bin/env python3
"""Generate only five explicitly selected static files; no repository-wide publishing."""
import argparse
import json
from pathlib import Path
from string import Template

from evidence import REPOSITORY, SCENARIOS, read_json, validate
from locales import LOCALES

ROOT = Path(__file__).resolve().parents[1]
PUBLIC_FILES = {'index.html', 'ja/index.html', 'style.css', 'result.json', '.nojekyll'}


def badge(status):
    return f'<span class="badge {status.lower()}">{status}</span>'


def render(snapshot, locale='en'):
    if locale not in LOCALES:
        raise ValueError('Unsupported locale')
    text = LOCALES[locale]
    if set(text['scenarios']) != set(SCENARIOS):
        raise ValueError('Incomplete scenario translation')
    base = '../' if locale == 'ja' else ''
    data = validate(snapshot)
    status, values, src = data['status'], data['checks'], data['source']
    passed = sum(v == 'PASS' for v in values.values())
    repo = f'https://github.com/{REPOSITORY}'
    if src:
        run_url = f"{repo}/actions/runs/{src['run_id']}"
        commit_url = f"{repo}/commit/{src['head_sha']}"
        kind = text['artifact']
        provenance = f'''<dl class="provenance">
          <dt>{text['source']}</dt><dd>{kind} · {src['evidence_id']}</dd>
          <dt>{text['run']}</dt><dd><a href="{run_url}">#{src['run_id']} ↗</a></dd>
          <dt>{text['commit']}</dt><dd><a href="{commit_url}"><code>{src['head_sha'][:12]}</code> ↗</a></dd>
          <dt>{text['updated']}</dt><dd><time datetime="{src['updated_at']}">{src['updated_at']}</time></dd>
          <dt>{text['outcome']}</dt><dd>{src['conclusion']}</dd>
        </dl>'''
        headline = text['headline']
        detail = text['detail']
    else:
        provenance = f"<p>{text['no_evidence']}</p>"
        headline = text['bootstrap_headline']
        detail = text['bootstrap_detail']
    rows = ''.join(f'<tr data-scenario="{key}"><th scope="row">{label}</th><td>{badge(values[key])}</td></tr>'
                   for key, label in text['scenarios'].items())
    recovery = ''.join(f'<li><span>{text["scenarios"][key]}</span>{badge(values[key])}</li>' for key in (
        'explicit_rollback', 'automatic_expiry', 'partial_failure_visibility', 'verified_clean_recovery'))
    failure_note = (f'<p class="notice">{text["execution_failure"]}: ' + ', '.join(data['execution_failures']) + '.</p>') if data['execution_failures'] else ''
    language_switch = (f'<nav class="language-switch" aria-label="{text["language_label"]}">'
                       f'<a href="{base or "./"}" lang="en" hreflang="en"'
                       + (' aria-current="page"' if locale == 'en' else '') + '>English</a>'
                       + '<span aria-hidden="true">|</span>'
                       + f'<a href="{"./" if locale == "ja" else "ja/"}" lang="ja" hreflang="ja"'
                       + (' aria-current="page"' if locale == 'ja' else '') + '>日本語</a></nav>')
    filename = 'index.ja.html' if locale == 'ja' else 'index.html'
    template = Template((ROOT / 'portal' / filename).read_text(encoding='utf-8'))
    return template.substitute(base=base, language_switch=language_switch, repo=repo, headline=headline, detail=detail, aggregate=badge(status),
                               passed=passed, total=len(values), provenance=provenance, rows=rows,
                               recovery=recovery, failure_note=failure_note)


def check_publication(output):
    paths = list(output.rglob('*'))
    if any(p.is_symlink() for p in paths) or {p.relative_to(output).as_posix() for p in paths} != PUBLIC_FILES | {'ja'}:
        raise ValueError('Unexpected publication path')
    if not all((output / path).is_file() for path in PUBLIC_FILES):
        raise ValueError('Missing publication file')


def build(input_path, output):
    data = validate(read_json(input_path.read_bytes()))
    # Refuse a nonempty target: a stale log/source file must never hitchhike into Pages.
    if output.exists() and any(output.iterdir()):
        raise ValueError('Output directory must be empty')
    output.mkdir(parents=True, exist_ok=True)
    # Both presentations derive from the same validated snapshot. JSON is written once.
    (output / 'index.html').write_text(render(data, 'en'), encoding='utf-8')
    (output / 'ja').mkdir()
    (output / 'ja/index.html').write_text(render(data, 'ja'), encoding='utf-8')
    (output / 'style.css').write_text((ROOT / 'portal/style.css').read_text())
    (output / 'result.json').write_text(json.dumps(data, indent=2) + '\n')
    (output / '.nojekyll').touch()
    check_publication(output)
    return data


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', type=Path, default=ROOT / 'results/latest.json')
    parser.add_argument('--output', type=Path, default=ROOT / '_site')
    args = parser.parse_args()
    result = build(args.input, args.output)
    print(f"Portal built: {result['status']}; only index.html, ja/index.html, style.css, result.json, .nojekyll")


if __name__ == '__main__':
    main()
