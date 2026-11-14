# Build and verification details

## Find the current implementation

Use the policy's engine-selection order. Inspect `scripts/build_ipa_from_nsp.py --help` with that engine's Python and read its requirement checks before constructing a command. Keep versions and installed tool paths discoverable rather than pinning this skill to a past build. For internals, consult the selected engine's `docs/development.md`, `docs/agents/symptoms.md` and the game's profile note.

The current script discovers package files at the input directory's first level. Inspect nested source folders yourself, then copy selected packages into local `sources/`; do not rename a package merely to make it look like another version. It supports NSP/XCI and compressed NSZ/XCZ when the appropriate decompressor is available. Preserve the user's necessary original package formats in the archive rather than retaining decompression caches as additional source packages.

Use `-p` only after checking the selected package version against the current profile. It is a package selector, not a generic "latest" switch. Keep title ID and display version separate from profile aliases such as `v1`. If several games share an input container, inspect supported title selection instead of guessing an ID.

## Build command shape

Set the variables below from inspected paths: `game_dir` is the local game-name folder, `engine_work` is its complete writable engine copy, `py_bin` and `tool_bin` are the selected Python and tool directory, `keys_file` is the existing persistent private key, `app_name` is the output app basename, and `game_language` is a supported language code. Preserve any required .NET environment discovered during toolchain checks.

```sh
mkdir -p "$game_dir/sources/tmp"
PATH="$tool_bin:$PATH" \
TMPDIR="$game_dir/sources/tmp/" \
"$py_bin" "$engine_work/scripts/build_ipa_from_nsp.py" \
  "$game_dir/sources" \
  -k "$keys_file" \
  --platform mac-app \
  -l "$game_language" \
  -o "$game_dir/$app_name.app" \
  --progress lines \
  > "$game_dir/build-mac.log" 2>&1
```

The input directory's default `<title ID>_build/` stays local. If using `--work-dir`, first verify that the selected engine supports it and point it inside this same workspace. Do not assume the app's global output preference relocates every temporary file or copies external inputs locally.

A failed command leaves logs for diagnosis. Check its actual exit status; do not hide failure through an unchecked logging pipeline. Read the complete error context rather than treating any `[RED]` line as a cosmetic warning.

## Validate an app

Use `Contents/Info.plist` to read the executable, title ID and version. Validate the complete bundle with:

```sh
codesign --verify --deep --strict "$game_app"
```

Check resources and any symlink targets against the current packer and module inventory. A self-contained app can be moved independently of build caches; APFS clones are independent files and are not symlink dependencies.

The game launcher normally accepts `--no-launcher`. For an isolated test, set `DM_SAVE` to a separate test save directory, `DM_ROOT` and `DM_TEMP` to test-only paths, and `DM_SAVE_SYNC` to an empty string to disable cloud synchronization. Confirm these behaviors against the selected engine's launcher and save-sync implementation before use. Avoid assuming the launcher log itself moves with `DM_ROOT`: inspect its reported log location and archive the resulting log.

Where available, `DM_CTL` allows input and a `shot <absolute PNG path>` request. Observe the current screen before sending keys; avoid long blind key sequences. Do not force `DM_ROMFS` or shader paths to build artifacts during validation: testing must use the finished app's bundled resources. Stop gracefully and wait for the host to exit before evaluating logs or moving files.

A passing record includes the tested app path, version, title ID, signature result, visible screen, rendering evidence, screenshot, exit status, and any `[RED]`/crash findings. Separate isolated-save compatibility from formal save migration. Record limitations honestly, including absent controller or gameplay testing.

## Update the launcher

Discover the current library implementation and configuration before writing. On this installation the library has been stored at `~/Library/Application Support/NS Port Builder/library.json`; the app name does not imply the directory name changed. Preserve its schema and IDs rather than regenerating the whole library.

Check the game's `appPath`, `sourceFolder`, `inputs` base/update/DLC/keys lists, `outputDirectory`, and `lastTarget` against the current implementation. Older entries may reference a removed local folder or superseded update even when the app path works. Keep retained input paths on the external drive, future build output local, and the target Mac; the next build must still copy its inputs locally as required by policy.

Prefer a supported import/rescan flow when it produces these results. If a configuration edit is necessary, close the launcher normally, back up the file, change only this game's relevant fields, write atomically, reopen and read back the effective paths. Preserve existing player saves and user launch options.
