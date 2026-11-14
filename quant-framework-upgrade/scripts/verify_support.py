"""Optional runtime checks for dynamic configurations; no framework-specific defaults."""
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile


@contextmanager
def isolated_repo(repo):
    """Copy Git-visible files, including tracked reference data, into a disposable cwd.

    This protects ordinary relative-path side effects, not hostile code or absolute writes.
    Symlinks are never followed into another project/library.
    """
    with tempfile.TemporaryDirectory(prefix='quant-verify-') as directory:
        target = Path(directory)
        output = subprocess.check_output(['git', '-C', str(repo), 'ls-files', '-co',
                                          '--exclude-standard', '-z'])
        for rel in set(os.fsdecode(output).split('\0')) - {''}:
            source = repo / rel
            if not source.is_file() or any(p.is_symlink() for p in [source, *source.parents] if p != repo):
                continue
            if any(p in ('.git', '.venv', '__pycache__', 'node_modules') for p in Path(rel).parts):
                continue
            destination = target / rel
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)
        yield target


def run_probe(repo, python, code, timeout=60):
    """Use the selected interpreter with a fresh module table and no bytecode/network."""
    prefix = '''import sys, socket, webbrowser
from pathlib import Path
sys.path.insert(0, str(Path.cwd()))
def offline(*args, **kwargs):
    raise RuntimeError("verification probe does not allow network connections")
socket.socket.connect = offline
socket.create_connection = offline
webbrowser.open = lambda *a, **k: False
webbrowser.open_new = webbrowser.open
webbrowser.open_new_tab = webbrowser.open
'''
    with isolated_repo(repo) as sandbox:
        try:
            result = subprocess.run([python, '-B', '-c', prefix + code], cwd=sandbox,
                                    env={**os.environ, 'PYTHONPATH': str(sandbox),
                                         'PYTHONDONTWRITEBYTECODE': '1'},
                                    capture_output=True, text=True, timeout=timeout)
        except subprocess.TimeoutExpired:
            raise RuntimeError(f'probe timed out after {timeout}s') from None
        line = next((s for s in result.stdout.splitlines() if s.startswith('@@JSON@@')), None)
        if result.returncode or line is None:
            # Module output may contain credentials; do not echo arbitrary stdout/stderr.
            raise RuntimeError(f'probe failed (exit {result.returncode}); no structured result')
        return json.loads(line[8:])


def effective_keys(repo, python):
    result = run_probe(repo, python, '''import importlib, json
try:
    config = importlib.import_module("config")
    result = {"keys": [k for k in vars(config) if not k.startswith("_")],
              "selection": isinstance(getattr(config, "strategy_list", None), list) and bool(config.strategy_list),
              "position": isinstance(getattr(config, "strategy_config", None), dict) and bool(config.strategy_config)
                          and isinstance(getattr(config, "strategy_pool", None), list) and bool(config.strategy_pool)}
except BaseException as error:
    result = {"error": type(error).__name__}
print("@@JSON@@" + json.dumps(result))
''')
    if 'error' in result:
        raise RuntimeError('config import failed: ' + result['error'])
    return result


def mode_exclusions(keys, selection, position):
    """Explicit selection-position layout only; flat stock/live configs never use this."""
    select_defined = 'strategy_list' in keys
    position_defined = bool({'strategy_config', 'strategy_pool'} & set(keys))
    if select_defined and not position_defined and selection:
        return {'strategy_config', 'strategy_pool'}
    if position_defined and not select_defined and position:
        return {'strategy_list'}
    raise ValueError('selection-position config must define exactly one complete nonempty mode')


def import_skips(repo, policy):
    """An explicit reviewed policy permits exact unchanged paths, never whole directories."""
    if policy is None:
        return {}
    contents = json.loads(Path(policy).read_text(encoding='utf-8'))
    skips = {}
    for item in contents['skip_imports']:
        relative = Path(item['path'])
        path = repo / relative
        if relative.is_absolute() or '..' in relative.parts or relative.suffix != '.py':
            raise ValueError('import policy requires relative .py file paths')
        if relative.parts[0] == 'core' or relative.as_posix() == 'config.py':
            raise ValueError('core and active config cannot be excluded')
        if not item.get('reason') or not path.is_file():
            raise ValueError(f'invalid import policy entry: {relative}')
        if hashlib.sha256(path.read_bytes()).hexdigest() != item['sha256']:
            raise ValueError(f'import policy fingerprint changed: {relative}')
        skips[relative.as_posix()] = {'reason': item['reason'], 'loader': item.get('loader')}
    return skips
