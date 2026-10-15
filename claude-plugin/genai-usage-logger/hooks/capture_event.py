"""Opt-in prompt capture for the governance workspace.

Two independent switches, both off by default:
  GENAI_LOG_METADATA=1    keep time, event type, random id and prompt length only.
  GENAI_CAPTURE_PROMPTS=1 also keep the prompt text locally, so it can be reviewed in
                          the workspace. Claude Code then suggests answers in the
                          background unless GENAI_AUTO_CLASSIFY=0.
The file is ~/.local/share/genai-governance/events.sqlite unless GENAI_EVENT_DB names
another absolute path. Nothing here can block a prompt.
"""
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import time
import uuid
MAX_INPUT_BYTES = 64000
MAX_EVENTS = 1000
MAX_PROMPT_CHARS = 8000
RETENTION_SECONDS = 7 * 24 * 60 * 60
CHILD_ENV = 'GENAI_GOVERNANCE_CHILD'

def default_db_path() -> Path:
    return Path.home() / '.local' / 'share' / 'genai-governance' / 'events.sqlite'

EVENTS_SQL = 'CREATE TABLE IF NOT EXISTS events(id TEXT PRIMARY KEY, timestamp REAL NOT NULL,event_type TEXT NOT NULL,prompt_chars INTEGER NOT NULL)'
PROMPTS_SQL = 'CREATE TABLE IF NOT EXISTS prompts(id TEXT PRIMARY KEY, timestamp REAL NOT NULL, text TEXT NOT NULL, status TEXT NOT NULL, classification TEXT, error TEXT, updated REAL NOT NULL)'
COUNTERS_SQL = 'CREATE TABLE IF NOT EXISTS counters(name TEXT PRIMARY KEY, value INTEGER NOT NULL)'

def with_write_lock(path: Path, work, attempts: int = 6):
    """Take the write lock up front and retry briefly if another process holds it."""
    conn = sqlite3.connect(path, timeout=5, isolation_level=None)
    try:
        for attempt in range(attempts):
            try:
                conn.execute('BEGIN IMMEDIATE')
                result = work(conn)
                conn.execute('COMMIT')
                return result
            except sqlite3.OperationalError:
                try:
                    conn.execute('ROLLBACK')
                except sqlite3.Error:
                    pass
                if attempt == attempts - 1:
                    raise
                time.sleep(0.05 * (attempt + 1))
    finally:
        conn.close()

def write_event(path: Path, now: float, prompt_chars: int, attempts: int = 6):
    def work(conn):
        conn.execute(EVENTS_SQL)
        conn.execute('INSERT INTO events VALUES(?,?,?,?)', (str(uuid.uuid4()), now, 'UserPromptSubmit', prompt_chars))
        conn.execute('DELETE FROM events WHERE timestamp<?', (now - RETENTION_SECONDS,))
        conn.execute('DELETE FROM events WHERE id NOT IN (SELECT id FROM events ORDER BY timestamp DESC LIMIT ?)', (MAX_EVENTS,))
    with_write_lock(path, work, attempts)

def write_prompt(path: Path, now: float, text: str, attempts: int = 6) -> str:
    prompt_id = str(uuid.uuid4())
    def work(conn):
        conn.execute(PROMPTS_SQL)
        conn.execute('INSERT INTO prompts VALUES(?,?,?,?,?,?,?)', (prompt_id, now, text[:MAX_PROMPT_CHARS], 'pending', None, None, now))
        conn.execute('DELETE FROM prompts WHERE timestamp<?', (now - RETENTION_SECONDS,))
        conn.execute('DELETE FROM prompts WHERE id NOT IN (SELECT id FROM prompts ORDER BY timestamp DESC LIMIT ?)', (MAX_EVENTS,))
    with_write_lock(path, work, attempts)
    return prompt_id

def prepare(path: Path):
    path = Path(path)
    if not path.is_absolute() or path.is_symlink():
        raise ValueError('Event database must be an absolute, non-symlink path.')
    path.parent.mkdir(parents=True, exist_ok=True, mode=448)
    if not path.exists():
        try:
            fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 384)
            os.close(fd)
        except FileExistsError:
            pass
    return path

def start_classifier(path: Path):
    """Run the classifier in the background so the prompt is never delayed."""
    script = Path(__file__).with_name('classify_pending.py')
    subprocess.Popen([sys.executable, str(script), str(path)], stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True, env={**os.environ, CHILD_ENV: '1'})

def capture(event: dict, path: Path, *, metadata: bool = True, keep_text: bool = False, classify: bool = False):
    if not isinstance(event, dict) or event.get('hook_event_name') != 'UserPromptSubmit':
        return
    prompt = event.get('prompt')
    if not isinstance(prompt, str):
        return
    path = prepare(path)
    now = time.time()
    # Without the text switch, prompt content, hashes and session paths are never kept.
    if metadata:
        write_event(path, now, len(prompt))
    if keep_text and prompt.strip():
        write_prompt(path, now, prompt)
        if classify:
            start_classifier(path)
    os.chmod(path, 384)

def main():
    if os.environ.get(CHILD_ENV) == '1':
        return  # A classification run started by this plugin must never be captured again.
    filename = os.environ.get('GENAI_EVENT_DB') or str(default_db_path())
    metadata = os.environ.get('GENAI_LOG_METADATA') == '1'
    keep_text = os.environ.get('GENAI_CAPTURE_PROMPTS') == '1'
    if not (metadata or keep_text):
        return
    try:
        raw = sys.stdin.buffer.read(MAX_INPUT_BYTES + 1)
        if len(raw) > MAX_INPUT_BYTES:
            return
        capture(json.loads(raw), Path(filename), metadata=metadata, keep_text=keep_text, classify=os.environ.get('GENAI_AUTO_CLASSIFY') != '0')
    except Exception:
        print('Prompt event not recorded.', file=sys.stderr)
if __name__ == '__main__':
    main()
