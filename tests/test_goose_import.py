"""Offline import and HTTP regression checks; fixtures here are invented."""

import copy
import http.client
import json
import sys
import tempfile
import threading
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from goose_import import import_session
from review_app import Handler, ReviewServer
from review_provenance import citation_metadata


def fixture():
    def message(role, content):
        return {"role": role, "created": 1700000000, "content": content}

    def request(cid):
        return {"type": "toolRequest", "id": cid, "toolCall": {
            "status": "success", "value": {"name": "shell", "arguments": {"command": "python3 -m unittest -v"}}}}

    def response(cid, code):
        return {"type": "toolResponse", "id": cid, "toolResult": {"status": "success", "value": {
            "resultType": "complete", "isError": code != 0,
            "structuredContent": {"exit_code": code, "stdout": "", "stderr": "FAILED" if code else "OK"},
            "content": [{"type": "text", "text": "FAILED" if code else "OK"}]}}}

    return {"id": "invented-session", "provider_name": "ollama", "model_config": {"model_name": "example"},
            "conversation": [message("assistant", [request("call-1")]),
                message("user", [response("call-1", 1)]),
                message("assistant", [{"type": "thinking", "thinking": "Not evidence"},
                                      {"type": "text", "text": "All tests passed."}]),
                message("assistant", [request("call-2")]), message("user", [response("call-2", 0)]),
                message("assistant", [{"type": "text", "text": "The rerun passed."}])]}


class GooseImportTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / "session.json"

    def tearDown(self):
        self.temp.cleanup()

    def load(self, value=None):
        self.path.write_text(json.dumps(fixture() if value is None else value))
        return import_session(self.path, allowed_root=self.path.parent)

    def test_success_envelope_does_not_hide_process_failure_or_later_verification(self):
        bundle, turns, sessions = self.load()
        self.assertEqual([t["goose"]["process_exit_code"] for t in turns], [1, 0])
        self.assertEqual(turns[0]["error"], "FAILED")
        self.assertEqual(turns[0]["goose"]["result_status"], "success")
        self.assertEqual(len(bundle["episodes"]), 2)
        earlier, later = bundle["episodes"]
        self.assertEqual([e["phase"] for e in earlier["evidence"]], ["before", "after"])
        self.assertEqual([e["phase"] for e in later["evidence"]], ["before", "before"])
        self.assertEqual(earlier["created_at"], turns[1]["created_at"])
        pins = citation_metadata(earlier, {"units": [{"evidence_ids": [turns[1]["id"]]}]},
                                 {t["id"]: t for t in turns}, {s["id"]: s["agent_id"] for s in sessions})
        self.assertEqual(pins[turns[1]["id"]]["phase"], "after")
        self.assertEqual(pins[turns[1]["id"]]["record_offset_seconds"], 0)
        self.assertNotIn("status", earlier["proposed_units"][0])
        self.assertNotIn("Not evidence", earlier["message"])
        self.assertEqual(import_session(self.path, allowed_root=self.path.parent), (bundle, turns, sessions))

    def test_missing_result_stays_unknown_and_orphan_response_has_no_invented_command(self):
        value = fixture()
        value["conversation"].pop(1)
        _, turns, _ = self.load(value)
        self.assertEqual(turns[0]["goose"]["tool_observation"], "No result recorded")
        self.assertIsNone(turns[0]["goose"]["process_exit_code"])
        value = fixture()
        value["conversation"].pop(0)
        _, turns, _ = self.load(value)
        self.assertTrue(turns[0]["goose"]["request_missing"])
        self.assertNotIn("arguments", turns[0]["agent_action"])

    def test_malformed_sources_are_rejected_and_duplicate_ids_are_not_merged(self):
        cases = []
        value = fixture(); value["conversation"].append(copy.deepcopy(value["conversation"][0])); cases.append(value)
        value = fixture(); value["conversation"][0], value["conversation"][1] = value["conversation"][1], value["conversation"][0]; cases.append(value)
        value = fixture(); value["conversation"][0]["created"] = float("nan"); cases.append(value)
        value = fixture(); value["conversation"][0]["content"] = "not an array"; cases.append(value)
        value = fixture(); value["conversation"][1]["content"][0]["toolResult"]["value"]["structuredContent"]["exit_code"] = True; cases.append(value)
        for value in cases:
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.load(value)
        self.path.write_text('{"type":"message"}\n{"type":"complete"}')
        with self.assertRaisesRegex(ValueError, "not a streaming"):
            import_session(self.path, allowed_root=self.path.parent)

    def test_tool_error_nonfinal_result_and_hidden_assistant_text(self):
        value = fixture()
        value["conversation"][1]["content"][0]["toolResult"] = {"status": "error", "value": "denied"}
        value["conversation"][4]["content"][0]["toolResult"]["value"] = {"resultType": "task", "content": []}
        value["conversation"][-1]["metadata"] = {"userVisible": False}
        b, t, _ = self.load(value)
        self.assertEqual(len(b["episodes"]), 1)
        self.assertEqual(t[0]["goose"]["tool_observation"], "Tool returned an error")
        self.assertEqual(t[1]["goose"]["tool_observation"], "Non-final tool response recorded")
        self.assertIsNone(t[1]["goose"]["process_exit_code"])

    def test_goose_http_save_reload_export_search_and_source_change_protection(self):
        self.load()
        labels = self.path.with_name("reviews.json")
        with self.assertRaisesRegex(ValueError, "source export"):
            ReviewServer(("127.0.0.1", 0), Handler, None, None, self.path, goose_session=self.path, allowed_root=self.path.parent)
        server = ReviewServer(("127.0.0.1", 0), Handler, None, None, labels, goose_session=self.path, allowed_root=self.path.parent)
        thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()

        def request(path, payload=None):
            c = http.client.HTTPConnection("127.0.0.1", server.server_port, timeout=5)
            c.request("GET" if payload is None else "POST", path,
                      body=None if payload is None else json.dumps(payload), headers={
                          "Content-Type": "application/json", "Origin": f"http://127.0.0.1:{server.server_port}"})
            r = c.getresponse(); result = r.status, json.loads(r.read()); c.close(); return result

        try:
            _, listing = request("/api/episodes")
            self.assertEqual(listing["mode"], "goose_session")
            self.assertFalse(labels.exists())
            cid = listing["items"][0]["claim_id"]
            _, opened = request("/api/episode/" + cid)
            self.assertEqual([e["phase"] for e in opened["episode"]["evidence"]], ["before", "after"])
            self.assertIn("Process exit code 1", opened["summary"]["before"][0]["text"])
            self.assertIn("Process exit code 0", opened["summary"]["later"][0]["text"])
            later = opened["episode"]["evidence"][1]["turn_id"]
            _, search = request(f"/api/search?episode_id={cid}&q=unittest&scope=claimant&phase=after")
            self.assertEqual([x["turn_id"] for x in search["results"]], [later])
            payload = {"claim_id": cid, "base_revision": None, "units": [{"unit_id": "u1",
                       "text": "Tests passed", "status": "unresolved", "evidence_ids": [later], "notes": "Later evidence"}]}
            code, saved = request("/api/review/" + cid, payload)
            self.assertEqual(code, 200, saved)
            self.assertEqual(request("/api/review/" + cid, payload)[0], 409)
            _, exported = request("/api/export")
            self.assertEqual(exported[cid]["data_mode"], "goose_session")
            self.assertFalse(exported[cid]["assessment_policy"]["independent_human_validation"])
            self.assertEqual(exported[cid]["citations"][later]["phase"], "after")
            with ReviewServer(("127.0.0.1", 0), Handler, None, None, labels, goose_session=self.path, allowed_root=self.path.parent) as reopened:
                self.assertEqual(reopened.checked_reviews(), exported)
            original_labels = labels.read_bytes()
            value = fixture(); value["conversation"][1]["content"][0]["toolResult"]["value"]["structuredContent"]["stderr"] = "changed"
            self.path.write_text(json.dumps(value))
            self.assertEqual(request("/api/export")[0], 409)
            self.assertEqual(labels.read_bytes(), original_labels)
        finally:
            server.shutdown(); server.server_close(); thread.join()

    def test_recorded_local_example_retains_failed_check_and_later_rerun(self):
        path = Path(__file__).resolve().parents[1] / "examples/goose/local-session.redacted.json"
        bundle, turns, _ = import_session(path)
        self.assertEqual([t["goose"]["process_exit_code"] for t in turns], [1, None, 0])
        self.assertEqual(len(bundle["episodes"]), 2)
        self.assertIn("second test run", bundle["episodes"][0]["message"])
        self.assertEqual([e["phase"] for e in bundle["episodes"][0]["evidence"]], ["before", "before", "after"])


if __name__ == "__main__":
    unittest.main()
