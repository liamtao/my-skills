#!/usr/bin/env python3
"""Read/stage OKyun scripts; offline apply never controls application lifecycle."""
import argparse
import copy
import ctypes
import hashlib
import json
from pathlib import Path
import plistlib
import shlex
import shutil
import subprocess
import sys
from datetime import datetime

DOMAIN = "com.okyun.clash"
KEY = "flutter.config"
STAGE_ROOT = Path.home() / "Library/Application Support/OKyun-migration/changes"


def digest(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def baseline_path(source):
    return source.with_name(source.name + ".baseline.json")


def read_preferences():
    result = subprocess.run(
        ["/usr/bin/defaults", "export", DOMAIN, "-"], capture_output=True
    )
    if result.returncode:
        raise ValueError("Cannot read OKyun preferences; no changes made.")
    preferences = plistlib.loads(result.stdout)
    return result.stdout, json.loads(preferences[KEY])


def selected_script(config):
    profile = next(
        p for p in config["profiles"] if p["id"] == config["currentProfileId"]
    )
    overwrite = profile["overwrite"]
    if overwrite["type"] != "script":
        raise ValueError("Current profile is not using a script; select the intended binding first.")
    script_id = overwrite["scriptOverwrite"]["scriptId"]
    script = next(s for s in config["scripts"] if s["id"] == script_id)
    return profile, script


def app_is_running():
    result = subprocess.run(
        ["/bin/ps", "-axo", "comm="], capture_output=True, text=True, check=True
    )
    return any(
        line.strip().endswith("/OK云.app/Contents/MacOS/OK云")
        or line.strip() == "OK云"
        for line in result.stdout.splitlines()
    )


def private_file(path, content):
    data = content.encode("utf-8") if isinstance(content, str) else content
    with path.open("xb") as stream:
        path.chmod(0o600)
        stream.write(data)


def check_syntax(source):
    node = shutil.which("node")
    if node is None:
        raise ValueError("Node.js is required for syntax validation; nothing applied.")
    result = subprocess.run(
        [node, "--check", "--input-type=commonjs"],
        input=source, text=True, capture_output=True,
    )
    if result.returncode:
        raise ValueError("JavaScript syntax validation failed (node --check); nothing applied.")


def prepare_update(config, manifest, source):
    if digest(source) != manifest["new_sha256"]:
        raise ValueError("Staged source changed; export and stage again.")
    profile, script = selected_script(config)
    if (profile["id"], script["id"]) != (manifest["profile_id"], manifest["script_id"]):
        raise ValueError("Active profile or script binding changed; nothing applied.")
    current_hash = digest(script["content"])
    if current_hash == manifest["new_sha256"]:
        return copy.deepcopy(config), False
    if current_hash != manifest["old_sha256"]:
        raise ValueError("Saved script changed since staging; merge current edits first.")
    updated = copy.deepcopy(config)
    next(s for s in updated["scripts"] if s["id"] == script["id"])["content"] = source
    return updated, True


def write_config(config):
    # Update one preference key through CFPreferences; credentials never enter argv.
    library = ctypes.CDLL(
        "/System/Library/Frameworks/CoreFoundation.framework/CoreFoundation"
    )
    pointer = ctypes.c_void_p
    library.CFStringCreateWithCString.argtypes = [pointer, ctypes.c_char_p, ctypes.c_uint32]
    library.CFStringCreateWithCString.restype = pointer
    library.CFPreferencesSetAppValue.argtypes = [pointer, pointer, pointer]
    library.CFPreferencesSetAppValue.restype = None
    library.CFPreferencesAppSynchronize.argtypes = [pointer]
    library.CFPreferencesAppSynchronize.restype = ctypes.c_bool
    library.CFRelease.argtypes = [pointer]
    library.CFRelease.restype = None
    values = [KEY, json.dumps(config, ensure_ascii=False, separators=(",", ":")), DOMAIN]
    references = []
    try:
        for value in values:
            reference = library.CFStringCreateWithCString(None, value.encode("utf-8"), 0x08000100)
            if not reference:
                raise ValueError("Cannot encode preferences; nothing applied.")
            references.append(reference)
        library.CFPreferencesSetAppValue(*references)
        if not library.CFPreferencesAppSynchronize(references[2]):
            raise ValueError("Preference synchronization failed; inspect saved state before retrying.")
    finally:
        for reference in references:
            library.CFRelease(reference)


def load_stage(folder):
    manifest = json.loads((folder / "change.json").read_text(encoding="utf-8"))
    source = (folder / "override.js").read_text(encoding="utf-8")
    return manifest, source


def apply_stage(folder):
    if app_is_running():
        raise ValueError("OKyun is running. Quit it yourself, run this command offline, then reopen it yourself.")
    manifest, source = load_stage(folder)
    check_syntax(source)
    raw, config = read_preferences()
    updated, changed = prepare_update(config, manifest, source)
    if not changed:
        return {"saved": True, "changed": False, "next": "Open OKyun yourself; then verify runtime configuration."}
    backup = folder / "before-apply.plist"
    if not backup.exists():
        private_file(backup, raw)
    if app_is_running():
        raise ValueError("OKyun was reopened; nothing applied. Quit it before retrying.")
    write_config(updated)
    _, actual = read_preferences()
    if actual != updated:
        raise ValueError("Readback differs; preserve the backup and inspect before retrying.")
    return {"saved": True, "changed": True, "backup": str(backup), "next": "Open OKyun yourself; then verify runtime configuration."}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["export", "stage", "check", "apply", "verify"])
    parser.add_argument("path", type=Path)
    args = parser.parse_args(argv)
    path = args.path.expanduser().resolve()
    if args.command == "apply":
        return apply_stage(path)
    _, config = read_preferences()
    profile, script = selected_script(config)
    if args.command == "export":
        baseline = {"profile_id": profile["id"], "script_id": script["id"], "old_sha256": digest(script["content"])}
        if path.exists() or baseline_path(path).exists():
            raise ValueError("Export destination already exists; choose a new path.")
        private_file(path, script["content"])
        private_file(baseline_path(path), json.dumps(baseline, ensure_ascii=False, indent=2) + "\n")
        return {"source": str(path), "profile_id": profile["id"], "script_id": script["id"], "label": script["label"], "sha256": digest(script["content"])}
    if args.command in ("check", "verify"):
        manifest, source = load_stage(path)
        _, changed = prepare_update(config, manifest, source)
        if args.command == "check":
            return {"ready_for_ui_save": changed, "already_saved": not changed}
        if changed:
            raise ValueError("Candidate is staged but has not been saved in OKyun.")
        return {"stored_script_matches": True, "runtime_applied": "Check generated config.yaml and client connection separately."}
    source = path.read_text(encoding="utf-8")
    baseline = json.loads(baseline_path(path).read_text(encoding="utf-8"))
    if (profile["id"], script["id"], digest(script["content"])) != (baseline["profile_id"], baseline["script_id"], baseline["old_sha256"]):
        raise ValueError("Saved script or binding changed since export; export again and merge current edits.")
    check_syntax(source)
    folder = STAGE_ROOT / datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    folder.mkdir(parents=True, mode=0o700)
    folder.chmod(0o700)
    manifest = {
        "profile_id": profile["id"], "script_id": script["id"],
        "old_sha256": digest(script["content"]), "new_sha256": digest(source),
    }
    private_file(folder / "original.js", script["content"])
    private_file(folder / "override.js", source)
    private_file(folder / "change.json", json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    command = [sys.executable, str(Path(__file__).resolve()), "apply", str(folder)]
    return {"stage": str(folder), "syntax_valid": True, "live_preferences_changed": False, "offline_apply_command_for_user": shlex.join(command)}


if __name__ == "__main__":
    try:
        print(json.dumps(main(), ensure_ascii=False, indent=2))
    except (ValueError, KeyError, StopIteration, OSError, subprocess.SubprocessError) as error:
        message = str(error) if isinstance(error, ValueError) else "Cannot complete this operation; inspect local inputs and preference schema."
        print(message, file=sys.stderr)
        sys.exit(1)
