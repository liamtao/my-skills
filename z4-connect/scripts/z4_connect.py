#!/usr/bin/env python3
"""Connect to the home Z4 using credentials held in macOS Keychain."""

import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import sys

HOST = "192.168.5.28"
PORT = 10000
SHARE = "135XXXX9330"
SERVICE = "codex.nas.z4.ssh"
MOUNT = Path("/Volumes") / SHARE
SCRIPTS = Path(__file__).resolve().parent


class ConnectionFailure(RuntimeError):
    pass


def read_account():
    result = subprocess.run(
        ["/usr/bin/security", "find-generic-password", "-s", SERVICE],
        capture_output=True, text=True, timeout=8,
    )
    match = re.search(r'"acct"<blob>="([^"\r\n]+)"', result.stdout)
    if result.returncode or not match:
        raise ConnectionFailure("钥匙串账户不可用，请检查 codex.nas.z4.ssh 条目")
    return match[1]


def verify_mount(account):
    result = subprocess.run(["/sbin/mount", "-t", "smbfs"],
                            capture_output=True, text=True, timeout=10)
    expected = f"//{account}@{HOST}/{SHARE} on {MOUNT} (smbfs,"
    return (result.returncode == 0 and not MOUNT.is_symlink()
            and os.path.ismount(MOUNT)
            and any(line.startswith(expected) for line in result.stdout.splitlines()))


def ensure_mount(account):
    if verify_mount(account):
        return str(MOUNT)
    if os.path.lexists(MOUNT):
        raise ConnectionFailure("挂载路径已被目录、链接或其他共享占用，请先检查；未覆盖")
    config = {"nas_host": HOST, "nas_user": account, "share": SHARE}
    try:
        result = subprocess.run([sys.executable, str(SCRIPTS / "mount_worker.py")],
                                input=json.dumps(config), capture_output=True,
                                text=True, timeout=45)
        failure = ("钥匙串密码不可用，请检查解锁状态及访问授权"
                   if result.returncode == 2 else "SMB 自动挂载失败，请检查网络、共享及凭据")
    except subprocess.TimeoutExpired:
        failure = "SMB 自动挂载超时"
    # Finder or a concurrent caller may have completed the same mount.
    if not verify_mount(account):
        raise ConnectionFailure(failure + "；指定共享挂载核对未通过")
    return str(MOUNT)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="mode", required=True)
    sub.add_parser("smb", help="Reuse or automatically mount the verified SMB share")
    ssh = sub.add_parser("ssh", help="Run one SSH command using Keychain authentication")
    ssh.add_argument("--sudo", action="store_true", help="Execute as root through sudo")
    ssh.add_argument("--timeout", type=int, default=60, help="Seconds per connection/command stage")
    ssh.add_argument("command", nargs="?", default="id")
    args = parser.parse_args()
    if args.mode == "ssh" and args.timeout <= 0:
        parser.error("--timeout must be positive")
    try:
        account = read_account()
        if args.mode == "smb":
            print(ensure_mount(account))
            return 0
        return subprocess.call([
            "/usr/bin/expect", str(SCRIPTS / "ssh.exp"), HOST, str(PORT),
            account, SERVICE, str(args.timeout), str(int(args.sudo)), args.command,
        ])
    except ConnectionFailure as exc:
        print(str(exc), file=sys.stderr)
    except subprocess.TimeoutExpired:
        print("连接检查超时，请检查钥匙串或 NAS 状态", file=sys.stderr)
    except OSError:
        print("连接工具不可用，请在 macOS 上检查 Python、security、expect 和 ssh", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
