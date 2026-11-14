#!/usr/bin/env python3
"""在临时仓库中验证升级工具，不修改真实框架、数据或分支。"""

import importlib.util
import hashlib
import json
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

    def test_effective_config_checks_dynamic_keys_and_missing_keys(self):
        (self.repo / "config.py").write_text("globals().update({'setting': True})\n")
        result = self.cli("verify", "--effective-config")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        (self.repo / "config.py").write_text("globals().update({'renamed': True})\n")
        result = self.cli("verify", "--effective-config")
        self.assertEqual(result.returncode, 1, result.stdout)
        self.assertIn("setting", result.stdout)

    def test_selection_position_layout_is_opt_in_and_checks_actual_presence(self):
        (self.repo / "config.py").write_text(
            "setting=True\nstrategy_config={'name': 'Fixed'}\nstrategy_pool=[{}]\n")
        self.git("add", "config.py")
        self.git("commit", "-m", "official position template")
        (self.repo / "config.py").write_text("globals().update({'setting': True, 'strategy_list': [{}]})\n")
        flat = self.cli("verify", "--effective-config")
        self.assertEqual(flat.returncode, 1)
        select = self.cli("verify", "--effective-config", "--config-layout", "selection-position")
        self.assertEqual(select.returncode, 0, select.stdout + select.stderr)
        for value in ("[]", "[{}]"):
            (self.repo / "config.py").write_text(
                f"setting=True\nstrategy_list={value}\nstrategy_config={{'name':'Fixed'}}\nstrategy_pool=[{{}}]\n")
            result = self.cli("verify", "--effective-config", "--config-layout", "selection-position")
            self.assertEqual(result.returncode, 1, result.stdout)

    def test_static_stock_config_still_requires_all_keys(self):
        (self.repo / "config.py").write_text("setting=True\nstock_timing_list=[]\n")
        self.git("add", "config.py")
        self.git("commit", "-m", "stock config")
        (self.repo / "config.py").write_text("setting=True\n")
        for args in (("--no-import",), ("--effective-config",)):
            result = self.cli("verify", *args)
            self.assertEqual(result.returncode, 1)
            self.assertIn("stock_timing_list", result.stdout)

    def test_no_import_never_executes_dynamic_config(self):
        (self.repo / "config.py").write_text("raise RuntimeError('must not execute')\n")
        result = self.cli("verify", "--no-import", "--effective-config")
        self.assertEqual(result.returncode, 2)
        self.assertNotIn("must not execute", result.stdout)

    def test_import_writes_stay_in_disposable_copy(self):
        (self.repo / "core").mkdir()
        (self.repo / "core/writer.py").write_text(
            "from pathlib import Path\nPath('generated.txt').write_text('probe')\n"
            "Path(__file__).with_name('generated.py').write_text('value=1')\n")
        result = self.cli("verify", "--effective-config")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertFalse((self.repo / "generated.txt").exists())
        self.assertFalse((self.repo / "core/generated.py").exists())

    def test_import_network_is_blocked(self):
        (self.repo / "core").mkdir()
        (self.repo / "core/network.py").write_text(
            "import socket\nsocket.create_connection(('example.invalid', 80))\n")
        result = self.cli("verify")
        self.assertEqual(result.returncode, 1)
        self.assertIn("does not allow network", result.stdout)

    def policy(self, path, **extra):
        file = self.root / 'policy.json'
        file.write_text(json.dumps({'skip_imports': [dict(path=path,
            sha256=hashlib.sha256((self.repo / path).read_bytes()).hexdigest(),
            reason='reviewed existing archive', **extra)]}))
        return file

    def test_only_exact_unchanged_archive_is_excluded(self):
        archive = self.repo / 'strategy/archive'
        archive.mkdir(parents=True)
        (archive / 'old.py').write_text("raise RuntimeError('expected legacy block')\n")
        policy = self.policy('strategy/archive/old.py')
        result = self.cli('verify', '--import-policy', policy)
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertIn('已登记跳过', result.stdout)
        (archive / 'new.py').write_text("raise RuntimeError('new regression')\n")
        self.assertEqual(self.cli('verify', '--import-policy', policy).returncode, 1)
        (archive / 'old.py').write_text('changed = True\n')
        self.assertEqual(self.cli('verify', '--import-policy', policy).returncode, 2)

    def test_core_and_config_cannot_be_excluded(self):
        policy = self.policy('config.py')
        self.assertEqual(self.cli('verify', '--import-policy', policy).returncode, 2)

    def test_valid_profiles_use_loader_not_raw_import(self):
        (self.repo / 'configlib').mkdir()
        (self.repo / 'configlib/profile.py').write_text("raise RuntimeError('not a raw module')\n")
        (self.repo / 'configlib/loader.py').write_text(
            "def load_profile(path):\n    assert path == 'configlib/profile.py'\n    return {'setting':True}\n")
        policy = self.policy('configlib/profile.py', loader='configlib.loader:load_profile')
        result = self.cli('verify', '--import-policy', policy)
        self.assertEqual(result.returncode, 0, result.stdout)
        (self.repo / 'configlib/loader.py').write_text("def load_profile(path):\n    raise RuntimeError('new profile failure')\n")
        result = self.cli('verify', '--import-policy', policy)
        self.assertEqual(result.returncode, 1)
        self.assertIn('new profile failure', result.stdout)

    def test_tracked_reference_data_and_ignored_runtime_are_partitioned_per_file(self):
        tracked = self.repo / 'data/tracked.csv'
        tracked.write_text('old official')
        self.git('add', '-f', 'data/tracked.csv')
        self.git('commit', '-m', 'official reference data')
        (self.package / 'data/tracked.csv').write_text('new official')
        result = self.cli('scout', '--package', self.package, '--json')
        inventory = json.loads(result.stdout)
        self.assertNotIn('data/tracked.csv', inventory['official_runtime_files'])
        self.assertIn('data/runtime.txt', inventory['official_runtime_files'])
        result = self.cli('apply_official', '--package', self.package)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(tracked.read_text(), 'new official')
        self.assertIn('data/tracked.csv', self.git('diff', '--cached', '--name-only'))
        self.assertEqual((self.repo / 'data/runtime.txt').read_text(), 'USER DATA')

    def test_dependency_workflow_detects_requirements_and_uv_lock(self):
        (self.repo / 'requirements.txt').write_text('meta-package\n')
        (self.repo / 'requirements-local.txt').write_text('-r requirements.txt\n')
        def workflow():
            r = self.cli('scout', '--package', self.package, '--json')
            return json.loads(r.stdout)['dependency_workflow']
        self.assertEqual(workflow(), {'kind':'requirements', 'file':'requirements-local.txt'})
        (self.repo / 'pyproject.toml').write_text('[project]\nname="test"\nversion="1"\n')
        (self.repo / 'uv.lock').write_text('version = 1\n')
        self.assertEqual(workflow()['kind'], 'uv-lock')

    def test_migration_policy_uses_reviewed_fingerprints_and_keeps_profile_loader(self):
        policy_tool = load_script('migration_policy')
        path = self.repo / 'profile.py'
        path.write_text('setting=True\n')
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        manifest = {'assets': [{'path':'profile.py', 'destination_sha256':digest}],
                    'profiles':[{'path':'profile.py','status':'validated_config'}]}
        policy = policy_tool.build_policy(self.repo, manifest, {}, 'loader:load', 'pre')
        self.assertEqual(policy['skip_imports'][0]['loader'], 'loader:load')
        path.write_text('setting=False\n')
        with self.assertRaisesRegex(ValueError, 'fingerprint'):
            policy_tool.build_policy(self.repo, manifest, {}, 'loader:load', 'pre')

    def test_examples_are_static_only_but_new_normal_module_failure_is_not_hidden(self):
        sample = self.repo / 'configlib/examples'
        sample.mkdir(parents=True)
        (sample / 'post.py').write_text("raise RuntimeError('not a library entry')\n")
        self.assertEqual(self.cli('verify').returncode, 0)
        (self.repo / 'configlib/new.py').write_text("raise RuntimeError('real failure')\n")
        result = self.cli('verify')
        self.assertEqual(result.returncode, 1)
        self.assertIn('real failure', result.stdout)

    def test_apply_dry_run_leaves_index_code_and_data_untouched(self):
        result = self.cli('apply_official', '--package', self.package, '--dry-run')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assert_unmodified()

    def test_new_official_ignore_cannot_prevent_staging_explicit_official_code(self):
        (self.package / '.gitignore').write_text('data/\nnew_code.py\n')
        (self.package / 'new_code.py').write_text('setting=True\n')
        result = self.cli('apply_official', '--package', self.package)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('new_code.py', self.git('diff', '--cached', '--name-only'))


if __name__ == "__main__":
    unittest.main()
