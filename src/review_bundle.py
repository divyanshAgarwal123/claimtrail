"""Build a compact, unlabeled local review bundle from the frozen queue.

Evidence here is retrieved for inspection, never classified as true or false.
The frozen queue is read but not changed. No human-label file is created.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
from collections import defaultdict
from datetime import timedelta
from pathlib import Path

from claimtrail import bm25, rows
from identifier_retrieval import identifiers, is_claim_echo, parse_time


SOURCE_CARD = "https://huggingface.co/datasets/aidigestorg/ai-village"
SENTENCE_BREAK = re.compile(r"(?<=[.!?])\s+(?=[A-Za-z@*`])|[;\n]+")
ASSERTION = re.compile(
    r"\b(?:pushed|merged|created|fixed|added|finished|completed|verified|"
    r"deployed|implemented|built|passed|passes|works|working|live|now|"
    r"restored|resolved|total|unique|HTTP\s*200)\b", re.I
)


def proposed_units(content: str, limit: int = 7) -> list[dict]:
    """Suggest editable text spans. This is not a gold claim decomposition."""
    spans = [re.sub(r"\s+", " ", x).strip(" -•*\t") for x in SENTENCE_BREAK.split(content)]
    spans = [x for x in spans if len(x) >= 8 and ASSERTION.search(x)]
    if not spans:
        spans = [re.sub(r"\s+", " ", content).strip()[:500]]
    return [{"unit_id": f"u{i + 1}", "text": x if len(x) <= 1900 else x[:1899] + "…"}
            for i, x in enumerate(spans[:limit])]


def turn_text(turn: dict) -> str:
    action = json.dumps(turn.get("agent_action") or {}, ensure_ascii=False)
    return "\n".join(x for x in (action, turn.get("output") or "", turn.get("error") or "") if x)


def excerpt(value: str, query: str, limit: int = 1100) -> str:
    if len(value) <= limit:
        return value
    needles = list(identifiers(query))
    needles = [x.split(":", 1)[1] for x in needles] + [
        x for x in re.findall(r"[A-Za-z][A-Za-z0-9_.-]{5,}", query) if x.lower() not in {"cosmic", "sights", "universe"}
    ]
    lower = value.lower()
    positions = [lower.find(x.lower()) for x in needles]
    positions = [p for p in positions if p >= 0]
    start = max(0, (min(positions) - 180) if positions else 0)
    start = min(start, len(value) - limit)
    end = start + limit
    return ("…" if start else "") + value[start:end] + ("…" if end < len(value) else "")


def select_evidence(claim: dict, turns: list[dict], owner: dict, baseline: dict,
                    identifier_hits: dict, limit: int = 24) -> list[dict]:
    when = parse_time(claim["created_at"])
    floor, ceiling = when - timedelta(hours=24), when + timedelta(hours=2)
    own = []
    by_id = {}
    for turn in turns:
        t = parse_time(turn["created_at"])
        if floor <= t <= ceiling and not is_claim_echo(turn):
            by_id[turn["id"]] = turn
            if owner.get(turn["session_id"]) == claim["agent_id"] and turn_text(turn).strip("{}\n "):
                own.append(turn)

    selected: dict[str, set[str]] = defaultdict(set)
    scores = bm25(claim["content"], [turn_text(x)[:5000] for x in own])
    scored = sorted(zip(own, scores), key=lambda p: (-p[1], p[0]["created_at"], p[0]["id"]))
    for turn, _ in scored[:10]:
        selected[turn["id"]].add("lexical turn")
    preceding = [x for x in own if parse_time(x["created_at"]) <= when]
    for turn in preceding[-3:]:
        selected[turn["id"]].add("recent claimant turn")
    baseline_ids = {x["session_id"] for x in baseline["top3"]}
    for sid in baseline_ids:
        choices = [(turn, score) for turn, score in scored
                   if turn["session_id"] == sid and parse_time(turn["created_at"]) <= when]
        for turn, _ in choices[:2]:
            selected[turn["id"]].add("baseline session")
    hits = identifier_hits["hits"]
    # Keep both claimant and collaborator matches, on both sides of the claim.
    buckets = defaultdict(list)
    for hit in hits:
        if hit["turn_id"] in by_id:
            buckets[(hit["phase"], hit["same_agent"])].append(hit)
    for key, cap in {("before", True): 8, ("after", True): 4,
                     ("before", False): 5, ("after", False): 5}.items():
        for hit in buckets[key][-cap:]:
            selected[hit["turn_id"]].add("identifier " + hit["identifier"])
    # Deterministic cap: identifier matches first, then other ranked aids.
    priority = lambda tid: (0 if any(x.startswith("identifier") for x in selected[tid]) else 1,
                            0 if "lexical turn" in selected[tid] else 1,
                            abs((parse_time(by_id[tid]["created_at"]) - when).total_seconds()), tid)
    chosen = sorted(selected, key=priority)[:limit]
    result = []
    for tid in sorted(chosen, key=lambda x: (by_id[x]["created_at"], x)):
        turn = by_id[tid]
        t = parse_time(turn["created_at"])
        action = json.dumps(turn.get("agent_action") or {}, ensure_ascii=False)
        output = turn.get("output") or ""
        error = turn.get("error") or ""
        result.append({
            "turn_id": tid, "session_id": turn["session_id"], "created_at": turn["created_at"],
            "phase": "before" if t <= when else "after", "same_agent": owner.get(turn["session_id"]) == claim["agent_id"],
            "retrieved_by": sorted(selected[tid]), "action_excerpt": excerpt(action, claim["content"], 600),
            "output_excerpt": excerpt(output, claim["content"]), "error_excerpt": excerpt(error, claim["content"], 650),
            "screenshot_is_redacted": turn.get("screenshot_is_redacted"),
            "source_shard": turn["source_shard"],
        })
    return result


def build(raw: Path, derived: Path, output: Path) -> dict:
    with (derived / "review_queue.csv").open(newline="", encoding="utf-8") as fh:
        queue = list(csv.DictReader(fh))
    claim_map = {x["id"]: x for x in rows(derived / "candidate_claims.jsonl")}
    baseline = {x["claim_id"]: x for x in rows(derived / "baseline_links.jsonl")}
    hits = {x["claim_id"]: x for x in rows(derived / "identifier_hits.jsonl")}
    owner = {x["id"]: x["agent_id"] for x in rows(raw / "computer_use_sessions.jsonl")}
    turns = list(rows(derived / "window_turns.jsonl"))
    provenance = json.loads(Path("docs/provenance.json").read_text(encoding="utf-8"))
    episodes = []
    for record in queue:
        claim = claim_map[record["claim_id"]]
        episodes.append({
            "claim_id": claim["id"], "created_at": claim["created_at"],
            "agent_name": claim["agent_name"], "agent_id": claim["agent_id"],
            "message": claim["content"], "proposed_units": proposed_units(claim["content"]),
            "baseline_top3_sessions": baseline[claim["id"]]["top3"],
            "identifiers": hits[claim["id"]]["identifiers"],
            "evidence": select_evidence(claim, turns, owner, baseline[claim["id"]], hits[claim["id"]]),
        })
    bundle = {"source_card": SOURCE_CARD, "main_revision": provenance["main_revision"],
              "parquet_revision": provenance["parquet_revision"], "queue_seed": 20261003,
              "review_status": "unlabeled until a human saves a review", "episodes": episodes}
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(bundle, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"episodes": len(episodes), "evidence_cards": sum(len(x["evidence"]) for x in episodes),
                      "output": str(output)}))
    return bundle


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw", type=Path, default=Path("data/raw"))
    parser.add_argument("--derived", type=Path, default=Path("data/derived"))
    parser.add_argument("--output", type=Path, default=Path("data/derived/review_bundle.json"))
    args = parser.parse_args()
    build(args.raw, args.derived, args.output)
