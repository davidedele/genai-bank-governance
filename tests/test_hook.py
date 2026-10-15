import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
ROOT = Path(__file__).resolve().parents[1]
HOOK = ROOT / 'claude-plugin/genai-usage-logger/hooks/capture_event.py'

def run_hook(db, enabled=True):
    env = {**os.environ, 'GENAI_LOG_METADATA': '1' if enabled else '0', 'GENAI_EVENT_DB': str(db)}
    event = {'hook_event_name': 'UserPromptSubmit', 'prompt': 'PRIVATE_PROMPT_SENTINEL', 'cwd': 'PRIVATE_PATH', 'session_id': 'PRIVATE_SESSION', 'transcript_path': 'PRIVATE_TRANSCRIPT'}
    return subprocess.run([sys.executable, str(HOOK)], input=json.dumps(event), text=True, capture_output=True, env=env)

def test_hook_disabled_by_default(tmp_path):
    db = tmp_path / 'events.sqlite'
    result = run_hook(db, False)
    assert result.returncode == 0 and (not db.exists())

def test_only_metadata_is_retained(tmp_path):
    db = tmp_path / 'events.sqlite'
    result = run_hook(db)
    assert result.returncode == 0 and (not result.stdout)
    assert b'PRIVATE' not in db.read_bytes()
    with sqlite3.connect(db) as c:
        columns = [r[1] for r in c.execute('PRAGMA table_info(events)')]
        assert columns == ['id', 'timestamp', 'event_type', 'prompt_chars']
        assert c.execute('SELECT prompt_chars FROM events').fetchone()[0] == len('PRIVATE_PROMPT_SENTINEL')

def test_metadata_writes_are_transactional(tmp_path):
    db = tmp_path / 'events.sqlite'
    with ThreadPoolExecutor(max_workers=5) as pool:
        results = list(pool.map(lambda _: run_hook(db), range(20)))
    assert all((r.returncode == 0 and (not r.stderr) for r in results))
    with sqlite3.connect(db) as c:
        assert c.execute('SELECT COUNT(*) FROM events').fetchone()[0] == 20

def test_hook_matches_documented_command_hook_contract():
    config = json.loads((HOOK.parent / 'hooks.json').read_text())
    command = config['hooks']['UserPromptSubmit'][0]['hooks'][0]
    assert command['type'] == 'command' and 'capture_event.py' in command['command']
