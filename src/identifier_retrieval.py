"""Exact artifact-identifier retrieval from the frozen local analysis slice.

This finds evidence *candidates*, never assigns support labels. A commit hash
appearing in a log does not by itself prove that the claimant pushed it.
"""

from __future__ import annotations

import collections
import json
import re
from datetime import datetime, timedelta
from pathlib import Path

from claimtrail import rows, write_jsonl


HASH = re.compile(r"\b[0-9a-f]{7,40}\b", re.I)
PR = re.compile(r"\bPR\s*#\s*(\d+)\b", re.I)


def parse_time(value: str):
    if "." in value:
        whole, fraction = value.split(".", 1)
        value = whole + "." + fraction[:6].ljust(6, "0")
    return datetime.fromisoformat(value)


def identifiers(value: str):
    return {"hash:" + h.lower() for h in HASH.findall(value)} | {
        "pr:" + n for n in PR.findall(value)
    }


def is_claim_echo(turn):
    action_name = (turn.get("agent_action") or {}).get("action", "")
    return action_name in {"send_message_back_to_chat", "send_message_to_chat", "talk"}


def main():
    root = Path("data/derived")
    claims = list(rows(root / "candidate_claims.jsonl"))
    # Long-lived sessions may start before the one-day baseline lead-in.
    session_owner = {s["id"]: s["agent_id"] for s in rows(Path("data/raw/computer_use_sessions.jsonl"))}
    index = collections.defaultdict(list)
    for turn in rows(root / "window_turns.jsonl"):
        if is_claim_echo(turn):
            # The chat send turn simply echoes the claim and is circular evidence.
            continue
        action = json.dumps(turn.get("agent_action"), ensure_ascii=False)
        observed = (turn.get("output") or "") + "\n" + (turn.get("error") or "")
        for key in identifiers(action + "\n" + observed):
            index[key].append((turn, key in identifiers(observed)))

    results = []
    for claim in claims:
        when = parse_time(claim["created_at"])
        keys = sorted(identifiers(claim["content"]))
        hits = []
        for key in keys:
            for turn, in_output in index.get(key, []):
                t = parse_time(turn["created_at"])
                if not when - timedelta(hours=24) <= t <= when + timedelta(hours=2):
                    continue
                hits.append({"identifier": key, "turn_id": turn["id"],
                             "session_id": turn["session_id"], "created_at": turn["created_at"],
                             "phase": "before" if t <= when else "after",
                             "same_agent": session_owner.get(turn["session_id"]) == claim["agent_id"],
                             "in_tool_output": in_output})
        # Keep the complete unique hit list so downstream reviewers can audit recall.
        hits = list({(h["identifier"], h["turn_id"]): h for h in hits}.values())
        hits.sort(key=lambda h: (h["created_at"], h["identifier"], h["turn_id"]))
        results.append({"claim_id": claim["id"], "identifiers": keys, "hits": hits})
    write_jsonl(root / "identifier_hits.jsonl", results)
    print(json.dumps({"claims": len(results),
                      "claims_with_identifier": sum(bool(x["identifiers"]) for x in results),
                      "claims_with_hit": sum(bool(x["hits"]) for x in results)}))


if __name__ == "__main__":
    main()
