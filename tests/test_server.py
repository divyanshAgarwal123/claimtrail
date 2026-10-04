"""HTTP behavior and synthetic-only writes, using an ephemeral loopback port."""
import copy
import http.client
import json
import sys
import tempfile
import threading
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from demo_data import uid
from review_app import Handler, ReviewServer, revision
from review_provenance import SourceIntegrityError, citation_metadata, source_hash


class ServerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.labels = Path(self.temp.name) / "practice.json"
        # Deliberately pass absent research paths: demo must be self-contained.
        self.server = ReviewServer(("127.0.0.1", 0), Handler, None, None, self.labels, demo=True)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.cid = uid("claim-deploy")

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()
        self.temp.cleanup()

    def request(self, path, method="GET", payload=None, headers=None):
        connection = http.client.HTTPConnection("127.0.0.1", self.server.server_port, timeout=5)
        h = {"Content-Type": "application/json",
             "Origin": f"http://127.0.0.1:{self.server.server_port}"}
        h.update(headers or {})
        connection.request(method, path, body=json.dumps(payload) if payload is not None else None, headers=h)
        response = connection.getresponse()
        data = response.read()
        result = (response.status, json.loads(data) if "application/json" in response.getheader("Content-Type", "") else data)
        connection.close()
        return result

    def payload(self, tid=None, base_revision=None):
        return {"claim_id": self.cid, "base_revision": base_revision, "units": [
            {"unit_id": "u1", "text": "Synthetic practice assertion", "status": "unresolved",
             "confidence": "low", "evidence_ids": [tid] if tid else [], "notes": "Test fixture, not a real review"}]}

    def test_clean_demo_no_data_no_prefilled_labels_and_route_guards(self):
        code, data = self.request("/api/episodes")
        self.assertEqual(code, 200)
        self.assertEqual(data["mode"], "synthetic_demo")
        self.assertEqual(len(data["items"]), 3)
        self.assertTrue(all(i["total_units"] == 0 for i in data["items"]))
        self.assertFalse(self.labels.exists())
        self.assertEqual(self.request("/../../README.md")[0], 404)
        self.assertEqual(self.request("/api/episodes", headers={"Host": "evil.invalid"})[0], 403)
        self.assertEqual(self.request("/api/review/" + self.cid, "POST", self.payload(),
                                      {"Origin": "https://evil.invalid"})[0], 403)

    def test_invalid_echo_and_out_of_window_citations_rejected(self):
        for name in ("missing", "deploy-echo", "deploy-too-late"):
            with self.subTest(name=name):
                code, result = self.request("/api/review/" + self.cid, "POST", self.payload(uid(name)))
                self.assertEqual(code, 400, result)
        self.assertFalse(self.labels.exists())

    def test_stale_tab_cannot_overwrite_and_export_preserves_provenance(self):
        payload = self.payload(uid("deploy-later"))
        code, saved = self.request("/api/review/" + self.cid, "POST", payload)
        self.assertEqual(code, 200, saved)
        self.assertEqual(self.request("/api/review/" + self.cid, "POST", payload)[0], 409)
        code, opened = self.request("/api/episode/" + self.cid)
        self.assertEqual(opened["revision"], saved["revision"])
        self.assertEqual(opened["review"]["data_mode"], "synthetic_demo")
        self.assertEqual(opened["review"]["bundle_sha256"], self.server.bundle_sha256)
        payload["base_revision"] = saved["revision"]
        payload["units"][0]["notes"] = "Updated synthetic annotation"
        self.assertEqual(self.request("/api/review/" + self.cid, "POST", payload)[0], 200)
        code, export = self.request("/api/export")
        self.assertEqual(export[self.cid]["units"][0]["notes"], "Updated synthetic annotation")

    def test_search_filters_exclude_future_other_actor_and_claim_echo(self):
        path = "/api/search?episode_id=" + self.cid + "&q=a1b2c3d&scope=claimant&phase=before"
        code, data = self.request(path)
        self.assertEqual(code, 200)
        ids = {r["turn_id"] for r in data["results"]}
        self.assertIn(uid("deploy-commit"), ids)
        self.assertNotIn(uid("deploy-echo"), ids)
        self.assertNotIn(uid("deploy-later"), ids)
        self.assertNotIn(uid("deploy-too-late"), ids)
        code, data = self.request(path.replace("scope=claimant&phase=before", "scope=all&phase=after"))
        self.assertEqual({r["turn_id"] for r in data["results"]}, {uid("deploy-later")})

    def start_ai_fixture(self, pinned=True):
        bundle = {**copy.deepcopy(self.server.bundle), "data_mode": "research"}
        for episode in bundle["episodes"]:
            episode["evidence"] = []
        root = Path(self.temp.name)
        (root / "bundle.json").write_text(json.dumps(bundle))
        (root / "turns.jsonl").write_text("\n".join(json.dumps(t) for t in self.server.turns.values()))
        (root / "sessions.jsonl").write_text("\n".join(json.dumps({"id": k, "agent_id": v}) for k, v in self.server.owner.items()))
        initial = {**self.payload(uid("deploy-later")), "data_mode": "ai_assisted_review", "bundle_sha256": revision(bundle)}
        if pinned:
            initial["citations"] = citation_metadata(bundle["episodes"][0], initial, self.server.turns, self.server.owner)
            initial["assessment_policy"] = {"independent_human_validation": False, "limits": ["Keep this exact prior policy"]}
            initial["assessment_origin"] = "AI-assisted synthetic fixture"
        self.labels.write_text(json.dumps({self.cid: initial}))
        self.server.shutdown(); self.server.server_close(); self.thread.join()
        self.server = ReviewServer(("127.0.0.1", 0), Handler, root / "bundle.json", root / "turns.jsonl",
                                   self.labels, root / "sessions.jsonl", ai_review=True)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        return initial

    def test_ai_mode_exports_and_edits_retain_ai_origin_and_cited_timeline(self):
        initial = self.start_ai_fixture()
        self.assertEqual(self.request("/api/episodes")[1]["mode"], "ai_assisted_review")
        _, opened = self.request("/api/episode/" + self.cid)
        self.assertEqual(opened["episode"]["evidence"][0]["phase"], "after")
        self.assertIn("review citation", opened["episode"]["evidence"][0]["retrieved_by"])
        same = self.payload(uid("deploy-later"), opened["revision"])
        same.update(citations={"forged": {}}, assessment_policy={"independent_human_validation": True},
                    assessment_origin="human")
        code, saved = self.request("/api/review/" + self.cid, "POST", same)
        self.assertEqual(code, 200, saved)
        _, export = self.request("/api/export")
        for key in ("citations", "assessment_policy", "assessment_origin"):
            self.assertEqual(export[self.cid][key], initial[key])
        _, opened = self.request("/api/episode/" + self.cid)
        payload = self.payload(uid("deploy-commit"), opened["revision"])
        self.assertEqual(self.request("/api/review/" + self.cid, "POST", payload)[0], 200)
        _, export = self.request("/api/export")
        self.assertEqual(export[self.cid]["data_mode"], "ai_assisted_review")
        self.assertIn("AI-assisted", export[self.cid]["assessment_origin"])
        self.assertIn("not independent", export[self.cid]["source"])
        self.assertEqual(set(export[self.cid]["citations"]), {uid("deploy-commit")})
        metadata = export[self.cid]["citations"][uid("deploy-commit")]
        self.assertEqual(metadata["phase"], "before")
        self.assertTrue(metadata["same_agent"])
        self.assertEqual(metadata["source_record_sha256"], source_hash(self.server.turns[uid("deploy-commit")]))
        self.assertEqual(export[self.cid]["assessment_policy"], initial["assessment_policy"])
        root = Path(self.temp.name)
        # Restart verifies persisted metadata against source files, not browser state.
        with ReviewServer(("127.0.0.1", 0), Handler, root / "bundle.json", root / "turns.jsonl",
                          self.labels, root / "sessions.jsonl", ai_review=True) as reopened:
            self.assertEqual(reopened.checked_reviews(), export)

    def test_mutated_source_blocks_reload_export_and_save_without_losing_labels(self):
        self.start_ai_fixture()
        before = self.labels.read_bytes()
        _, opened = self.request("/api/episode/" + self.cid)
        path = Path(self.temp.name) / "turns.jsonl"
        records = [json.loads(line) for line in path.read_text().splitlines()]
        next(t for t in records if t["id"] == uid("deploy-later"))["output"] = "Changed output; same identifier and time"
        path.write_text("\n".join(json.dumps(t) for t in records))
        for url in ("/api/episode/" + self.cid, "/api/export", "/api/turn/" + uid("deploy-later")):
            self.assertEqual(self.request(url)[0], 409)
        self.assertEqual(self.request("/api/review/" + self.cid, "POST", self.payload(None, opened["revision"]))[0], 409)
        self.assertEqual(self.labels.read_bytes(), before)
        root = Path(self.temp.name)
        with self.assertRaisesRegex(SourceIntegrityError, "source content changed"):
            ReviewServer(("127.0.0.1", 0), Handler, root / "bundle.json", path,
                         self.labels, root / "sessions.jsonl", ai_review=True)

    def test_changed_cached_content_cannot_be_re_pinned_by_removing_citation(self):
        self.start_ai_fixture()
        _, opened = self.request("/api/episode/" + self.cid)
        before = self.labels.read_bytes()
        self.server.turns[uid("deploy-later")]["output"] = "Changed cached source"
        code, error = self.request("/api/review/" + self.cid, "POST", self.payload(None, opened["revision"]))
        self.assertEqual(code, 409, error)
        self.assertEqual(self.labels.read_bytes(), before)

    def test_legacy_unpinned_review_is_explicit_and_pins_only_current_sources(self):
        self.start_ai_fixture(pinned=False)
        _, opened = self.request("/api/episode/" + self.cid)
        self.assertEqual(opened["integrity"]["status"], "legacy_unpinned")
        code, result = self.request("/api/review/" + self.cid, "POST", self.payload(uid("deploy-later"), opened["revision"]))
        self.assertEqual(code, 200, result)
        self.assertIn("Earlier unpinned", result["integrity"]["message"])
        _, opened = self.request("/api/episode/" + self.cid)
        review = opened["review"]
        self.assertTrue(review["provenance_history"]["legacy_unpinned"])
        self.assertFalse(review["assessment_policy"]["independent_human_validation"])
        self.assertEqual(review["citations"][uid("deploy-later")]["phase"], "after")
        self.assertFalse(review["citations"][uid("deploy-later")]["same_agent"])
        self.assertEqual(set(review["source_files_sha256"]), {"bundle", "turns", "sessions"})

    def test_inconsistent_saved_citation_metadata_is_rejected_on_read(self):
        self.start_ai_fixture()
        saved = json.loads(self.labels.read_text())
        saved[self.cid]["citations"][uid("deploy-later")]["phase"] = "before"
        self.labels.write_text(json.dumps(saved))
        code, error = self.request("/api/episode/" + self.cid)
        self.assertEqual(code, 409, error)
        self.assertIn("metadata", error["error"])


if __name__ == "__main__":
    unittest.main()
