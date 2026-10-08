import importlib.util
from pathlib import Path
import unittest
from concurrent.futures import ThreadPoolExecutor

spec = importlib.util.spec_from_file_location('adapter', Path(__file__).resolve().parents[1] / 'docker/envoy/adapter/server.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
Adapter = module.Adapter


class AdapterTests(unittest.TestCase):
    def setUp(self):
        self.now = 100.0
        self.adapter = Adapter(clock=lambda: self.now)

    def request(self, **changes):
        req = {'request_id': 'unit', 'target': 'synthetic-session', 'scope': '/sensitive/export',
               'action': 'restrict_route', 'ttl_seconds': 10, 'rollback_required': True}
        req.update(changes)
        return req

    def test_scoped_bounds_and_exact_expiry(self):
        req = self.request()
        code, result = self.adapter.apply(req)
        self.assertEqual((code, result['outcome'], result['applied']), (200, 'APPLIED', req))
        for session, route, expected in (
            ('synthetic-session', '/sensitive/export', 403),
            ('synthetic-session', '/sensitive/export?format=json', 403),
            ('synthetic-session', '/public', 200),
            ('normal-session', '/sensitive/export', 200),
        ):
            self.assertEqual(self.adapter.authorize(session, route), expected)
        self.now = 109.999
        self.assertEqual(self.adapter.authorize('synthetic-session', '/sensitive/export'), 403)
        self.now = 110.0
        self.assertEqual(self.adapter.authorize('synthetic-session', '/sensitive/export'), 200)
        self.assertEqual(self.adapter.state(), (200, {'restrictions': []}))

    def test_all_invalid_preflights_have_no_mutation(self):
        changes = [{'ttl_seconds': x} for x in (61, 0, -1, True, 1.5, None, '10', [], {})]
        changes += [{'target': '*'}, {'target': []}, {'scope': '*'}, {'scope': {}},
                    {'action': 'other'}, {'action': []}, {'rollback_required': False},
                    {'rollback_required': 1}, {'request_id': ''}, {'request_id': []}, {'extra': 1}]
        for change in changes:
            with self.subTest(change=change):
                self.assertEqual(self.adapter.apply(self.request(**change))[1]['outcome'], 'REJECTED')
                self.assertEqual(self.adapter.operations, {})
        for req in (None, [], 2, 'request', {}):
            self.assertEqual(self.adapter.apply(req)[1]['outcome'], 'REJECTED')
        adapter = Adapter(rollback_supported=False)
        self.assertEqual(adapter.apply(self.request())[1]['reason'], 'rollback_incompatible')
        self.assertEqual(adapter.operations, {})

    def test_maximum_ttl_and_input_copies(self):
        req = self.request(ttl_seconds=60)
        _, result = self.adapter.apply(req)
        req['scope'] = '*'
        result['applied']['scope'] = '*'
        self.assertEqual(self.adapter.state()[1]['restrictions'][0]['scope'], '/sensitive/export')
        self.assertEqual(self.adapter.operations['unit']['deadline'], 160)

    def test_duplicate_and_overlapping_requests_cannot_extend_ttl(self):
        self.adapter.apply(self.request())
        self.now += 5
        for req in (self.request(ttl_seconds=60), self.request(request_id='overlap', ttl_seconds=60)):
            self.assertEqual(self.adapter.apply(req)[1]['outcome'], 'REJECTED')
        self.assertEqual(self.adapter.operations['unit']['deadline'], 110)

    def test_concurrent_duplicate_only_mutates_once(self):
        with ThreadPoolExecutor(max_workers=8) as pool:
            results = list(pool.map(lambda _: self.adapter.apply(self.request()), range(20)))
        self.assertEqual(sum(result[0] == 200 for result in results), 1)
        self.assertEqual(len(self.adapter.operations), 1)

    def test_partial_failure_stays_mutated_until_explicit_rollback(self):
        self.adapter.mode = 'partial_after_mutation'
        self.assertEqual(self.adapter.apply(self.request())[1]['outcome'], 'PARTIAL_FAILURE')
        self.assertEqual(self.adapter.authorize('synthetic-session', '/sensitive/export'), 403)
        self.assertFalse(self.adapter.verify('unit')[1]['verified_clean'])
        self.adapter.mode = 'none'
        for _ in range(2):
            result = self.adapter.rollback('unit')[1]
            self.assertEqual(result['outcome'], 'APPLIED')
            self.assertFalse(result['recovery_verified'])
        self.assertEqual(self.adapter.verify('unit')[1]['outcome'], 'RECOVERED')

    def test_provider_unavailable_never_claims_mutation_or_clean(self):
        self.adapter.mode = 'provider_unavailable'
        self.assertEqual(self.adapter.apply(self.request()),
                         (503, {'outcome': 'REJECTED', 'reason': 'provider_unavailable', 'mutated': False}))
        self.assertEqual(self.adapter.operations, {})
        self.assertIsNone(self.adapter.state()[1]['restrictions'])
        self.assertEqual(self.adapter.authorize('normal-session', '/public'), 503)

    def test_rollback_and_verification_failures_are_separate(self):
        self.adapter.apply(self.request())
        self.adapter.mode = 'rollback_failure'
        self.assertEqual(self.adapter.rollback('unit')[1]['outcome'], 'PARTIAL_FAILURE')
        self.assertEqual(self.adapter.authorize('synthetic-session', '/sensitive/export'), 403)
        self.adapter.mode = 'verification_failure'
        self.assertEqual(self.adapter.rollback('unit')[1]['outcome'], 'APPLIED')
        self.assertIsNone(self.adapter.verify('unit')[1]['verified_clean'])
        self.adapter.mode = 'none'
        self.assertEqual(self.adapter.verify('unit')[1]['outcome'], 'RECOVERED')

    def test_unknown_is_not_clean_and_other_active_target_prevents_recovery(self):
        self.assertIsNone(self.adapter.verify('unknown')[1]['verified_clean'])
        self.assertEqual(self.adapter.rollback('unknown')[1]['outcome'], 'REJECTED')
        self.adapter.apply(self.request())
        self.adapter.apply(self.request(request_id='second', target='normal-session'))
        self.adapter.rollback('unit')
        self.assertFalse(self.adapter.verify('unit')[1]['verified_clean'])
        self.assertEqual(self.adapter.authorize('normal-session', '/sensitive/export'), 403)
        self.adapter.rollback('second')
        self.assertTrue(self.adapter.verify('unit')[1]['verified_clean'])


if __name__ == '__main__':
    unittest.main()
