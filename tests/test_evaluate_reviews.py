import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from evaluate_reviews import evaluate


class EvaluateReviewsTests(unittest.TestCase):
    def test_no_human_reviews_emits_no_metric(self):
        result = evaluate(["c1"], {}, {}, {}, {}, {}, {})
        self.assertEqual(result["status"], "pending_human_review")
        self.assertNotIn("lexical_top3_citation_coverage", result)

    def test_cited_prior_claimant_session_coverage_is_paired(self):
        queue = ["c1", "c2"]
        claims = {cid: {"created_at": "2026-05-05 12:00:00", "agent_id": "agent-a"} for cid in queue}
        sessions = {
            "relevant": {"id": "relevant", "agent_id": "agent-a", "created_at": "2026-05-05 10:00:00"},
            "decoy": {"id": "decoy", "agent_id": "agent-a", "created_at": "2026-05-05 09:00:00"},
            "other": {"id": "other", "agent_id": "agent-b", "created_at": "2026-05-05 10:00:00"},
        }
        turns = {
            "prior": {"session_id": "relevant", "created_at": "2026-05-05 11:00:00"},
            "later": {"session_id": "relevant", "created_at": "2026-05-05 13:00:00"},
            "other-agent": {"session_id": "other", "created_at": "2026-05-05 11:00:00"},
        }
        reviews = {
            "c1": {"units": [{"status": "supported", "evidence_ids": ["prior", "later", "other-agent"]}]},
            "c2": {"units": [{"status": "unresolved", "evidence_ids": ["later"]}]},
        }
        lexical = {cid: {"candidates_24h": 2, "top3": [{"session_id": "decoy"}]} for cid in queue}
        semantic = {cid: {"candidates_24h": 2, "top3": [{"session_id": "relevant"}]} for cid in queue}
        result = evaluate(queue, reviews, claims, turns, sessions, lexical, semantic)
        self.assertEqual(result["fully_labeled_episodes"], 2)
        self.assertEqual(result["eligible_episodes_with_cited_prior_claimant_sessions"], 1)
        self.assertEqual(result["lexical_top3_citation_coverage"]["hits"], 0)
        self.assertEqual(result["semantic_top3_citation_coverage"]["hits"], 1)
        self.assertEqual(result["semantic_minus_lexical"]["rate_difference"], 1.0)

    def test_invalid_citations_and_demo_reviews_fail_closed(self):
        review = {"c1": {"units": [{"status": "supported", "evidence_ids": ["missing"]}]}}
        with self.assertRaisesRegex(ValueError, "unknown cited turn"):
            evaluate(["c1"], review, {}, {}, {}, {}, {})
        review["c1"]["data_mode"] = "synthetic_demo"
        with self.assertRaisesRegex(ValueError, "synthetic practice"):
            evaluate(["c1"], review, {}, {}, {}, {}, {})
        for mode in ("development_review", "ai_assisted_review"):
            review["c1"]["data_mode"] = mode
            with self.assertRaisesRegex(ValueError, "independent human"):
                evaluate(["c1"], review, {}, {}, {}, {}, {})
        review["c1"]["data_mode"] = "research"
        review["c1"]["bundle_sha256"] = "different-bundle"
        with self.assertRaisesRegex(ValueError, "provenance"):
            evaluate(["c1"], review, {}, {}, {}, {}, {}, "expected-bundle")


if __name__ == "__main__":
    unittest.main()
