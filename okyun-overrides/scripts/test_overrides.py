"""Isolated fixtures only: no real OKyun writes, UI actions, or process control."""
import copy
import importlib.util
import json
from pathlib import Path
import plistlib
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import uuid

spec = importlib.util.spec_from_file_location("overrides", Path(__file__).with_name("overrides.py"))
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
OLD = 'const main = (config) => { config.rules = ["MATCH,🚀 节点选择"]; return config; };\n'
NEW = OLD.replace('"MATCH', '"DOMAIN-SUFFIX,example.org,💬 OpenAi", "MATCH')


class OverrideTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.config = {
            "currentProfileId": "active",
            "profiles": [
                {"id": "other", "overwrite": {"type": "standard"}},
                {"id": "active", "overwrite": {"type": "script", "scriptOverwrite": {"scriptId": "chosen"}}, "selectedMap": {"💬 OpenAi": "🇸🇬 狮城节点"}, "url": "fixture-private-url"},
            ],
            "scripts": [{"id": "inactive", "label": "other", "content": "unrelated"}, {"id": "chosen", "label": "fixture", "content": OLD}],
            "patchClashConfig": {"dns": {"ipv6": False}, "tun": {"enable": True}},
            "unrelated": "preserve newer values",
        }
        self.initial = copy.deepcopy(self.config)
        self.pref_patch = patch.object(m, "read_preferences", side_effect=self.read_fixture)
        self.pref_patch.start()
        self.root_patch = patch.object(m, "STAGE_ROOT", self.root / "changes")
        self.root_patch.start()

    def tearDown(self):
        self.root_patch.stop()
        self.pref_patch.stop()
        self.temp.cleanup()

    def read_fixture(self):
        raw = plistlib.dumps({m.KEY: json.dumps(self.config), "otherPreference": "fixture"})
        return raw, copy.deepcopy(self.config)

    def staged(self):
        source = self.root / "edit.js"
        m.main(["export", str(source)])
        source.write_text(NEW, encoding="utf-8")
        return Path(m.main(["stage", str(source)])["stage"])

    def test_export_stage_preserve_live_state_and_unicode(self):
        folder = self.staged()
        self.assertEqual(self.config, self.initial)
        self.assertEqual((folder / "original.js").read_text(), OLD)
        self.assertEqual((folder / "override.js").read_text(), NEW)
        self.assertEqual(folder.stat().st_mode & 0o777, 0o700)
        self.assertEqual((folder / "override.js").stat().st_mode & 0o777, 0o600)
        self.assertTrue(m.main(["check", str(folder)])["ready_for_ui_save"])

    def test_export_refuses_existing_files(self):
        path = self.root / "existing.js"
        path.write_text("keep")
        with self.assertRaises(ValueError):
            m.main(["export", str(path)])
        self.assertEqual(path.read_text(), "keep")

    def test_change_after_export_is_rejected(self):
        source = self.root / "edit.js"
        m.main(["export", str(source)])
        self.config["scripts"][1]["content"] += "// user edit\n"
        with self.assertRaisesRegex(ValueError, "since export"):
            m.main(["stage", str(source)])

    def test_change_after_stage_is_rejected_by_ui_gate(self):
        folder = self.staged()
        self.config["scripts"][1]["content"] += "// user edit\n"
        with self.assertRaisesRegex(ValueError, "since staging"):
            m.main(["check", str(folder)])

    def test_binding_change_is_rejected(self):
        folder = self.staged()
        self.config["profiles"][1]["overwrite"]["scriptOverwrite"]["scriptId"] = "inactive"
        with self.assertRaisesRegex(ValueError, "binding changed"):
            m.main(["check", str(folder)])

    def test_modified_staged_file_is_rejected(self):
        folder = self.staged()
        (folder / "override.js").write_text(NEW + "// extra\n")
        with self.assertRaisesRegex(ValueError, "Staged source changed"):
            m.main(["check", str(folder)])

    def test_syntax_failure_creates_no_stage(self):
        source = self.root / "edit.js"
        m.main(["export", str(source)])
        source.write_text("const main = ( => invalid")
        with self.assertRaisesRegex(ValueError, "syntax validation failed"):
            m.main(["stage", str(source)])
        self.assertFalse(m.STAGE_ROOT.exists())

    def test_running_app_blocks_apply_before_any_read_or_write(self):
        with patch.object(m, "app_is_running", return_value=True), patch.object(m, "write_config") as write, patch.object(m, "read_preferences") as read:
            with self.assertRaisesRegex(ValueError, "OKyun is running"):
                m.apply_stage(self.root / "nonexistent")
            read.assert_not_called()
            write.assert_not_called()

    def test_offline_apply_is_surgical_and_idempotent(self):
        folder = self.staged()
        self.config["unrelated"] = "changed after staging"
        expected = copy.deepcopy(self.config)
        expected["scripts"][1]["content"] = NEW
        def save(updated):
            self.config = copy.deepcopy(updated)
        with patch.object(m, "app_is_running", return_value=False), patch.object(m, "write_config", side_effect=save) as write:
            self.assertTrue(m.apply_stage(folder)["changed"])
            self.assertEqual(self.config, expected)
            self.assertFalse(m.apply_stage(folder)["changed"])
            self.assertEqual(write.call_count, 1)
        self.assertEqual((folder / "before-apply.plist").stat().st_mode & 0o777, 0o600)
        self.assertTrue(m.main(["verify", str(folder)])["stored_script_matches"])

    def test_reopen_race_blocks_write(self):
        folder = self.staged()
        with patch.object(m, "app_is_running", side_effect=[False, True]), patch.object(m, "write_config") as write:
            with self.assertRaisesRegex(ValueError, "reopened"):
                m.apply_stage(folder)
            write.assert_not_called()

    @unittest.skipUnless(sys.platform == "darwin", "CFPreferences requires macOS")
    def test_native_writer_uses_only_an_isolated_test_domain(self):
        domain = "com.codex.okyun-skill-test." + uuid.uuid4().hex
        try:
            subprocess.run(["/usr/bin/defaults", "write", domain, "sentinel", "-string", "preserve"], check=True)
            self.pref_patch.stop()
            with patch.object(m, "DOMAIN", domain):
                m.write_config(self.config)
                raw, saved = m.read_preferences()
                self.assertEqual(saved, self.config)
                self.assertEqual(plistlib.loads(raw)["sentinel"], "preserve")
        finally:
            self.pref_patch.start()
            subprocess.run(["/usr/bin/defaults", "delete", domain], capture_output=True)


if __name__ == "__main__":
    unittest.main()
