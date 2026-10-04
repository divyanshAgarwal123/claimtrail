"""Describe retrieval disagreement and freeze ablation candidates without gold labels."""

from __future__ import annotations

import csv
import json
from datetime import timedelta
from pathlib import Path

from claimtrail import bm25, rows, write_jsonl
from identifier_retrieval import parse_time


DERIVED = Path("data/derived")


def top_bm25(claim: dict, sessions: list[dict], top_k: int = 3) -> list[dict]:
    texts = [(s.get("short_displayed_session_goal") or "") + " " + (s.get("session_goal") or "")
             for s in sessions]
    scores = bm25(claim["content"], texts)
    ranked = sorted(zip(sessions, scores), key=lambda x: (-x[1], x[0]["created_at"], x[0]["id"]))
    return [{"session_id": s["id"], "score": score} for s, score in ranked[:top_k]]


def comparison_rows(queue: list[dict], claims: dict, sessions: list[dict],
                    lexical: dict, semantic: dict, identifiers: dict) -> list[dict]:
    result = []
    for q in queue:
        cid = q["claim_id"]
        claim = claims[cid]
        left, right = lexical[cid], semantic[cid]
        if left["candidates_24h"] != right["candidates_24h"]:
            raise ValueError(f"candidate-universe mismatch for {cid}")
        when = parse_time(claim["created_at"])
        floor, ceiling = when - timedelta(hours=24), when + timedelta(hours=2)
        prior_all = [s for s in sessions if floor <= parse_time(s["created_at"]) <= when]
        no_actor = top_bm25(claim, prior_all)
        no_time = top_bm25(claim, [s for s in sessions
                                   if s["agent_id"] == claim["agent_id"] and
                                   floor <= parse_time(s["created_at"]) <= ceiling])
        other = top_bm25(claim, [s for s in prior_all if s["agent_id"] != claim["agent_id"]], 1)
        future = top_bm25(claim, [s for s in sessions
                                  if s["agent_id"] == claim["agent_id"] and
                                  when < parse_time(s["created_at"]) <= ceiling], 1)
        l_ids = [x["session_id"] for x in left["top3"]]
        s_ids = [x["session_id"] for x in right["top3"]]
        result.append({
            "claim_id": cid, "candidate_sessions_24h": left["candidates_24h"],
            "lexical_top3": l_ids, "semantic_top3": s_ids,
            "top3_overlap": len(set(l_ids) & set(s_ids)),
            "no_actor_lexical_top3": [x["session_id"] for x in no_actor],
            "no_time_lexical_top3": [x["session_id"] for x in no_time],
            "other_agent_hard_control": other[0] if other else None,
            "future_same_agent_control": future[0] if future else None,
            "identifier_keys": identifiers[cid]["identifiers"],
            "identifier_turn_hits": len(identifiers[cid]["hits"]),
            "human_relevant_turn_ids": None, "human_support_labels": None,
        })
    return result


def main():
    with (DERIVED / "review_queue.csv").open(newline="", encoding="utf-8") as fh:
        queue = list(csv.DictReader(fh))
    claims = {x["id"]: x for x in rows(DERIVED / "candidate_claims.jsonl")}
    sessions = list(rows(DERIVED / "window_sessions.jsonl"))
    lexical = {x["claim_id"]: x for x in rows(DERIVED / "baseline_links.jsonl")}
    semantic = {x["claim_id"]: x for x in rows(DERIVED / "semantic_links.jsonl")}
    identifiers = {x["claim_id"]: x for x in rows(DERIVED / "identifier_hits.jsonl")}
    comparison = comparison_rows(queue, claims, sessions, lexical, semantic, identifiers)
    write_jsonl(DERIVED / "retrieval_comparison.jsonl", comparison)
    overlap = {k: sum(x["top3_overlap"] == k for x in comparison) for k in range(4)}
    print(json.dumps({"held_out_unlabeled": len(comparison), "top3_overlap_distribution": overlap,
                      "same_top1": sum(x["lexical_top3"][0] == x["semantic_top3"][0] for x in comparison),
                      "other_agent_controls": sum(x["other_agent_hard_control"] is not None for x in comparison),
                      "future_same_agent_controls": sum(x["future_same_agent_control"] is not None for x in comparison),
                      "accuracy_metrics": "not computed; human evidence labels absent"}))


if __name__ == "__main__":
    main()
