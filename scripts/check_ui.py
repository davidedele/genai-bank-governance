"""Exercise the actual UI against an isolated in-process HTTP backend.

Uses a temporary database and an offline fetch bridge; never touches an existing
workspace. This is not a deployment, browser-network or live-provider test.
"""
import argparse, json, sys, re, tempfile
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser()
parser.add_argument('--browser', help='Optional path to a Chromium executable')
parser.add_argument('--output-dir', type=Path, default=ROOT / '.runtime' / 'ui-check')
args = parser.parse_args()
sys.path.insert(0, str(ROOT))
from app import create_app
from fastapi.testclient import TestClient
from pathlib import Path
from playwright.sync_api import sync_playwright
root = args.output_dir
root.mkdir(parents=True, exist_ok=True)
report = {'checks': [], 'console_errors': [], 'page_errors': []}
tmp = tempfile.TemporaryDirectory()
client = TestClient(create_app(Path(tmp.name) / 'ui.sqlite'))
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, executable_path=args.browser, args=['--no-sandbox'])
    page = browser.new_page(viewport={'width': 1440, 'height': 1040}, device_scale_factor=1)
    page.on('pageerror', lambda e: report['page_errors'].append(str(e)))
    page.on('console', lambda m: report['console_errors'].append(m.text) if m.type == 'error' else None)

    def transport(source, request):
        response = client.request(request.get('method', 'GET'), request['path'], headers=request.get('headers', {}), content=request.get('body'))
        return {'body': response.text, 'status': response.status_code, 'headers': dict(response.headers)}
    page.expose_binding('__localTransport', transport)
    html = (ROOT / 'web/index.html').read_text()
    html = re.sub('<link rel="stylesheet"[^>]*>', '', html)
    html = re.sub('<script src="/static/app.js" defer></script>', '', html)
    page.set_content(html)
    page.add_style_tag(path=str(ROOT / 'web/style.css'))
    page.evaluate("() => { window.fetch=async (path, options={})=>{const r=await window.__localTransport({path:path,method:options.method||'GET',headers:options.headers||{},body:options.body});return new Response(r.body,{status:r.status,headers:r.headers});}; }")
    page.add_script_tag(path=str(ROOT / 'web/app.js'))
    page.locator('.sample').first.wait_for()
    assert page.locator('.sample').count() == 8
    page.screenshot(path=str(root / 'overview-desktop.png'), full_page=True)
    report['checks'].append('Overview renders eight separated synthetic examples.')
    page.locator('#mode-label').click()
    assert page.locator('dialog.modal').get_by_text('To turn it on').is_visible()
    page.screenshot(path=str(root / 'ai-dialog.png'))
    page.locator('.modal-close').click()
    report['checks'].append('The AI suggestions pill opens an explanation of why it is off and how to turn it on.')
    page.get_by_role('button', name='Register', exact=False).click()
    page.get_by_text('Nothing saved yet').wait_for()
    page.screenshot(path=str(root / 'register-empty.png'), full_page=True)
    page.get_by_role('button', name='Overview', exact=False).click()
    page.locator('.sample').first.click()
    page.locator('#decision-panel h2').first.wait_for()
    assert page.locator('#decision-panel h2').first.inner_text() == 'Standard controls'
    page.locator('#owner').fill('Operations (synthetic)')
    page.locator('#reviewer').fill('Demo reviewer')
    page.locator('#confirm-review').check()
    page.locator('#save-record').click()
    page.locator('#register table').wait_for()
    assert page.locator('#register tbody tr').count() == 1
    report['checks'].append('Manual review/save flow succeeds without a model or key.')
    page.get_by_role('button', name='Overview', exact=False).click()
    page.locator('.sample').nth(1).click()
    page.locator('#decision-panel h2').first.wait_for()
    assert page.locator('#decision-panel h2').first.inner_text() == 'Review required'
    page.locator('#decision-panel details').first.click()
    page.screenshot(path=str(root / 'assessment-desktop.png'), full_page=True)
    page.locator('#owner').fill('Operations (synthetic)')
    page.locator('#reviewer').fill('Demo reviewer')
    page.locator('#confirm-review').check()
    page.locator('#save-record').click()
    page.locator('#register table').wait_for()
    boot = client.get('/api/bootstrap').json()
    for i in [2, 3]:
        e = boot['examples'][i]
        result = client.post('/api/records', headers={'x-workspace-token': boot['token']}, json={'name': e['name'], 'owner': 'Example owner', 'reviewer': 'Demo reviewer', 'case': e['case'], 'confirm_review': True})
        assert result.is_success, result.text
    page.get_by_role('button', name='Register', exact=False).click()
    page.locator('#register tbody tr').nth(3).wait_for()
    page.screenshot(path=str(root / 'register-desktop.png'), full_page=True)
    page.locator('#register tbody button').filter(has_text='Summarizing a public report').click()
    page.get_by_role('button', name='Create a revised assessment').click()
    page.locator('#reviewer').fill('Second demo review')
    page.locator('#review-note').fill('Synthetic revision used to test history preservation.')
    page.locator('#confirm-review').check()
    page.locator('#save-record').click()
    page.locator('#register tbody button').filter(has_text='Summarizing a public report').wait_for()
    records = client.get('/api/records').json()
    r = next((r for r in records if r['name'] == 'Summarizing a public report'))
    assert r['revision'] == 2
    assert len(client.get('/api/records/' + r['id']).json()['history']) == 2
    report['checks'].append('Revision workflow creates a second immutable assessment.')
    assert len(client.get('/api/export/json').json()) == 5
    assert client.get('/api/export/csv').is_success
    report['checks'].append('CSV and JSON exports succeed and include all revisions.')
    page.get_by_role('button', name='Test results', exact=False).click()
    assert page.get_by_text('Live-model accuracy is not established.', exact=False).is_visible()
    page.screenshot(path=str(root / 'validation-desktop.png'), full_page=True)
    page.get_by_role('button', name='Framework', exact=False).click()
    assert page.locator('#framework details').count() == 9
    report['checks'].append('Framework and validation pages render with no fabricated model accuracy.')
    page.set_viewport_size({'width': 390, 'height': 844})
    page.get_by_role('button', name='Overview', exact=False).click()
    assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth'), page.evaluate('document.documentElement.scrollWidth')
    page.screenshot(path=str(root / 'overview-mobile.png'), full_page=True)
    page.locator('.sample').first.click()
    assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth')
    report['checks'].append('390px mobile layout has no horizontal overflow on overview and assessment.')
    browser.close()
(root / 'browser-results.json').write_text(json.dumps(report, indent=2))
print(json.dumps(report, indent=2))
assert not report['page_errors']
client.close()
tmp.cleanup()
