"""Runs the real FastAPI app inside the browser (Pyodide) and answers /api requests from the page."""
import json
import os
import sys

os.environ['GOVERNANCE_DEMO'] = '1'
os.environ.setdefault('GOVERNANCE_DB_PATH', '/tmp/register.sqlite')  # nosec B108: the browser's in-memory file system, not a real /tmp
ROOT = os.environ.get('DEMO_APP_ROOT', '/home/pyodide/app')  # the build sets this to read the start-up data
os.makedirs(ROOT + '/web', exist_ok=True)  # the app mounts this folder; the browser serves the real files
sys.path.insert(0, ROOT)

# Pyodide has no threads: run the app's plain functions inline instead of in a thread pool.
import starlette.concurrency
import fastapi.routing

async def _inline(func, *args, **kwargs):
    return func(*args, **kwargs)

starlette.concurrency.run_in_threadpool = _inline
fastapi.routing.run_in_threadpool = _inline

from app import create_app
_app = create_app()

async def request(method, path, body, token):
    """Returns (status, content-type, text) for one request to the app."""
    path, _, query = path.partition('?')
    data = body.encode() if body else b''
    headers = [(b'host', b'localhost'), (b'x-workspace-token', (token or '').encode())]
    if data:
        headers += [(b'content-type', b'application/json'), (b'content-length', str(len(data)).encode())]
    scope = {'type': 'http', 'asgi': {'version': '3.0'}, 'http_version': '1.1', 'method': method, 'scheme': 'http',
             'path': path, 'raw_path': path.encode(), 'query_string': query.encode(), 'root_path': '',
             'headers': headers, 'client': ('127.0.0.1', 0), 'server': ('localhost', 80)}
    sent = {'body': b''}
    state = {'done': False}

    async def receive():
        if not state['done']:
            state['done'] = True
            return {'type': 'http.request', 'body': data, 'more_body': False}
        return {'type': 'http.disconnect'}

    async def send(message):
        if message['type'] == 'http.response.start':
            sent['status'] = message['status']
            sent['headers'] = {k.decode().lower(): v.decode() for k, v in message['headers']}
        elif message['type'] == 'http.response.body':
            sent['body'] += message.get('body', b'')

    await _app(scope, receive, send)
    return json.dumps({'status': sent['status'], 'type': sent['headers'].get('content-type', ''),
                       'disposition': sent['headers'].get('content-disposition', ''), 'body': sent['body'].decode('utf-8', 'replace')})
