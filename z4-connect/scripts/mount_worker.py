"""macOS no-UI SMB mount worker; credentials stay in this process's memory."""

import ctypes
import json
import subprocess
import sys
from urllib.parse import quote


def read_password(account):
    security = ctypes.CDLL("/System/Library/Frameworks/Security.framework/Security")
    pointer = ctypes.c_void_p
    security.SecKeychainSetUserInteractionAllowed.argtypes = [ctypes.c_bool]
    security.SecKeychainGetStatus.argtypes = [pointer, ctypes.POINTER(ctypes.c_uint32)]
    if security.SecKeychainSetUserInteractionAllowed(False):
        raise RuntimeError("Keychain unavailable")
    status = ctypes.c_uint32()
    if security.SecKeychainGetStatus(None, ctypes.byref(status)) or not status.value & 1:
        raise RuntimeError("Keychain unavailable")
    # The existing item's ACL trusts /usr/bin/security, not the Python binary.
    # Read its captured pipe only; never put the password in argv or an error.
    result = subprocess.run(["/usr/bin/security", "find-generic-password", "-s", "codex.nas.z4.ssh",
        "-a", account, "-w"], capture_output=True, text=True, timeout=8)
    if result.returncode or not result.stdout:
        raise RuntimeError("Keychain unavailable")
    return result.stdout.removesuffix("\n")


def mount_share(config, password):
    core = ctypes.CDLL("/System/Library/Frameworks/CoreFoundation.framework/CoreFoundation")
    netfs = ctypes.CDLL("/System/Library/Frameworks/NetFS.framework/NetFS")
    pointer = ctypes.c_void_p
    core.CFStringCreateWithCString.argtypes = [pointer, ctypes.c_char_p, ctypes.c_uint32]
    core.CFStringCreateWithCString.restype = pointer
    core.CFURLCreateWithString.argtypes = [pointer, pointer, pointer]
    core.CFURLCreateWithString.restype = pointer
    core.CFDictionaryCreateMutable.argtypes = [pointer, ctypes.c_long, pointer, pointer]
    core.CFDictionaryCreateMutable.restype = pointer
    core.CFDictionarySetValue.argtypes = [pointer, pointer, pointer]
    core.CFRelease.argtypes = [pointer]
    netfs.NetFSMountURLSync.argtypes = [pointer] * 6 + [ctypes.POINTER(pointer)]
    netfs.NetFSMountURLSync.restype = ctypes.c_int
    refs, mounted = [], pointer()

    def string(value):
        ref = core.CFStringCreateWithCString(None, value.encode(), 0x08000100)
        if not ref:
            raise RuntimeError("CFString allocation failed")
        refs.append(ref)
        return ref

    try:
        address = f"smb://{config['nas_host']}/{quote(config['share'], safe='')}"
        url = core.CFURLCreateWithString(None, string(address), None)
        options = core.CFDictionaryCreateMutable(None, 0, None, None)
        refs.extend([url, options])
        core.CFDictionarySetValue(options, string("UIOption"), string("NoUI"))
        # NetFS creates the share's mountpoint under /Volumes. The caller verifies
        # the exact mount afterwards, and never accepts an alternate '-1' path.
        return netfs.NetFSMountURLSync(url, None, string(config["nas_user"]), string(password),
            options, None, ctypes.byref(mounted))
    finally:
        if mounted:
            core.CFRelease(mounted)
        for ref in reversed(refs):
            if ref:
                core.CFRelease(ref)


def main():
    try:
        config = json.load(sys.stdin)
        password = read_password(config["nas_user"])
    except Exception:
        return 2
    try:
        return 0 if mount_share(config, password) == 0 else 3
    except Exception:
        return 3


if __name__ == "__main__":
    sys.exit(main())
