"""Builds the static demo site: the real web files plus the Python app, which runs in the browser.

Usage: python scripts/build_pages.py OUTPUT_DIR [--pyodide-dir DIR | --pyodide-url URL]
The result needs no server code. Python runs in the visitor's browser through Pyodide.
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PYODIDE = 'https://cdn.jsdelivr.net/pyodide/v0.29.3/full/'
# The files the app needs at run time. Anything else (tests, plugin, docs) stays out of the site.
PYTHON_FILES = ['app.py', 'auto_log.py', 'classifier.py', 'mapper.py', 'providers.py', 'schema.py', 'storage.py', 'demo_examples.py',
                'data/framework.py', 'data/policy.json', 'eval/__init__.py', 'eval/cases.py', 'eval/benchmark.json']
# The hosting service sets no security headers, so the page carries its own policy. Everything must come from the
# same site. 'wasm-unsafe-eval' lets the browser run the Python runtime and nothing else.
PAGE_POLICY = "default-src 'self'; script-src 'self' 'wasm-unsafe-eval'; style-src 'self'; img-src 'self' data:; connect-src 'self'; worker-src 'self'; base-uri 'none'; form-action 'none'"
# What link previews (LinkedIn, Slack, search results) show when the demo address is shared.
SITE_URL = 'https://davidedele.github.io/genai-bank-governance/'
SITE_DESCRIPTION = 'Describe what an employee did with an AI tool and see which risks and controls apply. Runs in your browser, with no account.'
BANNER_OLD = '<strong>Public demo.</strong> Use made-up information only. Saved cases are visible to every visitor and are cleared regularly.'
BANNER_NEW = '<strong>Public demo.</strong> It runs entirely in your browser, so nothing you enter is sent anywhere. Saved cases are lost when you close or reload the page.'


START_UP_DATA = """
import asyncio, json, sys
sys.path.insert(0, sys.argv[1])
import bridge
reply = json.loads(asyncio.run(bridge.request('GET', '/api/bootstrap', '', '')))
assert reply['status'] == 200, reply
data = json.loads(reply['body'])
data.pop('token')
print(json.dumps(data))
"""


def start_up_data() -> str:
    """What the app sends when the page opens, produced by the real app, without its one-time token.

    The page shows this at once while Python is still downloading, so the overview does not wait.
    """
    with tempfile.TemporaryDirectory() as scratch:
        env = dict(os.environ, DEMO_APP_ROOT=str(ROOT), GOVERNANCE_DB_PATH=str(Path(scratch) / 'register.sqlite'))
        done = subprocess.run([sys.executable, '-c', START_UP_DATA, str(ROOT / 'static_demo')], env=env, capture_output=True, text=True, check=True)
    return done.stdout.strip()


def build(out: Path, pyodide_url: str = PYODIDE, pyodide_dir: Path = None, site_url: str = SITE_URL) -> None:
    if out.exists():
        shutil.rmtree(out)
    (out / 'py').mkdir(parents=True)
    shutil.copytree(ROOT / 'web', out / 'static')
    shutil.copy(ROOT / 'static_demo' / 'runtime.js', out / 'static' / 'runtime.js')
    for name in PYTHON_FILES:
        target = out / 'py' / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(ROOT / name, target)
    shutil.copy(ROOT / 'static_demo' / 'bridge.py', out / 'py' / 'bridge.py')
    (out / 'py' / 'manifest.json').write_text(json.dumps({'files': PYTHON_FILES}))
    (out / 'py' / 'bootstrap.json').write_text(start_up_data())
    if pyodide_dir is not None:  # serve the runtime from the same site instead of a public CDN
        shutil.copytree(pyodide_dir, out / 'pyodide')
        pyodide_url = 'pyodide/'
    page = (ROOT / 'web' / 'index.html').read_text()
    for old, new in [('href="/static/', 'href="static/'), ('src="/static/', 'src="static/')]:
        assert old in page, old
        page = page.replace(old, new)
    assert BANNER_OLD in page
    page = page.replace(BANNER_OLD, BANNER_NEW)
    config = json.dumps({'pyodideUrl': pyodide_url, 'pyBase': 'py/'})
    (out / 'static' / 'demo-config.js').write_text(f'window.DEMO_CONFIG={config};\n')
    page = page.replace('<main id="main"', '<div id="demo-loading" class="demo-loading" role="status">Loading the demo.</div><main id="main"', 1)
    page = page.replace('<script src="static/app.js" defer></script>', '<script src="static/demo-config.js"></script><script src="static/runtime.js"></script><script src="static/app.js" defer></script>', 1)
    assert 'runtime.js' in page and 'demo-loading' in page
    shutil.copy(ROOT / 'static_demo' / 'social-preview.png', out / 'social-preview.png')
    preview = (f'<meta name="description" content="{SITE_DESCRIPTION}">'
               '<meta property="og:type" content="website"><meta property="og:title" content="GenAI Governance">'
               f'<meta property="og:description" content="{SITE_DESCRIPTION}"><meta property="og:url" content="{site_url}">'
               f'<meta property="og:image" content="{site_url}social-preview.png">'
               '<meta property="og:image:width" content="1200"><meta property="og:image:height" content="630">'
               '<meta property="og:image:alt" content="The overview page: Govern the use, not just the tool.">'
               '<meta name="twitter:card" content="summary_large_image">')
    page = page.replace('</head>', preview + '</head>', 1)
    page = page.replace('</head>', f'<meta http-equiv="Content-Security-Policy" content="{PAGE_POLICY}"><link rel="icon" href="data:,"></head>', 1)
    (out / 'index.html').write_text(page)
    (out / '.nojekyll').write_text('')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('output', type=Path)
    parser.add_argument('--pyodide-url', default=PYODIDE, help='Folder that holds pyodide.js, ending in a slash')
    parser.add_argument('--pyodide-dir', type=Path, help='Folder made by fetch_pyodide.py. It is copied into the site and used instead of the CDN')
    args = parser.parse_args()
    build(args.output, args.pyodide_url, args.pyodide_dir)
    print(f'Built {args.output}')
