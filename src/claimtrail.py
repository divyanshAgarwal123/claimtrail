"""Reproducible, local-only ClaimTrail candidate retrieval.

This stage retrieves possible source sessions. Session goals are agent statements,
not proof that a task was completed. Verification requires turns/artifacts.
"""

from __future__ import annotations

import argparse
import collections
import csv
import json
import math
import random
import re
from pathlib import Path


START = "2026-05-05 00:00:00"
END = "2026-05-09 00:00:00"
ROOM = "universe-coordination"
SEED = 20261003
# Development examples are excluded from the held-out review queue.
CASE_STUDY_IDS = {
    "52c54340-a444-4c66-a159-443d5916a15c",
    "f7007710-b83d-4f76-b4e3-a194093c700f",
}
CLAIM_RE = re.compile(
    r"\b(?:I|we)(?:'ve| have)?\s+(?:just\s+)?"
    r"(finished|completed|deployed|published|shipped|built|created|uploaded|"
    r"fixed|implemented|merged|pushed|integrated|added|launched)\b",
    re.IGNORECASE,
)
NEGATION_RE = re.compile(r"\b(?:not|haven't|hasn't|can't|couldn't|failed to)\b", re.I)
TOKEN_RE = re.compile(r"[a-z][a-z0-9]{2,}", re.I)
STOP = set("the and for with from that this have just been into our your their all are was you can now but not yet its it via were they them who how what when where will would should could about after before only over under more than out own use using used also onto make made still work working done ready live agent agents world worlds universe".split())


def rows(path: Path):
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            yield json.loads(line)


def write_jsonl(path: Path, records):
    with path.open("w", encoding="utf-8") as fh:
        for record in records:
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")


def tokens(text: str):
    return [x for x in TOKEN_RE.findall(text.lower()) if x not in STOP]


def completion_candidate(text: str):
    match = CLAIM_RE.search(text)
    if not match:
        return None
    # Negation near the trigger can flip its meaning. Keep distant negation for review.
    prefix = text[max(0, match.start() - 35):match.start()]
    if NEGATION_RE.search(prefix):
        return None
    return match.group(1).lower()


def bm25(query: str, documents: list[str]):
    """Rank documents in this one claim's time-constrained candidate set."""
    q = set(tokens(query))
    token_docs = [tokens(d) for d in documents]
    n = len(token_docs)
    if not n or not q:
        return [0.0] * n
    df = collections.Counter(t for doc in token_docs for t in set(doc))
    avg_len = sum(map(len, token_docs)) / n or 1
    result = []
    for doc in token_docs:
        tf = collections.Counter(doc)
        score = 0.0
        for term in q:
            if term not in tf:
                continue
            idf = math.log(1 + (n - df[term] + 0.5) / (df[term] + 0.5))
            score += idf * tf[term] * 2.2 / (tf[term] + 1.2 * (0.25 + 0.75 * len(doc) / avg_len))
        result.append(round(score, 6))
    return result


def eligible_sessions(claim, sessions, horizon_hours=24):
    from datetime import datetime, timedelta

    def parse_time(value):
        if "." in value:
            whole, fraction = value.split(".", 1)
            value = whole + "." + fraction[:6].ljust(6, "0")
        return datetime.fromisoformat(value)

    when = parse_time(claim["created_at"])
    floor = when - timedelta(hours=horizon_hours)
    return [s for s in sessions if s["agent_id"] == claim["agent_id"]
            and floor <= parse_time(s["created_at"]) <= when]


def prepare(raw: Path, output: Path, review_n: int = 25):
    output.mkdir(parents=True, exist_ok=True)
    agents = {r["id"]: r["name"] for r in rows(raw / "agents.jsonl")}
    rooms = {r["id"]: r["name"] for r in rows(raw / "chat_rooms.jsonl")}
    chat = [r for r in rows(raw / "chat_messages.jsonl") if START <= r["created_at"] < END
            and r["speaker_type"] == "agent" and rooms.get(r["room_id"]) == ROOM]
    chat.sort(key=lambda r: (r["created_at"], r["id"]))
    # Sessions may start before the window. Only keep a one-day lead-in.
    sessions = [r for r in rows(raw / "computer_use_sessions.jsonl")
                if "2026-05-04 00:00:00" <= r["created_at"] < END]
    sessions.sort(key=lambda r: (r["created_at"], r["id"]))
    write_jsonl(output / "window_chat.jsonl", chat)
    write_jsonl(output / "window_sessions.jsonl", sessions)

    claims = []
    for r in chat:
        verb = completion_candidate(r["content"])
        if verb:
            claims.append({"id": r["id"], "created_at": r["created_at"],
                           "agent_id": r["agent_speaker_id"],
                           "agent_name": agents.get(r["agent_speaker_id"], "unknown"),
                           "room_id": r["room_id"], "verb": verb,
                           "content": r["content"]})
    write_jsonl(output / "candidate_claims.jsonl", claims)

    links = []
    for claim in claims:
        candidates = eligible_sessions(claim, sessions)
        text = [(s.get("short_displayed_session_goal") or "") + " " + (s.get("session_goal") or "")
                for s in candidates]
        scores = bm25(claim["content"], text)
        ranked = sorted(zip(candidates, scores), key=lambda x: (-x[1], x[0]["created_at"], x[0]["id"]))[:3]
        links.append({"claim_id": claim["id"], "candidates_24h": len(candidates),
                      "top3": [{"session_id": s["id"], "created_at": s["created_at"],
                                "score": score, "short_goal": s.get("short_displayed_session_goal")}
                               for s, score in ranked]})
    write_jsonl(output / "baseline_links.jsonl", links)

    rng = random.Random(SEED)
    by_agent = collections.defaultdict(list)
    for claim in claims:
        if claim["id"] not in CASE_STUDY_IDS:
            by_agent[claim["agent_id"]].append(claim)
    balanced_pool = []
    for agent_id in sorted(by_agent):
        balanced_pool.extend(rng.sample(by_agent[agent_id], min(6, len(by_agent[agent_id]))))
    review = rng.sample(balanced_pool, min(review_n, len(balanced_pool)))
    review.sort(key=lambda x: (x["created_at"], x["id"]))
    link_by_id = {x["claim_id"]: x for x in links}
    with (output / "review_queue.csv").open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=["claim_id", "created_at", "agent_name", "verb",
                                               "content", "baseline_top3_session_ids", "is_completion_claim",
                                               "evidence_label", "review_notes"])
        writer.writeheader()
        for c in review:
            writer.writerow({"claim_id": c["id"], "created_at": c["created_at"],
                             "agent_name": c["agent_name"], "verb": c["verb"],
                             "content": c["content"], "baseline_top3_session_ids": "|".join(
                                 x["session_id"] for x in link_by_id[c["id"]]["top3"]),
                             "is_completion_claim": "", "evidence_label": "", "review_notes": ""})
    print(json.dumps({"window_chat": len(chat), "window_sessions_with_leadin": len(sessions),
                      "candidate_claims": len(claims), "review_queue": len(review),
                      "claims_with_prior_session": sum(x["candidates_24h"] > 0 for x in links),
                      "seed": SEED}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw", type=Path, default=Path("data/raw"))
    parser.add_argument("--output", type=Path, default=Path("data/derived"))
    parser.add_argument("--review-n", type=int, default=25)
    args = parser.parse_args()
    prepare(args.raw, args.output, args.review_n)
