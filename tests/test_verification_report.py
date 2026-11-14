"""Offline report replay, pinned Goose messages and read-only HTTP boundaries."""
import hashlib
import http.client
import json
import sys
import tempfile
import threading
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from review_app import Handler, ReviewServer
from scope_verification import observe, policy, run_check, write_json
from verification_report import load_report


class VerificationReportTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        (self.root / "source.py").write_text("VALUE=1\n")
        spec = policy({"check_id": "example", "scope": ["source.py"], "command": [sys.executable, "-c", "pass"]})
        receipt = run_check(self.root, spec)
        self.case = {"id": "repo/fresh", "repository": "repo", "scenario": "fresh", "kind": "test fixture", "expected": "verified",
                     "note": "Invented unit-test record", "policy": spec, "receipt": receipt,
                     "observation": observe(self.root, spec, receipt), "baseline_rerun": None}
        self.path = self.root / "report.json"
        self.report = {"schema": "claimtrail.verification-report.v1", "repositories": [{"id": "repo", "revision": "invented"}],
                       "limits": ["Invented unit-test case"], "cases": [self.case]}

    def tearDown(self): self.temp.cleanup()

    def test_replay_recalculates_status_and_does_not_trust_cached_result(self):
        self.case["result"] = {"status": "stale"}
        write_json(self.path, self.report)
        actual, _ = load_report(self.path)
        self.assertEqual(actual["cases"][0]["result"]["status"], "verified")
        self.case["receipt"]["execution"]["exit_code"] = 1
        write_json(self.path, self.report)
        with self.assertRaises(ValueError): load_report(self.path)

    def test_goose_message_and_export_hash_must_match_pinned_source(self):
        session = self.root / "session.json"
        message = {"id": "m1", "role": "assistant", "created": 1, "content": [{"type": "text", "text": "Example claim"}]}
        write_json(session, {"conversation": [message]})
        self.case["goose_claim"] = {"session_file": "session.json", "session_sha256": hashlib.sha256(session.read_bytes()).hexdigest(),
            "message_index": 0, "message_id": "m1", "text": "Example claim", "created": 1}
        write_json(self.path, self.report)
        self.assertEqual(load_report(self.path)[1], {"session.json": session})
        self.case["goose_claim"]["text"] = "Changed claim"
        write_json(self.path, self.report)
        with self.assertRaisesRegex(ValueError, "claim differs"): load_report(self.path)
        self.case["goose_claim"]["text"] = "Example claim"
        session.write_text("changed")
        with self.assertRaisesRegex(ValueError, "source changed"): load_report(self.path)
        self.case["goose_claim"]["session_file"] = "../elsewhere.json"
        write_json(self.path, self.report)
        with self.assertRaisesRegex(ValueError, "inside"): load_report(self.path)

    def test_http_read_only_report_and_changed_source_protection(self):
        write_json(self.path, self.report)
        server = ReviewServer(("127.0.0.1", 0), Handler, None, None, self.root / "unused-labels.json", verification_report=self.path)
        thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
        def request(path, method="GET", host=None):
            c = http.client.HTTPConnection("127.0.0.1", server.server_port)
            c.request(method, path, headers={"Host": host or f"127.0.0.1:{server.server_port}"})
            r = c.getresponse(); data = r.read(); c.close(); return r.status, data
        try:
            self.assertEqual(request("/")[0], 200)
            status, data = request("/api/verification")
            self.assertEqual(status, 200)
            self.assertEqual(json.loads(data)["matching_cases"], 1)
            self.assertEqual(request("/api/review/x", "POST")[0], 405)
            self.assertEqual(request("/api/verification", host="evil.invalid")[0], 403)
            self.assertEqual(request("/../LICENSE")[0], 404)
            self.path.write_text(self.path.read_text() + " ")
            self.assertEqual(request("/api/verification")[0], 409)
            self.assertFalse((self.root / "unused-labels.json").exists())
        finally:
            server.shutdown(); server.server_close(); thread.join()

    def test_recorded_real_repo_cases_and_goose_tool_pins_replay_offline(self):
        path = Path(__file__).resolve().parents[1] / "examples/verification/recorded/report.json"
        report, sources = load_report(path)
        self.assertEqual(report["matching_cases"], 36)
        self.assertEqual(report["replayed_cases"], 36)
        self.assertEqual({c["repository"] for c in report["cases"]}, {"more-itertools", "itsdangerous"})
        goose = [c for c in report["cases"] if c.get("goose_claim")]
        self.assertEqual(len(goose), 6)
        self.assertEqual(len(sources), 6)
        self.assertTrue(all(c.get("tool_observation") and c.get("goose_tool_call_id") for c in goose))


if __name__ == "__main__": unittest.main()
