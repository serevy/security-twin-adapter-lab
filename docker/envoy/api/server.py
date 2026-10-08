"""Two fixed synthetic APIs; no user data or external calls."""
import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit

SERVICE = os.environ['SERVICE']
ROUTE = '/public' if SERVICE == 'normal-api' else '/sensitive/export'


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_GET(self):
        path = urlsplit(self.path).path
        code = 200 if path in (ROUTE, '/health') else 404
        body = json.dumps({'service': SERVICE, 'synthetic': True}).encode()
        self.send_response(code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)


if __name__ == '__main__':
    ThreadingHTTPServer(('0.0.0.0', 8080), Handler).serve_forever()
