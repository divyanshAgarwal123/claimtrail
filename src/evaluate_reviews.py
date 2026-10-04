"""Compare session retrievers against independently reviewed turn citations.

This measures coverage of cited eligible sessions, not claim truth or verifier accuracy.
No metric is emitted when the frozen queue has no human labels.
"""

from __future__ import annotations

import argparse
import csv
import json
import random
from collections import Counter
from datetime import timedelta
from pathlib import Path

from claimtrail import eligible_sessions, rows
from identifier_retrieval import is_claim_echo, parse_time
from review_app import revision


DERIVED = Path("data/derived")


def _interval(hits: int, count: int) -> list[float] | None:
    """Wilson 95% interval for a descriptive proportion."""
    if not count:
        return None
    z = 1.96
    p = hits / count
    d = 1 + z * z / count
    center = (p + z * z / (2 * count)) / d
    radius = z * ((p * (1 - p) / count + z * z / (4 * count * count)) ** 0.5) / d
    return [round(max(0, center - radius), 4), round(min(1, center + radius), 4)]


def _paired_interval(differences: list[int], draws: int = 3000) -> list[float] | None:
    if not differences:
        return None
    generator = random.Random(20261003)
    n = len(differences)
    samples = sorted(sum(generator.choice(differences) for _ in range(n)) / n
                     for _ in range(draws))
    return [round(samples[int(0.025 * draws)], 4),
            round(samples[min(draws - 1, int(0.975 * draws))], 4)]


def evaluate(queue: list[str], reviews: dict, claims: dict, turns: dict,
             sessions: dict, lexical: dict, semantic: dict, bundle_sha256: str | None = None) -> dict:
    if len(set(queue)) != len(queue):
        raise ValueError("duplicate episodes in review queue")
    if set(reviews) - set(queue):
        raise ValueError("review file contains episodes outside the frozen queue")
    counts = Counter()
    complete = 0
    examples = []
    for cid in queue:
        review = reviews.get(cid)
        if not review:
            continue
        if review.get("data_mode") in {"synthetic_demo", "development_review", "ai_assisted_review"}:
            raise ValueError("synthetic practice, development, or AI-assisted annotations cannot be evaluated as independent human labels")
        if bundle_sha256 is not None and (review.get("data_mode") != "research" or review.get("bundle_sha256") != bundle_sha256):
            raise ValueError("review provenance does not match the current research bundle")
        units = review.get("units", [])
        if not units:
            continue
        for unit in units:
            if unit.get("status", "") not in {"", "supported", "contradicted", "mixed", "unresolved", "not_a_claim"}:
                raise ValueError("unknown evidence status in review")
            for tid in unit.get("evidence_ids", []):
                if tid not in turns:
                    raise ValueError(f"unknown cited turn: {tid}")
                if is_claim_echo(turns[tid]):
                    raise ValueError("chat-send echoes cannot be action/output evidence")
        counts.update(u.get("status") or "unlabeled" for u in units)
        if any(not u.get("status") for u in units):
            continue
        complete += 1
        claim = claims[cid]
        candidates = {s["id"] for s in eligible_sessions(claim, list(sessions.values()))}
        for ranking in (lexical[cid], semantic[cid]):
            ranked_ids = [x["session_id"] for x in ranking["top3"]]
            if len(ranked_ids) != len(set(ranked_ids)) or not set(ranked_ids) <= candidates:
                raise ValueError("ranking contains duplicate or ineligible sessions")
            if ranking["candidates_24h"] != len(candidates):
                raise ValueError("ranking candidate count differs from current source snapshot")
        when = parse_time(claim["created_at"])
        floor = when - timedelta(hours=24)
        eligible = set()
        for unit in units:
            if unit["status"] == "not_a_claim":
                continue
            for tid in unit.get("evidence_ids", []):
                turn = turns.get(tid)
                session = sessions.get(turn["session_id"])
                if not session or session["agent_id"] != claim["agent_id"]:
                    continue
                if floor <= parse_time(turn["created_at"]) <= when and floor <= parse_time(session["created_at"]) <= when:
                    eligible.add(session["id"])
        if not eligible:
            continue
        left = {x["session_id"] for x in lexical[cid]["top3"]}
        right = {x["session_id"] for x in semantic[cid]["top3"]}
        examples.append({"claim_id": cid, "eligible_cited_sessions": len(eligible),
                         "lexical_hit": bool(eligible & left),
                         "semantic_hit": bool(eligible & right)})
    if not reviews:
        return {"status": "pending_human_review", "queue_episodes": len(queue),
                "reviewed_episodes": 0, "fully_labeled_episodes": 0,
                "note": "No human labels exist; no accuracy or citation-coverage metric computed."}
    left_hits = sum(x["lexical_hit"] for x in examples)
    right_hits = sum(x["semantic_hit"] for x in examples)
    n = len(examples)
    differences = [int(x["semantic_hit"]) - int(x["lexical_hit"]) for x in examples]
    return {
        "status": "descriptive_only" if n else "no_eligible_cited_episodes",
        "queue_episodes": len(queue), "reviewed_episodes": sum(cid in reviews for cid in queue),
        "fully_labeled_episodes": complete, "unit_status_counts": dict(sorted(counts.items())),
        "eligible_episodes_with_cited_prior_claimant_sessions": n,
        "lexical_top3_citation_coverage": {"hits": left_hits, "denominator": n,
                                            "rate": round(left_hits / n, 4) if n else None,
                                            "wilson_95": _interval(left_hits, n)},
        "semantic_top3_citation_coverage": {"hits": right_hits, "denominator": n,
                                             "rate": round(right_hits / n, 4) if n else None,
                                             "wilson_95": _interval(right_hits, n)},
        "semantic_minus_lexical": {"rate_difference": round(sum(differences) / n, 4) if n else None,
                                   "paired_bootstrap_95": _paired_interval(differences)},
        "cases": examples,
        "caveat": "Citations can miss relevant evidence and may be influenced by displayed leads. Session goals are snapshot metadata, not guaranteed available at claim time. Intervals treat episodes as independent; shared agents/tasks can make them too narrow. This is descriptive cited-session coverage, not retrieval recall, claim support accuracy, a population estimate, or an official judging score.",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--derived", type=Path, default=DERIVED)
    parser.add_argument("--reviews", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    derived = args.derived
    with (derived / "review_queue.csv").open(newline="", encoding="utf-8") as fh:
        queue = [x["claim_id"] for x in csv.DictReader(fh)]
    reviews_path = args.reviews or derived / "human_reviews.json"
    reviews = json.loads(reviews_path.read_text(encoding="utf-8")) if reviews_path.exists() else {}
    if not reviews:
        result = evaluate(queue, {}, {}, {}, {}, {}, {})
    else:
        result = evaluate(
            queue, reviews,
            {x["id"]: x for x in rows(derived / "candidate_claims.jsonl")},
            {x["id"]: x for x in rows(derived / "window_turns.jsonl")},
            {x["id"]: x for x in rows(derived / "window_sessions.jsonl")},
            {x["claim_id"]: x for x in rows(derived / "baseline_links.jsonl")},
            {x["claim_id"]: x for x in rows(derived / "semantic_links.jsonl")},
            revision(json.loads((derived / "review_bundle.json").read_text(encoding="utf-8"))),
        )
    content = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(content + "\n", encoding="utf-8")
    print(content)


if __name__ == "__main__":
    main()
