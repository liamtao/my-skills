"""Partition package files using exact Git paths, preserving tracked official assets."""
import os
from pathlib import Path
import subprocess

NOISE = {'.git', '__pycache__', '.DS_Store', '.venv', 'venv', '.idea', '.vscode',
         '.pytest_cache', '.ruff_cache', '.mypy_cache', 'node_modules', '.ipynb_checkpoints'}


def package_inventory(repo, package):
    package = Path(package)
    files = []
    for directory, dirs, names in os.walk(package):
        dirs[:] = [d for d in dirs if d not in NOISE]
        for name in names:
            if name not in NOISE:
                files.append((Path(directory) / name).relative_to(package).as_posix())
    tracked = set(os.fsdecode(subprocess.check_output(
        ['git', '-C', str(repo), 'ls-files', '-z'])).split('\0')) - {''}
    result = subprocess.run(['git', '-C', str(repo), 'check-ignore', '--no-index', '-z', '--stdin'],
                            input=os.fsencode('\0'.join(files) + ('\0' if files else '')),
                            capture_output=True)
    if result.returncode not in (0, 1):
        raise RuntimeError('git check-ignore failed')
    ignored = set(os.fsdecode(result.stdout).split('\0')) - {''}
    runtime = ignored - tracked
    return sorted(set(files) - runtime), sorted(runtime)
