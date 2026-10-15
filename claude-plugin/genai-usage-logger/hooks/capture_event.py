"""Opt-in prompt-event metadata. No content retention and no model calls."""
import json
import os
from pathlib import Path
import sqlite3
import sys
import time
import uuid
MAX_INPUT_BYTES = 64000
MAX_EVENTS = 1000
RETENTION_SECONDS = 7 * 24 * 60 * 60

def write_event(path: Path, now: float, prompt_chars: int, attempts: int = 6):
    """Take the write lock up front and retry briefly if another hook holds it."""
    conn = sqlite3.connect(path, timeout=5, isolation_level=None)
    try:
        for attempt in range(attempts):
            try:
                conn.execute('BEGIN IMMEDIATE')
                conn.execute('CREATE TABLE IF NOT EXISTS events(id TEXT PRIMARY KEY, timestamp REAL NOT NULL,event_type TEXT NOT NULL,prompt_chars INTEGER NOT NULL)')
                conn.execute('INSERT INTO events VALUES(?,?,?,?)', (str(uuid.uuid4()), now, 'UserPromptSubmit', prompt_chars))
                conn.execute('DELETE FROM events WHERE timestamp<?', (now - RETENTION_SECONDS,))
                conn.execute('DELETE FROM events WHERE id NOT IN (SELECT id FROM events ORDER BY timestamp DESC LIMIT ?)', (MAX_EVENTS,))
                conn.execute('COMMIT')
                return
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

def capture(event: dict, path: Path):
    if not isinstance(event, dict) or event.get('hook_event_name') != 'UserPromptSubmit':
        return
    prompt = event.get('prompt')
    if not isinstance(prompt, str):
        return
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
    # Deliberately exclude prompt content, content hashes and identifiable session paths.
    now = time.time()
    write_event(path, now, len(prompt))
    os.chmod(path, 384)

def main():
    if os.environ.get('GENAI_LOG_METADATA') != '1':
        return
    filename = os.environ.get('GENAI_EVENT_DB', '')
    if not filename:
        return
    try:
        raw = sys.stdin.buffer.read(MAX_INPUT_BYTES + 1)
        if len(raw) > MAX_INPUT_BYTES:
            return
        capture(json.loads(raw), Path(filename))
    except Exception:
        print('Metadata event not recorded.', file=sys.stderr)
if __name__ == '__main__':
    main()
