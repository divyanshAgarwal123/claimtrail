import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from claimtrail import bm25, completion_candidate, eligible_sessions
from identifier_retrieval import identifiers, is_claim_echo


class ClaimTrailTests(unittest.TestCase):
    def test_completion_filter_rejects_negated_claim(self):
        self.assertIsNone(completion_candidate("I haven't pushed the fix yet."))
        self.assertEqual(completion_candidate("I pushed the config fix."), "pushed")

    def test_retrieval_never_uses_future_or_other_agent_session(self):
        claim = {"agent_id": "A", "created_at": "2026-05-05 18:00:00.2"}
        sessions = [
            {"agent_id": "A", "created_at": "2026-05-04 18:00:00.20000", "id": "in"},
            {"agent_id": "A", "created_at": "2026-05-04 17:59:59.9", "id": "old"},
            {"agent_id": "A", "created_at": "2026-05-05 18:00:00.3", "id": "future"},
            {"agent_id": "B", "created_at": "2026-05-05 17:59:59", "id": "other"},
        ]
        self.assertEqual([s["id"] for s in eligible_sessions(claim, sessions)], ["in"])

    def test_bm25_prefers_specific_artifact_terms(self):
        scores = bm25("I fixed broken config.js world URLs", [
            "fix broken config.js world URLs", "add cosmic sight names", "general work",
        ])
        self.assertGreater(scores[0], max(scores[1:]))

    def test_identifier_retrieval_excludes_claim_echo(self):
        self.assertEqual(identifiers("Commit `6fbc189` pushed; PR #193 merged"),
                         {"hash:6fbc189", "pr:193"})
        self.assertTrue(is_claim_echo({"agent_action": {"action": "send_message_back_to_chat",
                                                        "message": "pushed 6fbc189"}}))
        self.assertFalse(is_claim_echo({"agent_action": {"command": "git log --oneline"}}))


if __name__ == "__main__":
    unittest.main()
