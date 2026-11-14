"""Host root and executable/option boundaries for agent-invoked CLIs."""
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from cli_paths import allowed_path, executable, model_name
from goose_import import import_session
from verification_report import load_report


class CliPathsTests(unittest.TestCase):
    def test_import_and_report_reject_unapproved_files_before_reading_them(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d) / "approved"; root.mkdir()
            outside = Path(d) / "private.json"; outside.write_text("not even JSON")
            with patch.dict(os.environ, {"CLAIMTRAIL_ALLOWED_ROOT": str(root)}):
                for reader in [import_session, load_report]:
                    with self.subTest(reader=reader.__name__), self.assertRaisesRegex(ValueError, "host-approved"):
                        reader(outside)
    def test_paths_cannot_escape_host_root_through_absolute_relative_or_symlink_paths(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d) / "approved"; root.mkdir()
            outside = Path(d) / "outside"; outside.mkdir()
            (root / "link").symlink_to(outside, target_is_directory=True)
            with patch.dict(os.environ, {"CLAIMTRAIL_ALLOWED_ROOT": str(root)}):
                self.assertEqual(allowed_path(root / "new.json"), root.resolve() / "new.json")
                for path in [outside / "secret.json", root / "../outside/x", root / "link/x"]:
                    with self.subTest(path=path), self.assertRaisesRegex(ValueError, "host-approved"):
                        allowed_path(path)

    def test_executable_and_model_arguments_are_not_options_or_arbitrary_commands(self):
        self.assertEqual(executable(sys.executable, "python"), str(Path(sys.executable).absolute()))
        for value in ["--help", "sh", "python3; echo unexpected", "not-installed-claimtrail"]:
            with self.subTest(value=value), self.assertRaises(ValueError): executable(value, "python")
        self.assertEqual(model_name("qwen3:8b"), "qwen3:8b")
        for value in ["--recipe", "qwen3 --no-session", "", "qwen3;echo"]:
            with self.subTest(value=value), self.assertRaises(ValueError): model_name(value)
