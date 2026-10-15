"""Local research workspace. Start with: python app.py"""
import json
import os
import secrets
import time
from pathlib import Path
from threading import Lock
from urllib.parse import urlparse
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from data.framework import DIMENSIONS, FORMS_OF_USE, RISK_AREAS
from schema import APP_VERSION, UNKNOWN, APPROVAL_OPTIONS, ValidationError, normalize_case
from mapper import assess_use_case, load_policy
from storage import Store, ConflictError, export_csv
from classifier import classify_with_metadata, ClassificationError
from providers import current_model, current_provider_id, ProviderError
from demo_examples import examples
from auto_log import read_metadata_events
ROOT = Path(__file__).resolve().parent

class AssessRequest(BaseModel):
    case: dict

class ClassifyRequest(BaseModel):
    description: str = Field(min_length=1, max_length=1500)
    confirm_external_processing: bool = False

class SaveRequest(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    owner: str = Field(min_length=1, max_length=120)
    reviewer: str = Field(min_length=1, max_length=120)
    case: dict
    classification_id: str | None = None
    description: str = Field(default='', max_length=1500)
    retain_description: bool = False
    parent_id: str | None = None
    review_note: str = Field(default='', max_length=1000)
    confirm_review: bool = False

def create_app(db_path: Path | None=None):
    application = FastAPI(title='GenAI Governance Workspace', version=APP_VERSION, docs_url=None, redoc_url=None)
    store = Store(db_path or Path(os.environ.get('GOVERNANCE_DB_PATH', ROOT / '.runtime' / 'register.sqlite')))
    token = secrets.token_urlsafe(32)
    # Pending extraction provenance stays server-side and is never accepted from a client.
    pending = {}
    pending_lock = Lock()

    def prune_pending():
        now = time.monotonic()
        for key in list(pending):
            if now - pending[key]['created'] > 1200:
                del pending[key]
    application.state.store = store
    application.state.token = token
    application.mount('/static', StaticFiles(directory=ROOT / 'web'), name='static')

    @application.middleware('http')
    async def boundary(request: Request, call_next):
        host = request.headers.get('host', '')
        hostname = urlparse('http://' + host).hostname
        if hostname not in {'localhost', '127.0.0.1', '::1', 'testserver'}:
            return JSONResponse({'detail': 'This workspace accepts local hosts only.'}, status_code=403)
        origin = request.headers.get('origin')
        if origin and origin != f'{request.url.scheme}://{host}':
            return JSONResponse({'detail': 'Cross-origin requests are not accepted.'}, status_code=403)
        if request.method in {'POST', 'PUT', 'PATCH', 'DELETE'}:
            supplied = request.headers.get('x-workspace-token', '')
            if not secrets.compare_digest(supplied, token):
                return JSONResponse({'detail': 'Reload the workspace before submitting.'}, status_code=403)
            try:
                length = int(request.headers.get('content-length', '0'))
            except ValueError:
                return JSONResponse({'detail': 'Invalid content length.'}, status_code=400)
            if length < 0:
                return JSONResponse({'detail': 'Invalid content length.'}, status_code=400)
            if length > 64000:
                return JSONResponse({'detail': 'Request exceeds the local input limit.'}, status_code=413)
        response = await call_next(request)
        response.headers['Content-Security-Policy'] = "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'"
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['Referrer-Policy'] = 'no-referrer'
        response.headers['Cache-Control'] = 'no-store'
        return response

    @application.exception_handler(ValidationError)
    async def invalid_case(request, error):
        return JSONResponse({'detail': str(error)}, status_code=422)

    @application.get('/', response_class=HTMLResponse)
    def home():
        return (ROOT / 'web/index.html').read_text()

    @application.get('/api/bootstrap')
    def bootstrap():
        live = os.environ.get('ENABLE_LIVE_CLASSIFICATION', '0') == '1'
        provider = model = None
        try:
            provider = current_provider_id()
            model = current_model(provider)
        except ProviderError:
            pass
        return {'token': token, 'version': APP_VERSION, 'unknown': UNKNOWN, 'dimensions': DIMENSIONS, 'approval_options': APPROVAL_OPTIONS, 'forms': FORMS_OF_USE, 'risks': RISK_AREAS, 'examples': [{**e, 'assessment': assess_use_case(e['case'])} for e in examples()], 'policy_version': load_policy()['version'], 'live_enabled': live, 'provider': provider, 'model': model}

    @application.post('/api/assess')
    def assess(body: AssessRequest):
        return {'case': normalize_case(body.case), 'assessment': assess_use_case(body.case)}

    @application.post('/api/classify')
    def classify(body: ClassifyRequest):
        if not body.confirm_external_processing:
            raise HTTPException(400, 'Explicit confirmation of external processing is required.')
        if os.environ.get('ENABLE_LIVE_CLASSIFICATION', '0') != '1':
            raise HTTPException(403, 'Live classification is disabled in local configuration.')
        try:
            store.reserve_api_attempt()
            case, meta = classify_with_metadata(body.description)
        except (ClassificationError, ValueError) as e:
            raise HTTPException(400, str(e)) from None
        with pending_lock:
            prune_pending()
            if len(pending) >= 100:
                pending.pop(next(iter(pending)))
            key = secrets.token_urlsafe(20)
            pending[key] = {'case': case, 'metadata': meta, 'description': body.description, 'created': time.monotonic()}
        return {'classification_id': key, 'case': case, 'metadata': meta, 'assessment': assess_use_case(case)}

    @application.post('/api/records')
    def save(body: SaveRequest):
        if not body.confirm_review:
            raise HTTPException(400, 'Confirm that you reviewed the recorded characteristics.')
        original = None
        provenance = {'source': 'manual'}
        if body.classification_id:
            with pending_lock:
                prune_pending()
                original = pending.get(body.classification_id)
            if not original:
                raise HTTPException(409, 'Classification expired. Classify again or save as a manual entry.')
            if body.description != original['description']:
                raise HTTPException(409, 'The description changed after classification. Classify again before saving.')
            provenance = {'source': 'model extraction, human reviewed', **original['metadata']}
        try:
            record = store.save(name=body.name, owner=body.owner, reviewer=body.reviewer, case=body.case, prediction=original['case'] if original else None, provenance=provenance, description=body.description, retain_description=body.retain_description, parent_id=body.parent_id, review_note=body.review_note)
        except ConflictError as e:
            raise HTTPException(409, str(e)) from None
        except ValueError as e:
            raise HTTPException(422, str(e)) from None
        return record

    @application.get('/api/events')
    def metadata_events():
        filename = os.environ.get('GENAI_EVENT_DB', '')
        enabled = os.environ.get('GENAI_LOG_METADATA') == '1' and bool(filename)
        return {'enabled': enabled, 'events': read_metadata_events(Path(filename)) if enabled else [], 'note': 'Prompt-event metadata only; these events are not classified use cases or proof of review.'}

    @application.get('/api/records')
    def records():
        return store.list(latest_only=True)

    @application.get('/api/records/{record_id}')
    def detail(record_id: str):
        record = store.get(record_id)
        if record is None:
            raise HTTPException(404, 'Record not found.')
        return {'record': record, 'history': [r for r in store.list() if r['case_id'] == record['case_id']]}

    @application.get('/api/export/{format}')
    def export(format: str):
        records = store.list()
        if format == 'csv':
            return Response(export_csv(records), media_type='text/csv', headers={'Content-Disposition': 'attachment; filename=governance-register.csv'})
        if format == 'json':
            return Response(json.dumps(records, indent=2, ensure_ascii=False), media_type='application/json', headers={'Content-Disposition': 'attachment; filename=governance-register.json'})
        raise HTTPException(404, 'Export format not found.')
    return application
if __name__ == '__main__':
    from dotenv import load_dotenv
    import uvicorn
    load_dotenv(ROOT / '.env', override=False)
    uvicorn.run(create_app(), host='127.0.0.1', port=8501, access_log=False)
