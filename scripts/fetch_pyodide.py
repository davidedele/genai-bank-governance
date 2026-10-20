"""Downloads the official Pyodide release and keeps only the files the demo needs.

Usage: python scripts/fetch_pyodide.py OUTPUT_DIR [--archive FILE]
The download is checked against a fixed SHA-256 value before anything is unpacked, so the demo
runs the exact runtime that was reviewed and not whatever a server happens to return.
Pyodide checks every package file it loads against the hashes in the lock file as well.
"""
import argparse
import hashlib
import json
import shutil
import tarfile
import tempfile
import urllib.request
from pathlib import Path

VERSION = '0.29.3'
URL = f'https://github.com/pyodide/pyodide/releases/download/{VERSION}/pyodide-{VERSION}.tar.bz2'
SHA256 = '458e8ddbcbb6e21037d3237cd5c5146c451765bc738dfa2249ff34c5140331e4'
# The Python packages the in-browser app loads. static_demo/runtime.js loads the same list.
PACKAGES = ['fastapi', 'pydantic', 'sqlite3']
CORE_FILES = ['pyodide.js', 'pyodide.asm.js', 'pyodide.asm.wasm', 'python_stdlib.zip', 'pyodide-lock.json']


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, 'rb') as handle:
        for block in iter(lambda: handle.read(1 << 20), b''):
            digest.update(block)
    return digest.hexdigest()


def needed_packages(lock: dict, names=PACKAGES) -> dict:
    """The named packages and everything they depend on, as entries of the lock file."""
    packages = lock['packages']
    wanted, pending = {}, list(names)
    while pending:
        name = pending.pop().lower().replace('_', '-')
        if name in wanted:
            continue
        wanted[name] = packages[name]
        pending.extend(packages[name]['depends'])
    return wanted


def trim(source: Path, out: Path) -> list:
    """Copies the core files and the needed packages from an unpacked release folder."""
    lock = json.loads((source / 'pyodide-lock.json').read_text())
    wanted = needed_packages(lock)
    out.mkdir(parents=True, exist_ok=True)
    for name in CORE_FILES:
        if name != 'pyodide-lock.json':
            shutil.copy(source / name, out / name)
    for entry in wanted.values():
        shutil.copy(source / entry['file_name'], out / entry['file_name'])
    lock['packages'] = wanted
    (out / 'pyodide-lock.json').write_text(json.dumps(lock))
    return sorted(wanted)


def unpack(archive: Path, target: Path) -> None:
    """Unpacks plain files and folders only. Links, devices and paths that leave the target are refused."""
    root = target.resolve()
    with tarfile.open(archive, 'r:bz2') as tar:
        for member in tar:
            destination = (root / member.name).resolve()
            if root != destination and root not in destination.parents:
                raise SystemExit(f'Refusing to unpack {member.name}: it points outside the target folder.')
            if member.isdir():
                destination.mkdir(parents=True, exist_ok=True)
            elif member.isreg():
                destination.parent.mkdir(parents=True, exist_ok=True)
                with tar.extractfile(member) as source, open(destination, 'wb') as handle:
                    shutil.copyfileobj(source, handle)
            else:
                raise SystemExit(f'Refusing to unpack {member.name}: only plain files and folders are expected.')


def fetch(out: Path, archive: Path = None) -> list:
    with tempfile.TemporaryDirectory() as scratch:
        scratch = Path(scratch)
        if archive is None:
            archive = scratch / 'pyodide.tar.bz2'
            print(f'Downloading {URL}')
            assert URL.startswith('https://')
            # A fixed https address; the checksum below decides whether the file is used.
            urllib.request.urlretrieve(URL, archive)  # nosec B310
        if sha256_of(archive) != SHA256:
            raise SystemExit('The Pyodide download does not match the expected checksum. Nothing was unpacked.')
        unpack(archive, scratch / 'unpacked')
        return trim(scratch / 'unpacked' / 'pyodide', out)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('output', type=Path)
    parser.add_argument('--archive', type=Path, help='Use this already downloaded .tar.bz2 instead of downloading it')
    args = parser.parse_args()
    names = fetch(args.output, args.archive)
    print(f'Kept {len(names)} packages in {args.output}: {", ".join(names)}')
