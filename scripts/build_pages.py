"""Builds the static demo site: the real web files plus the Python app, which runs in the browser.

Usage: python scripts/build_pages.py OUTPUT_DIR [--pyodide-url URL]
The result needs no server code. Python runs in the visitor's browser through Pyodide.
"""
import argparse
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PYODIDE = 'https://cdn.jsdelivr.net/pyodide/v0.29.3/full/'
# The files the app needs at run time. Anything else (tests, plugin, docs) stays out of the site.
PYTHON_FILES = ['app.py', 'auto_log.py', 'classifier.py', 'mapper.py', 'providers.py', 'schema.py', 'storage.py', 'demo_examples.py',
                'data/framework.py', 'data/policy.json', 'eval/__init__.py', 'eval/cases.py', 'eval/benchmark.json']
BANNER_OLD = '<strong>Public demo.</strong> Use made-up information only. Saved cases are visible to every visitor and are cleared regularly.'
BANNER_NEW = '<strong>Public demo.</strong> It runs entirely in your browser, so nothing you enter is sent anywhere. Saved cases are lost when you close or reload the page.'


def build(out: Path, pyodide_url: str = PYODIDE) -> None:
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
    page = (ROOT / 'web' / 'index.html').read_text()
    for old, new in [('href="/static/', 'href="static/'), ('src="/static/', 'src="static/')]:
        assert old in page, old
        page = page.replace(old, new)
    assert BANNER_OLD in page
    page = page.replace(BANNER_OLD, BANNER_NEW)
    config = json.dumps({'pyodideUrl': pyodide_url, 'pyBase': 'py/'})
    page = page.replace('<main id="main"', '<div id="demo-loading" class="demo-loading">Loading the demo.</div><main id="main"', 1)
    page = page.replace('<script src="static/app.js" defer></script>', f'<script>window.DEMO_CONFIG={config};</script><script src="static/runtime.js"></script><script src="static/app.js" defer></script>', 1)
    assert 'runtime.js' in page and 'demo-loading' in page
    page = page.replace('</head>', '<link rel="icon" href="data:,"></head>', 1)
    (out / 'index.html').write_text(page)
    (out / '.nojekyll').write_text('')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('output', type=Path)
    parser.add_argument('--pyodide-url', default=PYODIDE, help='Folder that holds pyodide.js, ending in a slash')
    args = parser.parse_args()
    build(args.output, args.pyodide_url)
    print(f'Built {args.output}')
