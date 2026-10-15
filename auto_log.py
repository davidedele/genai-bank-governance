"""Read and manage locally captured prompt data written by the optional Claude Code plugin."""
import json
from pathlib import Path
import sqlite3
from schema import ValidationError, normalize_case

def default_event_db() -> Path:
    """Where the plugin keeps its file unless GENAI_EVENT_DB says otherwise."""
    return Path.home() / '.local' / 'share' / 'genai-governance' / 'events.sqlite'

def capture_in_use(path: Path) -> bool:
    """True when prompt capture is switched on, or the plugin has already saved prompts."""
    import os
    if os.environ.get('GENAI_CAPTURE_PROMPTS') == '1':
        return True
    path = Path(path)
    if not path.exists():
        return False
    try:
        with sqlite3.connect(path.as_uri() + '?mode=ro', uri=True, timeout=2) as c:
            return c.execute("SELECT COUNT(*) FROM sqlite_master WHERE name='prompts'").fetchone()[0] == 1
    except sqlite3.DatabaseError:
        return False

def read_metadata_events(path: Path) -> list[dict]:
    path = Path(path).resolve()
    if not path.exists():
        return []
    try:
        with sqlite3.connect(path.as_uri() + '?mode=ro', uri=True, timeout=2) as c:
            c.row_factory = sqlite3.Row
            return [dict(r) for r in c.execute('SELECT id,timestamp,event_type,prompt_chars FROM events ORDER BY timestamp DESC LIMIT 1000')]
    except sqlite3.DatabaseError:
        return []

def read_captured_prompts(path: Path) -> list[dict]:
    """Captured prompts, newest first. Model answers are validated here, never trusted as stored."""
    path = Path(path).resolve()
    if not path.exists():
        return []
    try:
        with sqlite3.connect(path.as_uri() + '?mode=ro', uri=True, timeout=2) as c:
            c.row_factory = sqlite3.Row
            rows = [dict(r) for r in c.execute('SELECT id,timestamp,text,status,classification,error FROM prompts ORDER BY timestamp DESC LIMIT 500')]
    except sqlite3.DatabaseError:
        return []
    for row in rows:
        row['case'] = None
        row['title'] = row['text'].strip().splitlines()[0][:80] if row['text'].strip() else 'Untitled prompt'
        raw = row.pop('classification')
        if row['status'] == 'classified' and raw:
            try:
                parsed = json.loads(raw)
                row['case'] = normalize_case({k: v for k, v in parsed.items() if k != 'title'})
                title = parsed.get('title')
                if isinstance(title, str) and title.strip():
                    row['title'] = title.strip()[:80]
            except (ValueError, ValidationError, AttributeError):
                row['status'], row['error'] = 'failed', 'The suggested answers were not valid.'
    return rows

def delete_captured_prompts(path: Path, prompt_id: str | None = None) -> int:
    """Delete one captured prompt, or all of them. Returns the number removed."""
    path = Path(path)
    if not path.exists():
        return 0
    with sqlite3.connect(path, timeout=5) as c:
        try:
            cur = c.execute('DELETE FROM prompts WHERE id=?', (prompt_id,)) if prompt_id else c.execute('DELETE FROM prompts')
        except sqlite3.OperationalError:
            return 0
        return cur.rowcount
