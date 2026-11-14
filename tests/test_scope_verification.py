"""Deterministic receipt contract, invalidation, and fail-closed boundary checks."""
import copy
import json
import os
import subprocess
import sys
import tempfile
import unittest
from datetime import timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from scope_verification import (at, changed, digest, observe, policy, run_check, seal,
                                snapshot, verify, write_json)


class ScopeVerificationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name) / "repo"
        self.root.mkdir()
        (self.root / "src").mkdir()
        (self.root / "src/a.py").write_text("VALUE = 1\n")
        (self.root / "tests.py").write_text("assert True\n")
        (self.root / "config.json").write_text("{}\n")
        self.spec = policy({"check_id": "unit", "command": [sys.executable, "-B", "tests.py"],
                            "scope": ["src", "tests.py", "config.json"], "exclude": ["src/__pycache__"]})

    def tearDown(self):
        self.temp.cleanup()

    def verdict(self, receipt=None, spec=None):
        spec = spec or self.spec
        receipt = receipt or run_check(self.root, spec)
        return verify(spec, receipt, observe(self.root, spec, receipt))

    def test_fresh_and_content_restoration_with_timestamps_ignored(self):
        receipt = run_check(self.root, self.spec)
        self.assertEqual(self.verdict(receipt)["status"], "verified")
        file = self.root / "src/a.py"
        file.write_text("VALUE = 2\n")
        self.assertEqual(self.verdict(receipt)["changed_paths"], ["src/a.py"])
        file.write_text("VALUE = 1\n")
        self.assertEqual(self.verdict(receipt)["status"], "verified")
        self.assertEqual(receipt["execution"]["exit_code"], 0)

    def test_source_test_config_add_delete_rename_and_mode_changes(self):
        for kind in ["source", "tests", "config", "add", "delete", "rename", "mode"]:
            with self.subTest(kind=kind):
                saved = {str(p.relative_to(self.root)): (p.read_bytes(), p.stat().st_mode) for p in self.root.rglob("*") if p.is_file()}
                receipt = run_check(self.root, self.spec)
                file = self.root / "src/a.py"
                if kind in {"source", "tests", "config"}:
                    target = {"source": file, "tests": self.root / "tests.py", "config": self.root / "config.json"}[kind]
                    target.write_text(target.read_text() + "\n")
                elif kind == "add":
                    (self.root / "src/new.py").write_text("UNTRACKED = True\n")
                elif kind == "delete":
                    file.unlink()
                elif kind == "rename":
                    file.rename(self.root / "src/moved.py")
                else:
                    file.chmod(0o755)
                verdict = self.verdict(receipt)
                self.assertEqual(verdict["status"], "stale")
                self.assertTrue(verdict["changed_paths"])
                for p in self.root.rglob("*"):
                    if p.is_file(): p.unlink()
                for name, (data, mode) in saved.items():
                    path = self.root / name
                    path.write_bytes(data); path.chmod(mode)

    def test_exclusions_and_out_of_scope_changes_are_explicit(self):
        receipt = run_check(self.root, self.spec)
        (self.root / "src/__pycache__").mkdir()
        (self.root / "src/__pycache__/a.pyc").write_bytes(b"cache")
        (self.root / "README.md").write_text("outside this contract")
        self.assertEqual(self.verdict(receipt)["status"], "verified")
        self.assertEqual(receipt["policy"]["exclude"], ["src/__pycache__"])

    def test_policy_command_scope_environment_and_id_mismatch(self):
        receipt = run_check(self.root, self.spec)
        for field, value in [("scope", ["src"]), ("command", [sys.executable, "-c", "pass"]),
                             ("env", {"TEST_MODE": "different"}), ("check_id", "different")]:
            with self.subTest(field=field):
                spec = policy({**self.spec, field: value})
                self.assertEqual(self.verdict(receipt, spec)["status"], "scope_mismatch")

    def test_mutation_during_check_cannot_be_pinned_as_a_pass(self):
        spec = policy({**self.spec, "command": [sys.executable, "-c",
                      "from pathlib import Path; Path('src/a.py').write_text('VALUE = 2\\n')"]})
        self.assertEqual(self.verdict(spec=spec)["status"], "changed_during_check")

    def test_failure_timeout_and_launch_error_never_verify(self):
        for command, limit, expected in [([sys.executable, "-c", "raise SystemExit(3)"], 2, "failed"),
                ([sys.executable, "-c", "import time; time.sleep(5)"], .03, "timeout"),
                ([str(self.root / "absent-executable")], 2, "unresolved")]:
            with self.subTest(expected=expected):
                self.assertEqual(self.verdict(spec=policy({**self.spec, "command": command, "timeout_seconds": limit}))["status"], expected)

    def test_later_check_missing_receipt_and_wrong_workspace(self):
        earlier = observe(self.root, self.spec, None)
        self.assertEqual(verify(self.spec, None, earlier)["status"], "missing")
        receipt = run_check(self.root, self.spec)
        earlier = seal({**earlier, "receipt_sha256": receipt["sha256"]})
        self.assertEqual(verify(self.spec, receipt, earlier)["status"], "later")
        other = self.root.parent / "other"; other.mkdir()
        for name in ["src", "tests.py", "config.json"]:
            path = other / name
            if name == "src": path.mkdir()
            else: path.write_text("pass\n")
        self.assertEqual(verify(self.spec, receipt, observe(other, self.spec, receipt))["status"], "workspace_mismatch")

    def test_altered_records_bad_digest_and_replaced_receipt_rejected(self):
        receipt = run_check(self.root, self.spec)
        observation = observe(self.root, self.spec, receipt)
        bad = copy.deepcopy(receipt); bad["execution"]["exit_code"] = 99
        with self.assertRaises(ValueError): verify(self.spec, bad, observation)
        bad = copy.deepcopy(observation); bad["snapshot"]["files"][0]["sha256"] = "a" * 64
        bad = seal(bad)
        with self.assertRaises(ValueError): verify(self.spec, receipt, bad)
        replacement = run_check(self.root, self.spec)
        with self.assertRaises(ValueError): verify(self.spec, replacement, observation)
        wrong = policy({**self.spec, "check_id": "different"})
        with self.assertRaises(ValueError): verify(wrong, receipt, observation)

    def test_rejects_scope_escape_symlinks_special_files_and_invalid_policy(self):
        for name in ["../outside", "/absolute", "src/../tests.py", "src/*", "src/./a.py", ".git/config"]:
            with self.subTest(name=name), self.assertRaises(ValueError): policy({**self.spec, "scope": [name]})
        for update in [{"command": "echo pass"}, {"timeout_seconds": True}, {"timeout_seconds": float("nan")},
                       {"exclude": ["src"]}, {"unexpected": True}]:
            with self.subTest(update=update), self.assertRaises(ValueError): policy({**self.spec, **update})
        (self.root / "src/link").symlink_to(self.root / "tests.py")
        with self.assertRaisesRegex(ValueError, "symlink"): snapshot(self.root, self.spec)
        (self.root / "src/link").unlink()
        (self.root / "alias").symlink_to(self.root / "src", target_is_directory=True)
        with self.assertRaisesRegex(ValueError, "symlink"): snapshot(self.root, policy({**self.spec, "scope": ["alias/a.py"]}))
        if hasattr(os, "mkfifo"):
            os.mkfifo(self.root / "src/fifo")
            with self.assertRaisesRegex(ValueError, "non-regular"): snapshot(self.root, self.spec)

    def test_cli_exit_codes_receipt_round_trip_and_source_destination_guards(self):
        directory = self.root.parent
        spec_path, receipt, observation = [directory / (s + ".json") for s in ["policy", "receipt", "observation"]]
        write_json(spec_path, self.spec)
        command = [sys.executable, "-B", str(Path(__file__).resolve().parents[1] / "src/scope_verification.py"),
                   "run", "--repo", str(self.root), "--policy", str(spec_path), "--receipt", str(receipt),
                   "--observation", str(observation)]
        result = subprocess.run(command, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertEqual(verify(self.spec, json.loads(receipt.read_text()), json.loads(observation.read_text()))["status"], "verified")
        (self.root / "src/a.py").write_text("changed\n")
        command[3] = "verify"
        self.assertEqual(subprocess.run(command, capture_output=True).returncode, 1)
        command[command.index("--receipt") + 1] = str(spec_path)
        self.assertEqual(subprocess.run(command, capture_output=True).returncode, 2)
        self.assertEqual(json.loads(spec_path.read_text()), self.spec)


if __name__ == "__main__":
    unittest.main()
