#!/usr/bin/env python3
"""在临时仓库中验证升级工具，不修改真实框架、数据或分支。"""

import importlib.util
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import venv


SCRIPTS = Path(__file__).resolve().parent


def load_script(name):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


apply = load_script("apply_official")
verify = load_script("verify")


class UpgradeToolsTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="quant-upgrade-test-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.repo = self.root / "repo"
        self.repo.mkdir()
        self.git("init", "-b", "main")
        self.git("config", "user.name", "Upgrade Test")
        self.git("config", "user.email", "test@example.invalid")
        self.git("config", "commit.gpgsign", "false")
        (self.repo / ".gitignore").write_text("data/\n__pycache__/\n.venv/\n")
        (self.repo / "config.py").write_text("setting = True\n")
        (self.repo / "notes.md").write_text("baseline\n")
        (self.repo / "obsolete").mkdir()
        (self.repo / "obsolete" / "old.py").write_text("value = 1\n")
        self.git("add", ".")
        self.git("commit", "-m", "baseline")
        self.git("tag", "pre")
        (self.repo / "data" / "user-empty").mkdir(parents=True)
        (self.repo / "data" / "runtime.txt").write_text("USER DATA")
        self.package = self.root / "package"
        (self.package / "data").mkdir(parents=True)
        (self.package / "config.py").write_text("setting = False\n")
        (self.package / "notes.md").write_text("official\n")
        (self.package / "data" / "runtime.txt").write_text("OFFICIAL DATA")

    def git(self, *args):
        return subprocess.run(
            ["git", "-C", str(self.repo), *args], check=True, capture_output=True, text=True
        ).stdout.strip()

    def cli(self, script, *args):
        return subprocess.run(
            [sys.executable, str(SCRIPTS / f"{script}.py"), "--repo", str(self.repo), *map(str, args)],
            capture_output=True,
            text=True,
            timeout=30,
        )

    def apply_args(self, *args):
        return ("--package", self.package, "--runtime-data", "copy", *args)

    def assert_unmodified(self):
        self.assertEqual((self.repo / "config.py").read_text(), "setting = True\n")
        self.assertEqual((self.repo / "data" / "runtime.txt").read_text(), "USER DATA")
        self.assertEqual(self.git("status", "--porcelain"), "")

    def test_copy_requires_backup_before_mutation(self):
        result = self.cli("apply_official", *self.apply_args())
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assert_unmodified()

    def test_copy_rejects_unsafe_or_existing_backups(self):
        existing = self.root / "backup"
        existing.mkdir()
        (existing / "saved.txt").write_text("PREVIOUS BACKUP")
        for backup in (existing, self.repo / "backup", self.package / "backup"):
            with self.subTest(backup=backup):
                result = self.cli("apply_official", *self.apply_args("--backup-dir", backup))
                self.assertEqual(result.returncode, 2, result.stderr)
                self.assert_unmodified()
        self.assertEqual((existing / "saved.txt").read_text(), "PREVIOUS BACKUP")

    def test_copy_backs_up_original_and_leaves_unrelated_empty_directory(self):
        backup = self.root / "backup"
        result = self.cli("apply_official", *self.apply_args("--backup-dir", backup))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual((backup / "data" / "runtime.txt").read_text(), "USER DATA")
        self.assertEqual((self.repo / "data" / "runtime.txt").read_text(), "OFFICIAL DATA")
        self.assertTrue((self.repo / "data" / "user-empty").is_dir())
        self.assertFalse((self.repo / "obsolete").exists())
        self.assertNotIn("data/", self.git("diff", "--cached", "--name-only"))

    def test_backup_failure_prevents_code_and_data_replacement(self):
        argv = [
            "apply_official.py",
            "--repo",
            str(self.repo),
            *map(str, self.apply_args("--backup-dir", self.root / "backup")),
        ]
        with patch.object(sys, "argv", argv), patch.object(apply.shutil, "copy2", side_effect=OSError("backup failed")):
            with self.assertRaisesRegex(OSError, "backup failed"):
                apply.main()
        self.assert_unmodified()

    def test_config_keys_exclude_function_and_class_scopes(self):
        source = """global_key = 1
if enabled:
    condition_key = 2
def helper():
    function_local = 3
async def async_helper():
    async_local = 4
class Example:
    class_local = 5
"""
        keys = verify.config_assignments(source)
        self.assertEqual(set(keys), {"global_key", "condition_key"})
        self.assertTrue(keys["global_key"][3])
        self.assertFalse(keys["condition_key"][3])

    def test_since_includes_committed_staged_unstaged_and_new_files(self):
        (self.repo / "notes.md").write_text("committed\n")
        self.git("add", "notes.md")
        self.git("commit", "-m", "earlier change")
        (self.repo / "config.py").write_text("setting = True\npath = '/Users/xxxx/data'\n")
        self.git("add", "config.py")
        (self.repo / "obsolete" / "old.py").write_text("value = 2\n")
        (self.repo / "new.txt").write_text("/Users/xxxx/new\n")
        scope = verify.merge_changed_files(self.repo, "pre")
        self.assertEqual(set(scope), {"config.py", "notes.md", "obsolete/old.py", "new.txt"})
        result = self.cli("verify", "--since", "pre", "--no-import")
        self.assertEqual(result.returncode, 1, result.stdout)
        self.assertIn("config.py:", result.stdout)
        self.assertIn("new.txt:", result.stdout)

    def test_pending_merge_is_scanned_before_commit(self):
        self.git("checkout", "-b", "dev")
        (self.repo / "notes.md").write_text("local\n")
        self.git("add", "notes.md")
        self.git("commit", "-m", "local change")
        self.git("checkout", "main")
        (self.repo / "config.py").write_text("setting = True\npath = '/Users/xxxx/new'\n")
        self.git("add", "config.py")
        self.git("commit", "-m", "official change")
        self.git("checkout", "dev")
        self.git("merge", "--no-commit", "--no-ff", "main")
        self.assertEqual(verify.merge_changed_files(self.repo, None), ["config.py"])
        result = self.cli("verify", "--no-import")
        self.assertEqual(result.returncode, 1, result.stdout)
        self.assertIn("config.py:", result.stdout)

    def test_empty_diff_stays_empty_and_invalid_ref_fails(self):
        self.assertEqual(verify.merge_changed_files(self.repo, "HEAD"), [])
        result = self.cli("verify", "--since", "nonexistent-ref", "--no-import")
        self.assertEqual(result.returncode, 2, result.stderr)

    def test_nested_custom_modules_are_imported(self):
        nested = self.repo / "configlib" / "nested"
        nested.mkdir(parents=True)
        (nested / "broken.py").write_text("raise RuntimeError('nested failure')\n")
        result = self.cli("verify")
        self.assertEqual(result.returncode, 1, result.stdout)
        self.assertIn("nested/broken.py: RuntimeError: nested failure", result.stdout)

    def test_missing_official_key_fails_even_when_import_succeeds(self):
        (self.repo / "config.py").write_text("setting = True\nuse_flow = True\n")
        self.git("add", "config.py")
        self.git("commit", "-m", "official config key")
        (self.repo / "config.py").write_text("setting = True\n")
        flows = self.repo / "capital_flows"
        flows.mkdir()
        (flows / "Fixed.py").write_text("import config\ndef get_flow():\n    return config.use_flow\n")
        for args in ((), ("--no-import",)):
            with self.subTest(args=args):
                result = self.cli("verify", *args)
                self.assertEqual(result.returncode, 1, result.stdout)
                self.assertIn("use_flow", result.stdout)

    def test_missing_dependency_fails_unless_explicitly_allowed(self):
        name = "quant_upgrade_missing_dependency_for_test"
        (self.repo / "core").mkdir()
        (self.repo / "core" / "required.py").write_text(f"import {name}\n")
        result = self.cli("verify")
        self.assertEqual(result.returncode, 1, result.stdout)
        allowed = self.cli("verify", "--allow-missing-dependency", name)
        self.assertEqual(allowed.returncode, 0, allowed.stdout)
        self.assertIn("已明确放行的既有可选依赖", allowed.stdout)

    def test_default_venv_is_used_for_validation(self):
        env = self.repo / ".venv"
        venv.EnvBuilder(with_pip=False, symlinks=True).create(env)
        (self.repo / "config.py").write_text(
            f"import sys\nfrom pathlib import Path\nassert Path(sys.prefix).resolve() == Path({str(env)!r}).resolve()\nsetting = True\n"
        )
        result = self.cli("verify")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("core: 1 ok", result.stdout)


if __name__ == "__main__":
    unittest.main()
