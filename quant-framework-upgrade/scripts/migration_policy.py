"""Translate an approved migration manifest into exact, fingerprint-bound import rules.

Only writes the specified new policy file. No framework module is imported.
"""
import argparse
import hashlib
import json
import subprocess
from pathlib import Path


def build_policy(repo, manifest, blocked, loader, baseline_ref):
    assets = {item.get('destination', item['path']): item.get('destination_sha256')
              for item in manifest['assets'] if item.get('destination_sha256')}
    entries = []
    wanted = [(p['path'], p['status'], p.get('reason', p['status'])) for p in manifest['profiles']]
    wanted += [('strategy/' + name.replace('.', '/') + '.py', 'blocked', reason)
               for name, reason in blocked.items()]
    for path, status, reason in wanted:
        relative = Path(path)
        if relative.is_absolute() or '..' in relative.parts:
            raise ValueError('manifest paths must be relative')
        source = repo / path
        if not source.exists() and status == 'excluded_ml':
            continue
        expected = assets.get(path)
        if expected is None:
            # Generated active profiles may have no source asset entry. Anchor them
            # to an explicitly chosen pre-upgrade Git ref, never the working tree.
            result = subprocess.run(['git', '-C', str(repo), 'show', f'{baseline_ref}:{path}'],
                                    capture_output=True)
            if result.returncode == 0:
                expected = hashlib.sha256(result.stdout).hexdigest()
        if not expected or not source.is_file() or hashlib.sha256(source.read_bytes()).hexdigest() != expected:
            raise ValueError(f'approved destination fingerprint missing or changed: {path}')
        item = dict(path=path, sha256=expected, reason=reason)
        if status == 'validated_config':
            item['loader'] = loader
        elif status not in ('blocked', 'data_blocked', 'excluded_ml'):
            raise ValueError(f'unknown manifest status: {status}')
        entries.append(item)
    return {'skip_imports': entries}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', type=Path, default=Path.cwd())
    parser.add_argument('--manifest', type=Path, required=True)
    parser.add_argument('--blocked-strategies', type=Path)
    parser.add_argument('--profile-loader', required=True, help='module:function, returning a configuration dict')
    parser.add_argument('--baseline-ref', required=True, help='Reviewed pre-upgrade tag/commit')
    parser.add_argument('--output', type=Path, required=True, help='New file outside the framework')
    args = parser.parse_args()
    repo = args.repo.resolve()
    output = args.output.resolve()
    if output == repo or repo in output.parents:
        parser.error('--output must be outside the framework')
    manifest = json.loads(args.manifest.read_text(encoding='utf-8'))
    blocked = json.loads(args.blocked_strategies.read_text(encoding='utf-8')) if args.blocked_strategies else {}
    result = build_policy(repo, manifest, blocked, args.profile_loader, args.baseline_ref)
    with output.open('x', encoding='utf-8') as handle:
        json.dump(result, handle, ensure_ascii=False, indent=2)
    print(f'Wrote {len(result["skip_imports"])} fingerprint-bound rules: {output}')


if __name__ == '__main__':
    main()
