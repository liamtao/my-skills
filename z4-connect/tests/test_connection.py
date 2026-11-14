"""Offline checks: never mount, unmount, or read real credentials."""

import io
import json
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import mount_worker
import z4_connect as z4


class MountTests(unittest.TestCase):
    def setUp(self):
        self.verify = self.enterContext(patch.object(z4, "verify_mount"))
        self.verify.return_value = False
        self.exists = self.enterContext(patch.object(z4.os.path, "lexists", return_value=False))
        self.run = self.enterContext(patch.object(z4.subprocess, "run", return_value=Mock(returncode=0)))

    def test_existing_mount_is_reused_without_worker(self):
        self.verify.return_value = True
        self.assertEqual(z4.ensure_mount("user"), str(z4.MOUNT))
        self.run.assert_not_called()

    def test_absent_mount_invokes_worker_and_verifies_result(self):
        self.verify.side_effect = [False, True]
        self.assertEqual(z4.ensure_mount("user"), str(z4.MOUNT))
        args, kwargs = self.run.call_args
        self.assertEqual(Path(args[0][1]).name, "mount_worker.py")
        self.assertEqual(json.loads(kwargs["input"]),
                         {"nas_host": z4.HOST, "nas_user": "user", "share": z4.SHARE})
        self.assertEqual(kwargs["timeout"], 45)

    def test_occupied_path_is_preserved(self):
        self.exists.return_value = True
        with self.assertRaises(z4.ConnectionFailure):
            z4.ensure_mount("user")
        self.run.assert_not_called()

    def test_worker_success_without_verified_mount_is_failure(self):
        with self.assertRaises(z4.ConnectionFailure):
            z4.ensure_mount("user")

    def test_timeout_and_failure_accept_concurrent_success(self):
        for result in (subprocess.TimeoutExpired("worker", 45), Mock(returncode=3)):
            with self.subTest(result=result):
                self.verify.side_effect = [False, True]
                self.run.side_effect = [result]
                self.assertEqual(z4.ensure_mount("user"), str(z4.MOUNT))

    def test_failed_mount_redacts_worker_output(self):
        self.run.return_value = Mock(returncode=2, stdout="secret", stderr="secret")
        with self.assertRaises(z4.ConnectionFailure) as caught:
            z4.ensure_mount("user")
        self.assertNotIn("secret", str(caught.exception))


class CredentialAndSourceTests(unittest.TestCase):
    def test_account_comes_from_metadata(self):
        with patch.object(z4.subprocess, "run", return_value=Mock(
                returncode=0, stdout='    "acct"<blob>="saved-user"')) as run:
            self.assertEqual(z4.read_account(), "saved-user")
            self.assertNotIn("-w", run.call_args.args[0])

    def test_wrong_source_and_symlink_are_rejected(self):
        valid = f"//user@{z4.HOST}/{z4.SHARE} on {z4.MOUNT} (smbfs, nodev)\n"
        with patch.object(z4.subprocess, "run") as run, \
                patch.object(z4.os.path, "ismount", return_value=True), \
                patch.object(z4.Path, "is_symlink", return_value=False) as symlink:
            run.return_value = Mock(returncode=0, stdout=valid)
            self.assertTrue(z4.verify_mount("user"))
            self.assertFalse(z4.verify_mount("different-user"))
            run.return_value.stdout = valid.replace(z4.HOST, "192.0.2.1")
            self.assertFalse(z4.verify_mount("user"))
            run.return_value.stdout = valid
            symlink.return_value = True
            self.assertFalse(z4.verify_mount("user"))

    def test_worker_authentication_failure_does_not_mount_or_print_secret(self):
        with patch.object(mount_worker.sys, "stdin", io.StringIO('{"nas_user":"user"}')), \
                patch.object(mount_worker, "read_password", side_effect=RuntimeError("secret")), \
                patch.object(mount_worker, "mount_share") as mount, \
                patch("sys.stdout", new_callable=io.StringIO) as output:
            self.assertEqual(mount_worker.main(), 2)
            mount.assert_not_called()
            self.assertEqual(output.getvalue(), "")


class SSHOutputTests(unittest.TestCase):
    def test_buffered_output_without_newline_and_exit_status_are_preserved(self):
        helper = z4.SCRIPTS / "ssh.exp"
        # Replace credential access and SSH only in this isolated Tcl process.
        # The real helper must handle output arriving in the readiness packet.
        wrapper = """
set argv [list host 10000 account service 5 0 command]
set argc 7
rename exec original_exec
proc exec {args} {return "fake-password"}
rename spawn original_spawn
proc spawn {args} {
    global spawn_id
    original_spawn -noecho /bin/sh -c {printf '__Z4_COMMAND_READY__\\nno-newline'; exit 7}
}
source {%s}
""" % helper
        result = subprocess.run(["/usr/bin/expect"], input=wrapper,
                                capture_output=True, text=True, timeout=10)
        self.assertEqual((result.returncode, result.stdout, result.stderr), (7, "no-newline", ""))


if __name__ == "__main__":
    unittest.main()
