"""Read metadata events only. Legacy raw-prompt logs are not imported automatically."""
from pathlib import Path
import sqlite3

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
