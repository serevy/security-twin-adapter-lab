"""Public HTTP conformance through real Envoy. Standard library only."""
import argparse
import json
import time
import urllib.error
import urllib.request
from pathlib import Path

RESULT = Path('results/envoy-web-api.json')
SCENARIOS = (
    'baseline_availability', 'scoped_containment', 'unrelated_session_survival',
    'ttl_bound', 'automatic_expiry', 'explicit_rollback', 'partial_failure_visibility',
    'verified_clean_recovery', 'provider_unavailable', 'rollback_failure',
    'recovery_verification_failure', 'technical_preflight', 'control_plane_unavailable',
    'restart_clean_recovery',
)


def fresh_result():
    return {'schema_version': '1', 'contract_version': 'v1-draft',
            'scenario': 'envoy-web-api', 'synthetic_only': True,
            'status': 'FAIL', 'checks': dict.fromkeys(SCENARIOS, 'NOT_RUN')}


def save(result):
    result['status'] = 'PASS' if all(v == 'PASS' for v in result['checks'].values()) else 'FAIL'
    RESULT.parent.mkdir(exist_ok=True)
    temporary = RESULT.with_suffix('.tmp')
    temporary.write_text(json.dumps(result, indent=2) + '\n')
    temporary.replace(RESULT)


def http(base, path, data=None, session=None):
    headers = {'Content-Type': 'application/json'}
    if session:
        headers['x-lab-session'] = session
    req = urllib.request.Request(base + path, headers=headers,
                                 data=None if data is None else json.dumps(data).encode())
    try:
        response = urllib.request.urlopen(req, timeout=3)
    except urllib.error.HTTPError as error:
        response = error
    with response:
        raw = response.read()
        try:
            body = json.loads(raw)
        except ValueError:
            body = None
        return response.code, body


def require(condition, label):
    if not condition:
        raise AssertionError(label)


class Suite:
    def __init__(self, adapter, envoy):
        self.adapter, self.envoy = adapter, envoy

    def control(self, path, data=None):
        return http(self.adapter, path, data)

    def traffic(self, session, path, expected):
        status, body = http(self.envoy, path, session=session)
        require(status == expected, f'traffic expected {expected}, got {status}')
        if expected == 200:
            service = 'normal-api' if path == '/public' else 'sensitive-api'
            require(body == {'service': service, 'synthetic': True}, 'wrong upstream response')

    def ready(self):
        deadline = time.monotonic() + 45
        while time.monotonic() < deadline:
            try:
                require(self.control('/health') == (200, {'ready': True}), 'adapter readiness')
                self.traffic('normal-session', '/public', 200)
                self.traffic('normal-session', '/sensitive/export', 200)
                return
            except (AssertionError, OSError):
                time.sleep(0.25)
        raise AssertionError('range readiness timeout')

    @staticmethod
    def request(name, **changes):
        req = {'request_id': name, 'target': 'synthetic-session',
               'scope': '/sensitive/export', 'action': 'restrict_route',
               'ttl_seconds': 60, 'rollback_required': True}
        req.update(changes)
        return req

    def fault(self, mode):
        require(self.control('/test/fault', {'mode': mode}) == (200, {'mode': mode}), 'fault injection')

    def restrict(self, req, partial=False):
        status, body = self.control('/restrict', req)
        require(status == (500 if partial else 200), 'apply HTTP status')
        require(body['outcome'] == ('PARTIAL_FAILURE' if partial else 'APPLIED'), 'apply outcome')
        require(body['mutated'] is True and body['applied'] == req, 'bounds preserved exactly')
        require(body['expiry'] == 'automatic', 'expiry behavior explicit')
        require(self.control('/state') == (200, {'restrictions': [req]}), 'provider state observable')

    def clean(self, name):
        require(self.control('/state') == (200, {'restrictions': []}), 'state not clean')
        require(self.control('/verify/' + name) ==
                (200, {'outcome': 'RECOVERED', 'verified_clean': True}), 'recovery not verified')
        self.traffic('synthetic-session', '/sensitive/export', 200)
        self.traffic('normal-session', '/public', 200)
        self.traffic('normal-session', '/sensitive/export', 200)

    def rollback(self, name):
        for _ in range(2):
            require(self.control('/rollback', {'request_id': name}) ==
                    (200, {'outcome': 'APPLIED', 'operation': 'rollback', 'recovery_verified': False}),
                    'explicit idempotent rollback')
        self.clean(name)

    def baseline_availability(self):
        self.ready()
        require(self.control('/state') == (200, {'restrictions': []}), 'initial state not clean')
        self.traffic('normal-session', '/public', 200)
        self.traffic('normal-session', '/sensitive/export', 200)
        self.traffic('synthetic-session', '/sensitive/export', 200)

    def scoped_containment(self):
        self.restrict(self.request('scoped'))
        self.traffic('synthetic-session', '/sensitive/export', 403)
        self.traffic('synthetic-session', '/public', 200)

    def unrelated_session_survival(self):
        self.traffic('normal-session', '/sensitive/export', 200)
        self.traffic('normal-session', '/public', 200)

    def explicit_rollback(self):
        self.rollback('scoped')

    def reject_unchanged(self, req, reason):
        before = self.control('/state')
        status, body = self.control('/restrict', req)
        require(status == 400 and body == {'outcome': 'REJECTED', 'reason': reason, 'mutated': False},
                'preflight rejection')
        require(self.control('/state') == before, 'rejection mutated provider')

    def ttl_bound(self):
        status, profile = self.control('/profile')
        require(status == 200 and profile['adapter_id'] == 'synthetic-envoy-v1', 'profile')
        require(profile['action_capabilities'] == ['restrict_route'] and
                profile['observation_capabilities'] == [] and profile['rollback_supported'], 'capabilities')
        maximum = profile['maximum_safe_ttl_seconds']
        self.reject_unchanged(self.request('over-ttl', ttl_seconds=maximum + 1), 'ttl_out_of_bounds')
        for value in (0, -1, True, 1.5, '60', None):
            self.reject_unchanged(self.request('invalid-ttl', ttl_seconds=value), 'ttl_out_of_bounds')
        self.restrict(self.request('max-ttl', ttl_seconds=maximum))
        self.rollback('max-ttl')

    def automatic_expiry(self):
        self.restrict(self.request('expiry', ttl_seconds=2))
        self.traffic('synthetic-session', '/sensitive/export', 403)
        deadline = time.monotonic() + 8
        while time.monotonic() < deadline:
            if self.control('/state') == (200, {'restrictions': []}):
                self.clean('expiry')
                self.rollback('expiry')
                return
            time.sleep(0.1)
        raise AssertionError('automatic expiry timeout')

    def partial_failure_visibility(self):
        self.fault('partial_after_mutation')
        self.restrict(self.request('partial'), partial=True)
        self.traffic('synthetic-session', '/sensitive/export', 403)
        self.traffic('synthetic-session', '/public', 200)
        self.traffic('normal-session', '/sensitive/export', 200)
        require(self.control('/verify/partial') ==
                (409, {'verified_clean': False, 'reason': 'restriction_present'}), 'partial must not be recovered')

    def verified_clean_recovery(self):
        self.fault('none')
        self.rollback('partial')

    def provider_unavailable(self):
        self.fault('provider_unavailable')
        require(self.control('/restrict', self.request('provider-down')) ==
                (503, {'outcome': 'REJECTED', 'reason': 'provider_unavailable', 'mutated': False}),
                'provider failure reported as success')
        require(self.control('/state') ==
                (503, {'restrictions': None, 'reason': 'provider_unavailable'}), 'unknown state lost')
        self.traffic('normal-session', '/sensitive/export', 503)
        self.fault('none')
        require(self.control('/state') == (200, {'restrictions': []}), 'provider rejection mutated state')
        self.traffic('normal-session', '/sensitive/export', 200)

    def rollback_failure(self):
        self.restrict(self.request('rollback-fault'))
        self.fault('rollback_failure')
        require(self.control('/rollback', {'request_id': 'rollback-fault'}) ==
                (503, {'outcome': 'PARTIAL_FAILURE', 'reason': 'rollback_unavailable', 'recovery_verified': False}),
                'rollback failure visibility')
        self.traffic('synthetic-session', '/sensitive/export', 403)
        require(self.control('/verify/rollback-fault')[0] == 409, 'rollback failure became clean')
        self.fault('none')
        self.rollback('rollback-fault')

    def recovery_verification_failure(self):
        self.restrict(self.request('verify-fault'))
        self.fault('verification_failure')
        require(self.control('/rollback', {'request_id': 'verify-fault'})[0] == 200, 'rollback acknowledgement')
        require(self.control('/verify/verify-fault') ==
                (503, {'verified_clean': None, 'reason': 'verification_unavailable'}), 'unknown is not clean')
        self.fault('none')
        self.clean('verify-fault')

    def technical_preflight(self):
        for changes, reason in (
            ({'action': 'unsupported'}, 'unsupported_capability'),
            ({'target': '*'}, 'invalid_target'),
            ({'scope': '*'}, 'unsupported_scope'),
            ({'rollback_required': False}, 'rollback_incompatible'),
            ({'extra': 'not-a-contract-field'}, 'invalid_request'),
        ):
            self.reject_unchanged(self.request('unsupported', **changes), reason)
        require(self.control('/verify/unknown')[1]['verified_clean'] is None, 'unknown operation inferred clean')

    def control_plane_unavailable(self):
        # The host harness has stopped the adapter container, not just set a flag.
        try:
            self.control('/restrict', self.request('offline'))
        except (urllib.error.URLError, TimeoutError, ConnectionError):
            pass
        else:
            raise AssertionError('control plane unexpectedly reachable')
        self.traffic('synthetic-session', '/sensitive/export', 503)
        self.traffic('normal-session', '/public', 503)

    def restart_clean_recovery(self):
        self.ready()
        require(self.control('/state') == (200, {'restrictions': []}), 'restart state not clean')
        self.traffic('synthetic-session', '/sensitive/export', 200)
        # In-memory operation history is lost on restart; do not invent recovery evidence.
        require(self.control('/verify/scoped')[1]['verified_clean'] is None, 'restart inferred known operation')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('phase', choices=['main', 'outage', 'restart'])
    parser.add_argument('--adapter', default='http://adapter:8080')
    parser.add_argument('--envoy', default='http://envoy:8080')
    args = parser.parse_args()
    result = fresh_result() if args.phase == 'main' else json.loads(RESULT.read_text())
    suite = Suite(args.adapter, args.envoy)
    phases = {
        'main': ['baseline_availability', 'scoped_containment', 'unrelated_session_survival',
                 'explicit_rollback', 'ttl_bound', 'automatic_expiry', 'partial_failure_visibility',
                 'verified_clean_recovery', 'provider_unavailable', 'rollback_failure',
                 'recovery_verification_failure', 'technical_preflight'],
        'outage': ['control_plane_unavailable'], 'restart': ['restart_clean_recovery'],
    }
    save(result)
    for name in phases[args.phase]:
        try:
            getattr(suite, name)()
        except Exception as error:
            result['checks'][name] = 'FAIL'
            save(result)
            # Fixed scenario plus exception class only: no bodies, URLs or traces.
            print(f'FAIL {name} ({type(error).__name__})', flush=True)
            return 1
        result['checks'][name] = 'PASS'
        save(result)
        print(f'PASS {name}', flush=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
