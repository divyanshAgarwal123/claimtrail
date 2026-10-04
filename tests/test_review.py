import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from review_app import load_reviews, save_reviews, validate_review
from review_bundle import proposed_units, select_evidence
from retrieval_comparison import comparison_rows
from case_summary import case_summary
from demo_data import demo_records, uid


class ReviewTests(unittest.TestCase):
    def test_summary_links_keep_actor_time_and_unresolved_conclusions(self):
        bundle, turns, sessions = demo_records()
        episode = bundle["episodes"][0]
        summary = case_summary(episode, None, "synthetic_demo", {t["id"]: t for t in turns},
                               {s["id"]: s["agent_id"] for s in sessions}, {})
        for group, phase in (("before", "before"), ("later", "after")):
            self.assertTrue(summary[group])
            for observation in summary[group]:
                self.assertTrue(observation["sources"])
                self.assertTrue(all(s["phase"] == phase for s in observation["sources"]))
        self.assertFalse(summary["later"][0]["sources"][0]["same_agent"])
        self.assertIn("unresolved", summary["unresolved"][0])
        episode["case_summary"]["before"][0]["turn_ids"] = [uid("deploy-later")]
        with self.assertRaisesRegex(ValueError, "wrong side"):
            case_summary(episode, None, "synthetic_demo", {t["id"]: t for t in turns},
                         {s["id"]: s["agent_id"] for s in sessions}, {})

    def test_generic_summary_uses_saved_citations_and_keeps_uncertainty(self):
        bundle, turns, sessions = demo_records()
        review = {"units": [{"text": "Live state is unknown", "status": "unresolved", "evidence_ids": [uid("deploy-later")]}]}
        summary = case_summary(bundle["episodes"][0], review, "ai_assisted_review",
                               {t["id"]: t for t in turns}, {s["id"]: s["agent_id"] for s in sessions}, {})
        self.assertEqual(summary["before"], [])
        self.assertEqual(summary["later"][0]["sources"][0]["turn_id"], uid("deploy-later"))
        self.assertIn("Live state is unknown", summary["unresolved"])
        self.assertEqual(summary["attribution"], "Saved assessment overview")

    def test_claim_spans_are_editable_suggestions_not_labels(self):
        units = proposed_units("I pushed `abc1234` to main. `config.js` now uses the new URL. Checks passed.")
        self.assertEqual(len(units), 3)
        self.assertEqual(units[0]["unit_id"], "u1")
        self.assertNotIn("status", units[0])

    def test_review_validation_preserves_human_status_and_uncertainty(self):
        cid = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
        tid = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"
        payload = {"claim_id": cid, "units": [{"unit_id": "u1", "text": "PR merged",
                    "status": "unresolved", "confidence": "low", "evidence_ids": [tid],
                    "notes": "No merge action visible"}]}
        clean = validate_review(payload, cid)
        self.assertEqual(clean["units"][0]["status"], "unresolved")
        self.assertEqual(clean["units"][0]["evidence_ids"], [tid])
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "labels.json"
            self.assertFalse(path.exists())
            self.assertEqual(load_reviews(path), {})
            save_reviews({cid: clean}, path)
            self.assertEqual(load_reviews(path)[cid]["units"][0]["confidence"], "low")
        payload["units"][0]["status"] = "verified_by_model"
        with self.assertRaises(ValueError):
            validate_review(payload, cid)

    def test_evidence_respects_window_and_excludes_chat_echo(self):
        cid = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
        claim = {"id": cid, "agent_id": "A", "created_at": "2026-05-05 12:00:00",
                 "content": "I pushed abc1234"}
        def turn(tid, when, action):
            return {"id": tid, "session_id": "S", "created_at": when,
                    "agent_action": action, "output": "abc1234", "error": None,
                    "source_shard": "turns-0000.parquet"}
        turns = [turn("before", "2026-05-05 11:59:00", {"command": "git log"}),
                 turn("echo", "2026-05-05 11:59:59", {"action": "send_message_back_to_chat"}),
                 turn("future", "2026-05-05 14:00:01", {"command": "git log"})]
        evidence = select_evidence(claim, turns, {"S": "A"}, {"top3": []}, {"hits": []})
        self.assertEqual([x["turn_id"] for x in evidence], ["before"])
        self.assertEqual(evidence[0]["phase"], "before")

    def test_review_validation_does_not_silently_truncate_rationale(self):
        payload = {"claim_id": "c1", "units": [{"unit_id": "u1", "text": "Pushed fix", "notes": "x" * 4001}]}
        with self.assertRaisesRegex(ValueError, "rationale exceeds"):
            validate_review(payload, "c1")
        payload["units"][0]["notes"] = None
        with self.assertRaisesRegex(ValueError, "must be strings"):
            validate_review(payload, "c1")

    def test_comparison_rejects_different_candidate_universes(self):
        cid = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
        claim = {"id": cid, "agent_id": "A", "created_at": "2026-05-05 12:00:00",
                 "content": "I pushed abc1234"}
        with self.assertRaises(ValueError):
            comparison_rows([{"claim_id": cid}], {cid: claim}, [],
                            {cid: {"candidates_24h": 2, "top3": []}},
                            {cid: {"candidates_24h": 3, "top3": []}},
                            {cid: {"identifiers": [], "hits": []}})


if __name__ == "__main__":
    unittest.main()
