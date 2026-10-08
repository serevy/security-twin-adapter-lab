import copy
import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest
import zipfile

from build import ROOT, PUBLIC_FILES, build, check_publication, render
from locales import LOCALES
from evidence import BOOTSTRAP, REPOSITORY, SCENARIOS, from_artifact, read_json, validate


class PortalTests(unittest.TestCase):
    def setUp(self):
        self.snapshot = read_json((ROOT / 'results/latest.json').read_bytes())
        self.raw = {'schema_version': '1', 'contract_version': 'v1-draft', 'scenario': 'envoy-web-api',
                    'synthetic_only': True, 'status': 'PASS', 'checks': dict.fromkeys(SCENARIOS, 'PASS')}
        self.run = {'id': 1, 'repository': {'id': 2, 'full_name': REPOSITORY, 'private': False},
                    'head_repository': {'id': 2, 'private': False},
                    'path': '.github/workflows/envoy-conformance.yml', 'name': 'Envoy Conformance',
                    'status': 'completed', 'head_branch': 'main', 'head_sha': 'a' * 40,
                    'event': 'push', 'conclusion': 'success', 'updated_at': '2026-10-08T14:09:08Z'}

    def archive(self, raw=None, duplicate=False):
        stream = io.BytesIO()
        with zipfile.ZipFile(stream, 'w') as bundle:
            bundle.writestr('envoy-web-api.json', json.dumps(self.raw if raw is None else raw))
            bundle.writestr('envoy-compose.log', 'DO_NOT_PUBLISH_LOG')
            bundle.writestr('../../private.txt', 'DO_NOT_EXTRACT')
            if duplicate:
                import warnings
                with warnings.catch_warnings():
                    warnings.simplefilter('ignore')
                    bundle.writestr('envoy-web-api.json', '{}')
        data = stream.getvalue()
        artifact = {'id': 3, 'name': 'envoy-web-api-conformance', 'expired': False,
                    'size_in_bytes': len(data), 'digest': 'sha256:' + hashlib.sha256(data).hexdigest(),
                    'workflow_run': {'id': 1, 'head_sha': 'a' * 40, 'head_branch': 'main',
                                     'repository_id': 2, 'head_repository_id': 2}}
        return data, artifact

    def test_published_snapshot_provenance_and_all_required_sections(self):
        data = validate(self.snapshot)
        page = render(data)
        self.assertIn(data['status'], ('PASS', 'FAIL'))
        for marker in ('v1', 'Draft', 'Compatibility', 'Recovery', 'Rollback',
                       'PUBLIC_DISCLOSURE_BOUNDARY.md', str(data['source']['run_id']),
                       data['source']['head_sha'][:12], 'not a live status feed', 'No compatibility claim'):
            self.assertIn(marker.lower(), page.lower())
        for label in SCENARIOS.values():
            self.assertIn(label, page)

    def test_bootstrap_never_claims_success(self):
        page = render(BOOTSTRAP)
        self.assertIn('Bootstrap · awaiting evidence', page)
        self.assertNotIn('class="badge pass"', page)
        self.assertIn('0 <span class="muted">/ 14', page)
        self.assertEqual(validate(BOOTSTRAP)['source'], None)

    def test_fail_and_not_run_remain_visible(self):
        data = copy.deepcopy(self.snapshot)
        data['checks']['ttl_bound'] = 'FAIL'
        data['checks']['verified_clean_recovery'] = 'NOT_RUN'
        data['status'] = 'FAIL'
        page = render(data)
        self.assertIn('class="badge fail">FAIL', page)
        self.assertIn('class="badge not_run">NOT_RUN', page)
        data['status'] = 'PASS'
        with self.assertRaises(ValueError):
            validate(data)

    def test_unknown_fields_and_injection_are_rejected(self):
        candidates = []
        for key, value in (('trace', 'DO_NOT_PUBLISH'), ('status', '<script>alert(1)</script>'),
                           ('contract_version', '<img src=x>')):
            data = copy.deepcopy(self.snapshot)
            data[key] = value
            candidates.append(data)
        data = copy.deepcopy(self.snapshot)
        data['source']['url'] = 'https://example.invalid/private'
        candidates.append(data)
        data = copy.deepcopy(self.snapshot)
        data['checks']['extra'] = 'PASS'
        candidates.append(data)
        for data in candidates:
            with self.subTest(data=data), self.assertRaises(ValueError):
                validate(data)

    def test_duplicate_and_oversized_json_rejected(self):
        for raw in (b'{"status":"FAIL","status":"PASS"}', b' ' * 16385):
            with self.assertRaises(ValueError):
                read_json(raw)

    def test_artifact_import_projects_only_aggregate(self):
        archive, metadata = self.archive()
        result = from_artifact(archive, self.run, metadata)
        self.assertEqual(result['source']['evidence_kind'], 'workflow-artifact')
        self.assertEqual(result['checks'], self.raw['checks'])
        self.assertNotIn('DO_NOT_', json.dumps(result))

    def test_archive_digest_and_duplicates_rejected(self):
        archive, metadata = self.archive()
        metadata['digest'] = 'sha256:' + '0' * 64
        with self.assertRaises(ValueError):
            from_artifact(archive, self.run, metadata)
        archive, metadata = self.archive(duplicate=True)
        with self.assertRaises(ValueError):
            from_artifact(archive, self.run, metadata)

    def test_pr_fork_private_wrong_workflow_and_stale_artifact_rejected(self):
        archive, metadata = self.archive()
        for key, value in (('event', 'pull_request'), ('head_branch', 'feature'),
                           ('path', '.github/workflows/other.yml'), ('status', 'in_progress'),
                           ('conclusion', 'failure'), ('head_repository', {'id': 999, 'private': False}),
                           ('repository', {'id': 2, 'full_name': REPOSITORY, 'private': True})):
            run = copy.deepcopy(self.run)
            run[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                from_artifact(archive, run, metadata)
        for key, value in (('expired', True), ('name', 'other'), ('size_in_bytes', 262145)):
            item = copy.deepcopy(metadata)
            item[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                from_artifact(archive, self.run, item)
        metadata['workflow_run']['head_sha'] = 'b' * 40
        with self.assertRaises(ValueError):
            from_artifact(archive, self.run, metadata)

    def test_failure_artifact_and_execution_flags(self):
        self.raw.update(status='FAIL', harness='FAIL')
        self.run['conclusion'] = 'failure'
        archive, metadata = self.archive()
        result = from_artifact(archive, self.run, metadata)
        self.assertEqual(result['execution_failures'], ['harness'])
        self.assertIn('Execution failure: harness', render(result))
        self.raw['trace'] = 'FORBIDDEN'
        archive, metadata = self.archive()
        with self.assertRaises(ValueError):
            from_artifact(archive, self.run, metadata)

    def test_output_allowlist_and_nonempty_destination(self):
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder) / 'site'
            build(ROOT / 'results/latest.json', output)
            self.assertEqual({p.relative_to(output).as_posix() for p in output.rglob('*') if p.is_file()}, PUBLIC_FILES)
            self.assertEqual(json.loads((output / 'result.json').read_text()), validate(self.snapshot))
            (output / 'unexpected.log').write_text('DO_NOT_PUBLISH')
            with self.assertRaises(ValueError):
                build(ROOT / 'results/latest.json', output)

    def test_bilingual_shared_evidence_and_stable_identifiers(self):
        import re
        from urllib.parse import urljoin
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder) / 'site'
            build(ROOT / 'results/latest.json', output)
            self.assertEqual([p.relative_to(output).as_posix() for p in output.rglob('*.json')], ['result.json'])
            original = json.loads((output / 'result.json').read_text())
            self.assertEqual(original, validate(self.snapshot))
            for locale, page_path, url in (('en', 'index.html', 'https://example.test/lab/'),
                                           ('ja', 'ja/index.html', 'https://example.test/lab/ja/')):
                page = (output / page_path).read_text()
                self.assertIn(f'<html lang="{locale}">', page)
                href = re.search(r'data-evidence-link href="([^"]+)"', page)[1]
                self.assertEqual(urljoin(url, href), 'https://example.test/lab/result.json')
                self.assertEqual(re.findall(r'data-scenario="([^"]+)"', page), list(SCENARIOS))
                self.assertIn(original['source']['head_sha'][:12], page)
                self.assertIn(str(original['source']['evidence_id']), page)
                self.assertIn('>English</a>', page)
                self.assertIn('>日本語</a>', page)
            self.assertNotIn('ja/result.json', (output / 'ja/index.html').read_text())

    def test_both_locales_preserve_bootstrap_failure_and_not_run(self):
        for locale in LOCALES:
            page = render(BOOTSTRAP, locale)
            self.assertIn('class="badge bootstrap">BOOTSTRAP', page)
            self.assertNotIn('class="badge pass"', page)
            data = copy.deepcopy(self.snapshot)
            data['status'] = 'FAIL'
            data['checks']['ttl_bound'] = 'FAIL'
            data['checks']['verified_clean_recovery'] = 'NOT_RUN'
            page = render(data, locale)
            self.assertIn('class="badge fail">FAIL', page)
            self.assertIn('class="badge not_run">NOT_RUN', page)

    def test_translation_coverage_and_unknown_locale_fail_closed(self):
        import re
        for locale in LOCALES:
            self.assertEqual(set(LOCALES[locale]['scenarios']), set(SCENARIOS))
        en = re.findall(r'\$\{?([a-z_]+)', (ROOT / 'portal/index.html').read_text())
        ja = re.findall(r'\$\{?([a-z_]+)', (ROOT / 'portal/index.ja.html').read_text())
        self.assertEqual(set(en), set(ja))
        with self.assertRaises(ValueError):
            render(self.snapshot, 'unsupported')

    def test_publication_rejects_extra_nested_files(self):
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder) / 'site'
            build(ROOT / 'results/latest.json', output)
            (output / 'ja/result.json').write_text('{}')
            with self.assertRaises(ValueError):
                check_publication(output)


if __name__ == '__main__':
    unittest.main()
