import copy
import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest
import zipfile

from build import ROOT, build, render
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
        self.assertIn('class="badge not_run">NOT RUN', page)
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
            self.assertEqual({p.name for p in output.iterdir()}, {'index.html', 'style.css', 'result.json', '.nojekyll'})
            self.assertEqual(json.loads((output / 'result.json').read_text()), validate(self.snapshot))
            (output / 'unexpected.log').write_text('DO_NOT_PUBLISH')
            with self.assertRaises(ValueError):
                build(ROOT / 'results/latest.json', output)


if __name__ == '__main__':
    unittest.main()
