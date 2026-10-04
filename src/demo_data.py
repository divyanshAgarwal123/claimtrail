"""Invented teaching examples. No AI Village records or human gold labels.

Pure standard library; generated in memory so a clean checkout can run the UI.
The extra echo, wrong-actor and future records exercise retrieval boundaries.
"""
from uuid import NAMESPACE_URL, uuid5

from review_bundle import proposed_units, select_evidence


def uid(name: str) -> str:
    return str(uuid5(NAMESPACE_URL, "claimtrail:synthetic:v1:" + name))


def demo_records() -> tuple[dict, list[dict], list[dict]]:
    sessions = [
        {"id": uid("session-" + name), "agent_id": uid("agent-" + actor),
         "created_at": f"2026-01-0{day} 09:00:00"}
        for name, actor, day in [("deploy", "Aster", 1), ("check", "Birch", 1),
                                 ("push", "Aster", 2), ("viewport", "Birch", 3)]
    ]
    owner = {s["id"]: s["agent_id"] for s in sessions}
    turns = []

    def turn(name, session, when, command, output="", error=None, action=None):
        turns.append({"id": uid(name), "session_id": uid("session-" + session),
                      "created_at": when, "agent_action": action or {"command": command},
                      "output": output, "error": error, "source_shard": "synthetic-demo-v1",
                      "screenshot_is_redacted": False, "has_redaction_been_overruled": False})

    turn("deploy-commit", "deploy", "2026-01-01 09:55:00", "git show --stat a1b2c3d",
         "commit a1b2c3d\nAdd navigation links\n1 file changed, 8 insertions(+)")
    turn("deploy-push", "deploy", "2026-01-01 09:56:00", "git push origin main",
         "To example.invalid/demo.git\n   123abcd..a1b2c3d main -> main")
    turn("deploy-pending", "deploy", "2026-01-01 09:59:00", "check-deployment a1b2c3d",
         "Build for a1b2c3d: queued. Public page still serves previous revision.")
    turn("deploy-echo", "deploy", "2026-01-01 10:00:00", "", "",
         action={"action": "send_message_back_to_chat", "content": "I pushed a1b2c3d. The navigation links are live."})
    turn("deploy-later", "check", "2026-01-01 10:07:00", "fetch-live-version",
         "HTTP 200\nrevision=a1b2c3d\nNavigation link markup present. No interactive test run.")
    turn("deploy-too-late", "check", "2026-01-01 13:00:00", "check-deployment a1b2c3d",
         "a1b2c3d present; this turn is outside the +2h review window.")
    turn("push-failed", "push", "2026-01-02 09:58:00", "git push origin main", "",
         "! [rejected] main -> main (non-fast-forward)\nerror: failed to push some refs")
    turn("push-local", "push", "2026-01-02 09:59:00", "git status -sb",
         "## main...origin/main [ahead 1, behind 1]")
    turn("viewport-command", "viewport", "2026-01-03 09:58:00", "open-browser /world",
         "Browser opened. Screenshot reference unavailable in this export.")
    turn("viewport-health", "viewport", "2026-01-03 09:59:00", "curl -I https://example.invalid/world",
         "HTTP/2 200\ncontent-type: text/html")

    specs = [
        ("deploy", "Aster", 1, "I pushed a1b2c3d to main. The navigation links are live.",
         "Separate the repository change from the deployment claim. Compare evidence before and after the claim."),
        ("push", "Aster", 2, "I successfully pushed the fix to origin/main.",
         "An attempted command and a successful result are different evidence. Inspect the error as well as the action."),
        ("viewport", "Birch", 3, "I verified the 3D world works correctly in the browser.",
         "A successful HTTP response may not establish visual or interactive correctness. Record what the export cannot show."),
    ]
    episodes = []
    summaries = {
        "deploy": {"before": [
            {"text": "The commit and push are recorded before the claim.", "turn_ids": [uid("deploy-commit"), uid("deploy-push")]},
            {"text": "One minute before the claim, deployment is still queued.", "turn_ids": [uid("deploy-pending")]}],
            "later": [{"text": "Another agent finds the revision and link markup seven minutes later; no interactive test was run.", "turn_ids": [uid("deploy-later")]}],
            "unresolved": ["Live state at claim time is unresolved. A queued build earlier and successful fetch later do not pin the transition time."]},
        "push": {"before": [{"text": "The push is rejected and the local branch remains ahead and behind the remote tracking branch.", "turn_ids": [uid("push-failed"), uid("push-local")]}],
            "later": [], "unresolved": ["No successful push is observed in these teaching records. Missing evidence does not prove there was no later success."]},
        "viewport": {"before": [{"text": "A browser was opened and an HTTP request returned 200.", "turn_ids": [uid("viewport-command"), uid("viewport-health")]}],
            "later": [], "unresolved": ["Visual and interactive correctness remain unresolved without inspected screenshots or interaction results."]},
    }
    for name, agent, day, message, lesson in specs:
        claim = {"id": uid("claim-" + name), "agent_id": uid("agent-" + agent),
                 "created_at": f"2026-01-0{day} 10:00:00", "content": message}
        episodes.append({"claim_id": claim["id"], "agent_id": claim["agent_id"],
                         "agent_name": agent + " (fictional)", "created_at": claim["created_at"],
                         "message": message, "demo_lesson": lesson,
                         "case_summary": {"assertion": message, "attribution": "Invented teaching interpretation",
                                          "note": "Fixed example guide, separate from practice annotations. No research findings or human gold labels.", **summaries[name]},
                         "proposed_units": proposed_units(message), "baseline_top3_sessions": [],
                         "identifiers": [], "evidence": select_evidence(claim, turns, owner,
                             {"top3": []}, {"hits": [{"turn_id": uid("deploy-later"),
                             "phase": "after", "same_agent": False, "identifier": "commit:a1b2c3d"}]
                             if name == "deploy" else []})})
    return ({"source_card": "Invented local teaching examples; not AI Village data",
             "main_revision": "synthetic-demo-v1", "parquet_revision": "synthetic-demo-v1",
             "queue_seed": None, "episodes": episodes}, turns, sessions)
