"""Read-only lookup of saved reviews. Prints titles, outcomes and answers, never owners or notes."""
import json
import os
from pathlib import Path
import sqlite3
import sys

def find(path: Path, words: list[str], limit: int = 20) -> list[dict]:
    if not path.is_absolute() or not path.exists():
        return []
    with sqlite3.connect(path.as_uri() + '?mode=ro', uri=True, timeout=2) as c:
        rows = c.execute('SELECT a.payload FROM assessments a JOIN (SELECT case_id,MAX(revision) AS r FROM assessments GROUP BY case_id) b ON a.case_id=b.case_id AND a.revision=b.r ORDER BY a.created_at DESC').fetchall()
    out = []
    for (payload,) in rows:
        record = json.loads(payload)
        case, assessment = record['case'], record['assessment']
        item = {'title': record['name'], 'outcome': assessment['outcome'], 'revision': record['revision'], 'saved': record['created_at'][:10], 'risks': assessment.get('risk_ids', []), 'unresolved': assessment.get('unresolved', []),
                'answers': {k: case[k] for k in ('tool_access', 'information_involved', 'role_of_output', 'banking_process', 'task_expertise', 'approval_status')}, 'forms': case['forms']}
        haystack = json.dumps(item).lower()
        if all(w.lower() in haystack for w in words):
            out.append(item)
    return out[:limit]

def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    filename = os.environ.get('GOVERNANCE_DB_PATH', '')
    if not filename:
        # When the plugin is loaded from the project folder, the register sits beside it.
        beside = Path(__file__).resolve().parents[4] / '.runtime' / 'register.sqlite'
        if beside.exists():
            filename = str(beside)
    if not filename:
        print('GOVERNANCE_DB_PATH is not set. Set it to the absolute path of the workspace register, for example /path/to/genai-bank-governance/.runtime/register.sqlite')
        return 1
    try:
        items = find(Path(filename), argv)
    except sqlite3.Error:
        print('The register could not be read.')
        return 1
    if not items:
        print('No saved reviews match.' if argv else 'The register has no saved reviews.')
        return 0
    for i in items:
        print(json.dumps(i, ensure_ascii=False))
    return 0

if __name__ == '__main__':
    sys.exit(main())
