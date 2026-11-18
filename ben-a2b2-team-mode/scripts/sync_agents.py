#!/usr/bin/env python3
"""Install Team Mode's project profiles while preserving local customizations."""

import argparse
from collections import defaultdict
from difflib import unified_diff
import hashlib
import json
from pathlib import Path
import stat
import tempfile
import tomllib


TEMPLATES = Path(__file__).resolve().parents[1] / "assets" / "codex-agents"


def profile_names(directory: Path) -> dict[str, list[Path]]:
    """Codex identifies a role by its TOML name, which can differ from the filename."""
    profiles = defaultdict(list)
    for path in sorted(directory.glob("*.toml")):
        if not path.is_file():
            continue
        try:
            profile = tomllib.loads(path.read_text(encoding="utf-8"))
        except (UnicodeError, tomllib.TOMLDecodeError):
            continue
        name = profile.get("name")
        if isinstance(name, str):
            profiles[name].append(path)
    return profiles


def report_difference(path: Path, current: bytes, template: Path, wanted: bytes) -> None:
    print("".join(unified_diff(
        current.decode("utf-8", errors="replace").splitlines(keepends=True),
        wanted.decode("utf-8").splitlines(keepends=True),
        fromfile=str(path),
        tofile=str(template),
        n=0,
    )).rstrip())


def sync(project: Path) -> None:
    versions = json.loads((TEMPLATES / "known-versions.json").read_text(encoding="utf-8"))
    templates = {path.stem: path.read_bytes() for path in sorted(TEMPLATES.glob("*.toml"))}
    for role, content in templates.items():
        if tomllib.loads(content.decode("utf-8")).get("name") != role:
            raise ValueError(f"Template name does not match role {role}")

    codex = project / ".codex"
    directory = codex / "agents"
    for path in (codex, directory):
        if path.is_symlink() or (path.exists() and not path.is_dir()):
            raise ValueError(f"Expected a project directory at {path}")
        path.mkdir(exist_ok=True)

    names = profile_names(directory)
    for role, wanted in templates.items():
        template = TEMPLATES / f"{role}.toml"
        path = directory / template.name
        aliases = [other for other in names.get(role, []) if other != path]
        if aliases:
            for other in aliases:
                print(f"PRESERVED {other} (declares {role} under another filename)")
                current = other.read_bytes()
                if current != wanted:
                    report_difference(other, current, template, wanted)
            print(f"SKIPPED {path} (another file declares {role})")
            continue
        if path.is_symlink() or (path.exists() and not path.is_file()):
            print(f"PRESERVED {path} (expected a regular file)")
            continue
        if not path.exists():
            with path.open("xb") as output:
                output.write(wanted)
            print(f"CREATED {path}")
            continue

        current = path.read_bytes()
        if current == wanted:
            print(f"CURRENT {path}")
        elif hashlib.sha256(current).hexdigest() in versions.get(role, []):
            with tempfile.NamedTemporaryFile(dir=directory, delete=False) as output:
                staged = Path(output.name)
                try:
                    output.write(wanted)
                    output.close()
                    staged.chmod(stat.S_IMODE(path.stat().st_mode))
                    if path.is_symlink() or path.read_bytes() != current:
                        print(f"PRESERVED {path} (changed during sync)")
                        continue
                    staged.replace(path)
                    print(f"UPDATED {path}")
                finally:
                    staged.unlink(missing_ok=True)
        else:
            print(f"PRESERVED {path} (custom content)")
            report_difference(path, current, template, wanted)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", required=True, type=Path, help="Target project root")
    args = parser.parse_args()
    try:
        project = args.project.resolve(strict=True)
        if not project.is_dir():
            raise ValueError(f"Project root must be a directory: {project}")
        sync(project)
    except (OSError, ValueError) as exc:
        parser.exit(1, f"Profile sync failed: {exc}\n")
