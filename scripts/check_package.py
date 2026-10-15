"""Check a tracked release tree for accidentally included runtime artifacts."""
from pathlib import Path
import json
import subprocess
ROOT = Path(__file__).resolve().parents[1]

def main():
    try:
        names = subprocess.check_output(['git', '-C', str(ROOT), 'ls-files', '-z'], stderr=subprocess.DEVNULL).decode().split('\x00')
    except subprocess.CalledProcessError:
        names = [str(p.relative_to(ROOT)) for p in ROOT.rglob('*') if p.is_file()]
    errors = []
    for name in names:
        if not name:
            continue
        p = Path(name)
        if p.name == '.env' or p.name == 'auto_log.jsonl' or p.suffix in {'.sqlite', '.bundle', '.patch'} or ('.git' in p.parts):
            errors.append(name)
    settings = json.loads((ROOT / '.claude/settings.json').read_text())
    assert settings['attribution'] == {'commit': '', 'pr': '', 'sessionUrl': False}
    if errors:
        raise SystemExit('Runtime/private files found in package or tracked tree: ' + ', '.join(errors))
    print('Release tree checks passed.')
if __name__ == '__main__':
    main()
