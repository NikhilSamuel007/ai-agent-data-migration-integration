"""Static frontend host. All migration operations go to the separate API."""
import json
import os
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

PUBLIC = Path(__file__).resolve().parent / 'dist'

class FrontendHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(PUBLIC), **kwargs)

    def do_GET(self):
        if urlsplit(self.path).path == '/config.js':
            config = {'apiBaseUrl': os.environ.get('API_BASE_URL', 'http://localhost:8000').rstrip('/')}
            body = ('window.RELAY_CONFIG = ' + json.dumps(config) + ';\n').encode()
            self.send_response(200)
            self.send_header('Content-Type', 'text/javascript; charset=utf-8')
            self.send_header('Cache-Control', 'no-store')
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        elif urlsplit(self.path).path.startswith(('/api/', '/mock/')):
            self.send_error(404, 'API endpoints belong to the backend service')
        else:
            super().do_GET()

    def list_directory(self, path):
        self.send_error(404, 'Not found')
        return None

if __name__ == '__main__':
    if not (PUBLIC / 'index.html').is_file():
        raise SystemExit('Build the React frontend first: cd frontend && npm install && npm run build')
    host = os.environ.get('HOST', '127.0.0.1')
    port = int(os.environ.get('FRONTEND_PORT', 3000))
    print(f'Relay frontend is running at http://localhost:{port}', flush=True)
    with ThreadingHTTPServer((host, port), FrontendHandler) as server:
        server.serve_forever()
