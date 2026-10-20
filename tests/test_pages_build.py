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
    assert 'static/runtime.js' in page and 'static/app.js' in page
    assert '"pyodideUrl": "/pyodide/"' in (site / 'static' / 'demo-config.js').read_text()
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


def load_fetcher():
    spec = importlib.util.spec_from_file_location('fetch_pyodide', ROOT / 'scripts' / 'fetch_pyodide.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def make_release(folder, packages):
    """A small stand-in for an unpacked Pyodide release."""
    folder.mkdir(parents=True)
    for name in ['pyodide.js', 'pyodide.asm.js', 'pyodide.asm.wasm', 'python_stdlib.zip']:
        (folder / name).write_text(name)
    entries = {}
    for name, depends in packages.items():
        entries[name] = {'file_name': f'{name}.whl', 'depends': depends}
        (folder / f'{name}.whl').write_text(name)
    (folder / 'other.whl').write_text('not needed')
    (folder / 'pyodide-lock.json').write_text(json.dumps({'info': {}, 'packages': {**entries, 'other': {'file_name': 'other.whl', 'depends': []}}}))

def test_runtime_loads_the_packages_the_fetch_script_keeps():
    fetcher = load_fetcher()
    runtime = (ROOT / 'static_demo' / 'runtime.js').read_text()
    assert 'const PACKAGES = ' + json.dumps(fetcher.PACKAGES).replace('"', "'").replace("', '", "', '") in runtime

def test_fetch_keeps_only_the_needed_packages_and_their_dependencies(tmp_path):
    fetcher = load_fetcher()
    make_release(tmp_path / 'release', {'fastapi': ['starlette'], 'starlette': ['anyio'], 'anyio': [], 'pydantic': [], 'sqlite3': []})
    kept = fetcher.trim(tmp_path / 'release', tmp_path / 'out')
    assert kept == ['anyio', 'fastapi', 'pydantic', 'sqlite3', 'starlette']
    assert not (tmp_path / 'out' / 'other.whl').exists()
    lock = json.loads((tmp_path / 'out' / 'pyodide-lock.json').read_text())
    assert 'other' not in lock['packages'] and 'starlette' in lock['packages']
    for name in fetcher.CORE_FILES:
        assert (tmp_path / 'out' / name).exists(), name

def test_fetch_refuses_a_download_with_the_wrong_checksum(tmp_path):
    fetcher = load_fetcher()
    bad = tmp_path / 'bad.tar.bz2'
    bad.write_bytes(b'not the real release')
    try:
        fetcher.fetch(tmp_path / 'out', bad)
    except SystemExit as stop:
        assert 'checksum' in str(stop)
    else:
        raise AssertionError('a wrong checksum was accepted')
    assert not (tmp_path / 'out').exists()

def test_site_can_serve_its_own_runtime(tmp_path):
    builder = load_builder()
    runtime = tmp_path / 'runtime'
    make_release(runtime, {'fastapi': [], 'pydantic': [], 'sqlite3': []})
    builder.build(tmp_path / 'site', pyodide_dir=runtime)
    page = (tmp_path / 'site' / 'index.html').read_text()
    assert '"pyodideUrl": "pyodide/"' in (tmp_path / 'site' / 'static' / 'demo-config.js').read_text() and 'jsdelivr' not in page
    assert (tmp_path / 'site' / 'pyodide' / 'pyodide.js').exists()

def test_start_up_data_is_shipped_without_the_one_time_token(tmp_path):
    builder = load_builder()
    builder.build(tmp_path / 'site', '/pyodide/')
    data = json.loads((tmp_path / 'site' / 'py' / 'bootstrap.json').read_text())
    assert 'token' not in data and data['demo'] is True
    schema = importlib.util.spec_from_file_location('schema_for_test', ROOT / 'schema.py')
    module = importlib.util.module_from_spec(schema)
    schema.loader.exec_module(module)
    assert data['version'] == module.APP_VERSION
    assert data['examples'] and data['lookalikes'] and data['live_enabled'] is False


def test_unpacking_refuses_paths_and_links_that_leave_the_folder(tmp_path):
    import io
    import tarfile
    fetcher = load_fetcher()
    def archive(name, link=None):
        path = tmp_path / (str(abs(hash(name))) + '.tar.bz2')
        with tarfile.open(path, 'w:bz2') as tar:
            info = tarfile.TarInfo(name)
            if link:
                info.type, info.linkname = tarfile.SYMTYPE, link
                tar.addfile(info)
            else:
                info.size = 1
                tar.addfile(info, io.BytesIO(b'x'))
        return path
    for name, link in [('../outside', None), ('/absolute', None), ('shortcut', '/etc/passwd')]:
        try:
            fetcher.unpack(archive(name, link), tmp_path / 'target')
        except SystemExit:
            continue
        raise AssertionError(f'{name} was unpacked')
    assert not (tmp_path / 'outside').exists()
    fetcher.unpack(archive('inside/file.txt'), tmp_path / 'target')
    assert (tmp_path / 'target' / 'inside' / 'file.txt').read_text() == 'x'

def test_demo_page_carries_a_policy_that_allows_only_its_own_site(tmp_path):
    builder = load_builder()
    runtime = tmp_path / 'runtime'
    make_release(runtime, {'fastapi': [], 'pydantic': [], 'sqlite3': []})
    builder.build(tmp_path / 'site', pyodide_dir=runtime)
    page = (tmp_path / 'site' / 'index.html').read_text()
    assert 'http-equiv="Content-Security-Policy"' in page
    assert "connect-src 'self'" in page and "script-src 'self' 'wasm-unsafe-eval'" in page
    assert "'unsafe-inline'" not in page and "'unsafe-eval'" not in page
    import re
    for tag in re.findall(r'<script\b[^>]*>', page):
        assert 'src=' in tag, 'inline scripts are not allowed by the policy'
    assert (tmp_path / 'site' / 'static' / 'demo-config.js').read_text().startswith('window.DEMO_CONFIG=')
    assert 'style=' not in page


def test_demo_page_has_a_link_preview_that_points_at_its_own_image(tmp_path):
    builder = load_builder()
    runtime = tmp_path / 'runtime'
    make_release(runtime, {'fastapi': [], 'pydantic': [], 'sqlite3': []})
    builder.build(tmp_path / 'site', pyodide_dir=runtime, site_url='https://example.test/demo/')
    page = (tmp_path / 'site' / 'index.html').read_text()
    assert '<meta property="og:image" content="https://example.test/demo/social-preview.png">' in page
    assert '<meta property="og:title" content="GenAI Governance">' in page
    assert 'name="twitter:card" content="summary_large_image"' in page
    header = (tmp_path / 'site' / 'social-preview.png').read_bytes()[:24]
    assert header[:8] == b'\x89PNG\r\n\x1a\n'
    assert (int.from_bytes(header[16:20], 'big'), int.from_bytes(header[20:24], 'big')) == (1200, 630)
