import ast
import importlib.util
import json
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]

def load_builder():
    spec = importlib.util.spec_from_file_location('build_pages', ROOT / 'scripts' / 'build_pages.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def test_site_has_everything_it_needs(tmp_path):
    builder = load_builder()
    builder.build(tmp_path / 'site', '/pyodide/')
    site = tmp_path / 'site'
    page = (site / 'index.html').read_text()
    assert 'href="/static/' not in page and 'src="/static/' not in page
    assert 'static/runtime.js' in page and 'static/app.js' in page and '"pyodideUrl": "/pyodide/"' in page
    assert 'nothing you enter is sent anywhere' in page
    assert (site / '.nojekyll').exists() and (site / 'static' / 'style.css').exists()
    manifest = json.loads((site / 'py' / 'manifest.json').read_text())
    for name in manifest['files']:
        assert (site / 'py' / name).exists(), name
    assert (site / 'py' / 'bridge.py').exists()

def test_every_local_module_the_app_imports_is_shipped():
    """The in-browser copy only has the listed files, so an import of another local module would break it."""
    builder = load_builder()
    shipped = {Path(n).stem for n in builder.PYTHON_FILES if n.endswith('.py')}
    local = {p.stem for p in ROOT.glob('*.py')} | {'data', 'eval'}
    seen = set()
    pending = ['app.py']
    while pending:
        name = pending.pop()
        tree = ast.parse((ROOT / name).read_text())
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module and node.col_offset == 0:
                top = node.module.split('.')[0]
            elif isinstance(node, ast.Import) and node.col_offset == 0:
                top = node.names[0].name.split('.')[0]
            else:
                continue
            if top in local and top not in seen and top not in ('data', 'eval'):
                seen.add(top)
                assert top in shipped, f'{name} imports {top}, which is not in the demo build'
                pending.append(top + '.py')

def test_bridge_has_no_server_only_dependencies():
    text = (ROOT / 'static_demo' / 'bridge.py').read_text()
    assert "GOVERNANCE_DEMO'] = '1'" in text and 'run_in_threadpool' in text
