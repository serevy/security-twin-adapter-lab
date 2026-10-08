"""Exercise actual stdlib HTTP serialization and malformed-control handling."""
import json
import threading
import unittest
import urllib.error
import urllib.request

from test_adapter import module


class HTTPTests(unittest.TestCase):
    def setUp(self):
        module.ADAPTER = module.Adapter()
        self.server = module.ThreadingHTTPServer(('127.0.0.1', 0), module.Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base = f'http://127.0.0.1:{self.server.server_port}'

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()

    def call(self, path, data=None):
        request = urllib.request.Request(self.base + path, data=data)
        try:
            response = urllib.request.urlopen(request, timeout=2)
        except urllib.error.HTTPError as error:
            response = error
        with response:
            return response.status, json.load(response)

    def test_malformed_json_and_wrong_shapes_are_rejected_without_mutation(self):
        for data in (b'not-json', b'[]', b'null', b'{}', b'"text"', b'\xff', b' ' * 4097):
            status, body = self.call('/restrict', data)
            self.assertEqual(status, 400)
            self.assertEqual(body['outcome'], 'REJECTED')
        for endpoint in ('/rollback', '/test/fault'):
            self.assertEqual(self.call(endpoint, b'{"request_id": []}')[0], 400)
        self.assertEqual(self.call('/state'), (200, {'restrictions': []}))

    def test_mutation_partial_rollback_and_separate_verification_over_http(self):
        request = {'request_id': 'http', 'target': 'synthetic-session', 'scope': '/sensitive/export',
                   'action': 'restrict_route', 'ttl_seconds': 60, 'rollback_required': True}
        self.assertEqual(self.call('/test/fault', b'{"mode":"partial_after_mutation"}')[0], 200)
        self.assertEqual(self.call('/restrict', json.dumps(request).encode())[1]['outcome'], 'PARTIAL_FAILURE')
        self.assertEqual(self.call('/state')[1]['restrictions'], [request])
        self.assertEqual(self.call('/verify/http')[0], 409)
        self.assertFalse(self.call('/rollback', b'{"request_id":"http"}')[1]['recovery_verified'])
        self.assertEqual(self.call('/verify/http')[1]['outcome'], 'RECOVERED')
