"""Synthetic bounded actuator only. No detection or policy authority."""
import json
import re
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit


class Adapter:
    MAX_TTL = 60
    FIELDS = {'request_id', 'target', 'scope', 'action', 'ttl_seconds', 'rollback_required'}
    MODES = {'none', 'partial_after_mutation', 'provider_unavailable',
             'rollback_failure', 'verification_failure'}

    def __init__(self, clock=time.monotonic, rollback_supported=True):
        self.clock = clock
        self.rollback_supported = rollback_supported
        self.operations = {}
        self.mode = 'none'
        self.lock = threading.RLock()

    def profile(self):
        return {'adapter_id': 'synthetic-envoy-v1', 'contract_version': 'v1-draft',
                'observation_capabilities': [], 'action_capabilities': ['restrict_route'],
                'rollback_supported': self.rollback_supported,
                'maximum_safe_ttl_seconds': self.MAX_TTL, 'expiry': 'automatic'}

    def active(self):
        return [op for op in self.operations.values()
                if not op['rolled_back'] and self.clock() < op['deadline']]

    @staticmethod
    def rejected(reason):
        return 400, {'outcome': 'REJECTED', 'reason': reason, 'mutated': False}

    def apply(self, req):
        with self.lock:
            if not isinstance(req, dict) or set(req) != self.FIELDS:
                return self.rejected('invalid_request')
            if not isinstance(req['request_id'], str) or not re.fullmatch(r'[a-z0-9-]{1,64}', req['request_id']):
                return self.rejected('invalid_request_id')
            if req['action'] != 'restrict_route':
                return self.rejected('unsupported_capability')
            if req['target'] not in ('normal-session', 'synthetic-session'):
                return self.rejected('invalid_target')
            if req['scope'] != '/sensitive/export':
                return self.rejected('unsupported_scope')
            ttl = req['ttl_seconds']
            if type(ttl) is not int or not 0 < ttl <= self.MAX_TTL:
                return self.rejected('ttl_out_of_bounds')
            if req['rollback_required'] is not True or not self.rollback_supported:
                return self.rejected('rollback_incompatible')
            if req['request_id'] in self.operations:
                return self.rejected('duplicate_request')
            if any(op['request']['target'] == req['target'] for op in self.active()):
                return self.rejected('restriction_already_active')
            if self.mode == 'provider_unavailable':
                return 503, {'outcome': 'REJECTED', 'reason': 'provider_unavailable', 'mutated': False}
            # All technical preflight checks precede provider mutation.
            self.operations[req['request_id']] = {
                'request': dict(req), 'deadline': self.clock() + ttl, 'rolled_back': False}
            partial = self.mode == 'partial_after_mutation'
            return (500 if partial else 200), {
                'outcome': 'PARTIAL_FAILURE' if partial else 'APPLIED',
                'reason': 'injected_after_mutation' if partial else 'bounded_restriction',
                'mutated': True, 'applied': dict(req), 'expiry': 'automatic'}

    def rollback(self, request_id):
        with self.lock:
            if request_id not in self.operations:
                return self.rejected('unknown_operation')
            if self.mode in ('provider_unavailable', 'rollback_failure'):
                return 503, {'outcome': 'PARTIAL_FAILURE', 'reason': 'rollback_unavailable',
                             'recovery_verified': False}
            self.operations[request_id]['rolled_back'] = True
            # This acknowledges the rollback operation, not verified recovery.
            return 200, {'outcome': 'APPLIED', 'operation': 'rollback', 'recovery_verified': False}

    def verify(self, request_id):
        with self.lock:
            if request_id not in self.operations:
                return 404, {'verified_clean': None, 'reason': 'unknown_operation'}
            if self.mode in ('provider_unavailable', 'verification_failure'):
                return 503, {'verified_clean': None, 'reason': 'verification_unavailable'}
            if self.active():
                return 409, {'verified_clean': False, 'reason': 'restriction_present'}
            return 200, {'outcome': 'RECOVERED', 'verified_clean': True}

    def state(self):
        with self.lock:
            if self.mode == 'provider_unavailable':
                return 503, {'restrictions': None, 'reason': 'provider_unavailable'}
            return 200, {'restrictions': [dict(op['request']) for op in self.active()]}

    def authorize(self, session, path):
        with self.lock:
            if self.mode == 'provider_unavailable':
                return 503
            if session not in ('normal-session', 'synthetic-session'):
                return 403
            return 403 if any(op['request']['target'] == session and
                              op['request']['scope'] == urlsplit(path).path
                              for op in self.active()) else 200


ADAPTER = Adapter()


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass  # No request traces in public evidence.

    def respond(self, status, body):
        payload = json.dumps(body).encode()
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def do_GET(self):
        if self.server.server_port == 8081:
            status = ADAPTER.authorize(self.headers.get('x-lab-session'), self.path)
            return self.respond(status, {'allowed': status == 200})
        path = urlsplit(self.path).path
        if path == '/health':
            return self.respond(200, {'ready': True})
        if path == '/profile':
            return self.respond(200, ADAPTER.profile())
        if path == '/state':
            return self.respond(*ADAPTER.state())
        if path.startswith('/verify/'):
            return self.respond(*ADAPTER.verify(path.removeprefix('/verify/')))
        self.respond(404, {'reason': 'unknown_endpoint'})

    def do_POST(self):
        if self.server.server_port == 8081:
            return self.respond(405, {'reason': 'method_not_supported'})
        try:
            size = int(self.headers.get('Content-Length', '0'))
            if not 0 < size <= 4096:
                raise ValueError()
            req = json.loads(self.rfile.read(size))
        except (ValueError, UnicodeError):
            return self.respond(*ADAPTER.rejected('invalid_json'))
        if self.path == '/restrict':
            return self.respond(*ADAPTER.apply(req))
        if self.path == '/rollback' and isinstance(req, dict) and set(req) == {'request_id'} and isinstance(req['request_id'], str):
            return self.respond(*ADAPTER.rollback(req['request_id']))
        if self.path == '/test/fault' and isinstance(req, dict) and set(req) == {'mode'} and isinstance(req['mode'], str) and req['mode'] in Adapter.MODES:
            with ADAPTER.lock:
                ADAPTER.mode = req['mode']
            return self.respond(200, {'mode': req['mode']})
        self.respond(*ADAPTER.rejected('invalid_control_request'))


if __name__ == '__main__':
    authz = ThreadingHTTPServer(('0.0.0.0', 8081), Handler)
    threading.Thread(target=authz.serve_forever, daemon=True).start()
    ThreadingHTTPServer(('0.0.0.0', 8080), Handler).serve_forever()
