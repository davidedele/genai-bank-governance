"""Local SQLite records, immutable revisions and optimistic conflict detection."""
import csv
import io
import json
import os
import sqlite3
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4
from mapper import assess_use_case
from schema import normalize_case, APP_VERSION

class ConflictError(ValueError):
    pass

def utc_now():
    return datetime.now(timezone.utc).isoformat(timespec='seconds')

def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'))

class Store:

    def __init__(self, path: Path):
        self.path = Path(path).resolve()
        self.path.parent.mkdir(parents=True, exist_ok=True, mode=448)
        if not self.path.exists():
            try:
                fd = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 384)
                os.close(fd)
            except FileExistsError:
                pass
        with self.connect() as c:
            c.executescript('\n            CREATE TABLE IF NOT EXISTS assessments(\n              id TEXT PRIMARY KEY, case_id TEXT NOT NULL, revision INTEGER NOT NULL,\n              parent_id TEXT REFERENCES assessments(id), created_at TEXT NOT NULL,\n              payload TEXT NOT NULL, UNIQUE(case_id,revision));\n            CREATE TABLE IF NOT EXISTS counters(name TEXT PRIMARY KEY,value INTEGER NOT NULL);\n            ')
        try:
            os.chmod(self.path, 384)
        except OSError:
            pass

    def connect(self):
        c = sqlite3.connect(self.path, timeout=5)
        c.row_factory = sqlite3.Row
        c.execute('PRAGMA foreign_keys=ON')
        return c

    def save(self, *, name: str, owner: str, reviewer: str, case: dict, prediction: dict | None=None, provenance: dict | None=None, description: str='', retain_description: bool=False, parent_id: str | None=None, review_note: str='', policy: dict | None=None) -> dict:
        parent_id = parent_id or None  # an empty string must not reach the foreign key
        for label, text, limit in [('Name', name, 160), ('Owner', owner, 120), ('Reviewer', reviewer, 120)]:
            if not isinstance(text, str) or not text.strip() or len(text) > limit:
                raise ValueError(f'{label} is required and must be at most {limit} characters.')
        if len(description) > 1500 or len(review_note) > 1000:
            raise ValueError('Description or review note is too long.')
        case = normalize_case(case)
        original = normalize_case(prediction) if prediction is not None else None
        fields = ['forms', 'tool_access', 'information_involved', 'role_of_output', 'banking_process', 'task_expertise', 'approval_status']
        # Keep the model's original values; corrections do not rewrite their source.
        corrections = {f: {'predicted': deepcopy(original[f]), 'reviewed': deepcopy(case[f])} for f in fields if original is not None and original[f] != case[f]}
        for field in corrections:
            case['evidence'].pop(field, None)
        if corrections:
            case['rationale'] = ''
        field_sources = {f: 'reviewer correction' if f in corrections else 'model extraction, reviewer confirmed' if original is not None else 'manual entry' for f in fields}
        # Excerpts and rationales can contain the original description too.
        if not retain_description:
            for value in (case, original):
                if value is not None:
                    value['evidence'] = {}
                    value['rationale'] = ''
        decision = assess_use_case(case, policy)
        with self.connect() as c:
            c.execute('BEGIN IMMEDIATE')
            if parent_id:
                row = c.execute('SELECT * FROM assessments WHERE id=?', (parent_id,)).fetchone()
                if row is None:
                    raise ValueError('Original assessment was not found.')
                latest = c.execute('SELECT MAX(revision) FROM assessments WHERE case_id=?', (row['case_id'],)).fetchone()[0]
                if row['revision'] != latest:
                    raise ConflictError('A newer revision exists. Reload before saving.')
                case_id, revision = (row['case_id'], latest + 1)
            else:
                case_id, revision = (str(uuid4()), 1)
            record = {'id': str(uuid4()), 'case_id': case_id, 'revision': revision, 'parent_id': parent_id, 'created_at': utc_now(), 'name': name.strip(), 'owner': owner.strip(), 'reviewer': reviewer.strip(), 'review_note': review_note.strip(), 'record_state': 'Recorded by reviewer; not use approval', 'case': case, 'original_prediction': original, 'corrections': corrections, 'field_sources': field_sources, 'provenance': deepcopy(provenance or {'source': 'manual'}), 'description': description if retain_description else None, 'description_retained': retain_description, 'assessment': decision, 'app_version': APP_VERSION}
            c.execute('INSERT INTO assessments VALUES(?,?,?,?,?,?)', (record['id'], case_id, revision, parent_id, record['created_at'], canonical(record)))
        return record

    def list(self, *, latest_only: bool=False) -> list[dict]:
        with self.connect() as c:
            if latest_only:
                rows = c.execute('SELECT a.payload FROM assessments a JOIN (SELECT case_id,MAX(revision) AS r FROM assessments GROUP BY case_id) b ON a.case_id=b.case_id AND a.revision=b.r ORDER BY a.created_at DESC,a.id')
            else:
                rows = c.execute('SELECT payload FROM assessments ORDER BY created_at DESC,revision DESC,id')
            return [json.loads(r[0]) for r in rows]

    def get(self, id: str) -> dict | None:
        with self.connect() as c:
            row = c.execute('SELECT payload FROM assessments WHERE id=?', (id,)).fetchone()
            return json.loads(row[0]) if row else None

    def reserve_api_attempt(self, limit: int=30) -> int:
        """Count one model extraction for today (UTC). A limit of 0 turns the cap off."""
        name = 'classify:' + utc_now()[:10]
        with self.connect() as c:
            c.execute('BEGIN IMMEDIATE')
            c.execute('INSERT OR IGNORE INTO counters VALUES(?,0)', (name,))
            n = c.execute('SELECT value FROM counters WHERE name=?', (name,)).fetchone()[0]
            if limit > 0 and n >= limit:
                raise ValueError(f'Daily limit of {limit} model extractions reached. Try again tomorrow (UTC), or raise DAILY_CLASSIFICATION_LIMIT in .env.')
            c.execute('UPDATE counters SET value=value+1 WHERE name=?', (name,))
            return limit - n - 1 if limit > 0 else -1

def daily_limit_from_env(environ=None) -> int:
    """DAILY_CLASSIFICATION_LIMIT: a whole number, 0 for no cap. Anything else falls back to 30."""
    raw = (environ if environ is not None else os.environ).get('DAILY_CLASSIFICATION_LIMIT', '').strip()
    if not raw:
        return 30
    try:
        value = int(raw)
    except ValueError:
        return 30
    return value if value >= 0 else 30

def safe_csv_cell(value) -> str:
    text = str(value if value is not None else '')
    if text.lstrip().startswith(('=', '+', '-', '@')) or text.startswith(('\t', '\r', '\n')):
        return "'" + text
    return text

def export_csv(records: list[dict]) -> str:
    output = io.StringIO(newline='')
    fields = ['id', 'case_id', 'revision', 'created_at', 'name', 'owner', 'reviewer', 'outcome', 'unresolved', 'risk_ids', 'policy_version', 'policy_sha256']
    writer = csv.writer(output)
    writer.writerow(fields)
    for r in records:
        a = r['assessment']
        row = {**r, **a, 'risk_ids': '; '.join(a['risk_ids']), 'unresolved': '; '.join(a['unresolved'])}
        writer.writerow([safe_csv_cell(row.get(f, '')) for f in fields])
    return output.getvalue()
