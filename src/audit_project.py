"""Read-only structural audit of the research slice; never assigns human labels."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path

from claimtrail import CASE_STUDY_IDS, eligible_sessions, rows
from identifier_retrieval import is_claim_echo, parse_time
from review_app import revision


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def audit(root: Path) -> dict:
    derived = root / "data/derived"
    claims = list(rows(derived / "candidate_claims.jsonl"))
    sessions = list(rows(derived / "window_sessions.jsonl"))
    turns = list(rows(derived / "window_turns.jsonl"))
    owners = {s["id"]: s["agent_id"] for s in rows(root / "data/raw/computer_use_sessions.jsonl")}
    bundle = json.loads((derived / "review_bundle.json").read_text())
    with (derived / "review_queue.csv").open(newline="") as fh:
        queue = [r["claim_id"] for r in csv.DictReader(fh)]
    checks = {}
    for name, records in [("claims", claims), ("sessions", sessions), ("turns", turns)]:
        checks[name + "_unique_ids"] = len({r["id"] for r in records}) == len(records)
    checks["queue_unique_ids"] = len(set(queue)) == len(queue)
    checks["development_cases_excluded"] = not set(queue) & CASE_STUDY_IDS
    checks["bundle_matches_frozen_queue"] = [e["claim_id"] for e in bundle["episodes"]] == queue
    checks["all_turns_have_session_owner"] = all(t["session_id"] in owners for t in turns)
    turn_map = {t["id"]: t for t in turns}
    claim_map = {c["id"]: c for c in claims}
    bad_leads = 0
    for e in bundle["episodes"]:
        when = parse_time(e["created_at"])
        for lead in e["evidence"]:
            t = turn_map.get(lead["turn_id"])
            if not t:
                bad_leads += 1
                continue
            timestamp = parse_time(t["created_at"])
            bad_leads += int(is_claim_echo(t) or not when - timedelta(hours=24) <= timestamp <= when + timedelta(hours=2)
                             or lead["session_id"] != t["session_id"] or lead["created_at"] != t["created_at"]
                             or lead["same_agent"] != (owners[t["session_id"]] == e["agent_id"])
                             or lead["phase"] != ("before" if timestamp <= when else "after"))
    checks["all_leads_match_source_actor_time_window_no_chat_echo"] = bad_leads == 0
    eligible = {c["id"]: eligible_sessions(c, sessions) for c in claims}
    for method in ("baseline", "semantic"):
        rankings = list(rows(derived / f"{method}_links.jsonl"))
        valid = len(rankings) == len(claims) and {r["claim_id"] for r in rankings} == set(claim_map)
        for r in rankings:
            candidate_ids = {s["id"] for s in eligible[r["claim_id"]]}
            top = [s["session_id"] for s in r["top3"]]
            valid &= len(top) == len(set(top)) and set(top) <= candidate_ids and len(top) == min(3, len(candidate_ids))
            valid &= r["candidates_24h"] == len(candidate_ids)
        checks[method + "_rankings_valid_against_shared_eligible_pool"] = bool(valid)
    future_updates = sum(parse_time(s["updated_at"]) > parse_time(claim_map[cid]["created_at"])
                         for cid, pool in eligible.items() for s in pool if s.get("updated_at"))
    review_path = derived / "human_reviews.json"
    reviews = json.loads(review_path.read_text()) if review_path.exists() else {}
    checks["reviews_belong_to_frozen_queue"] = not set(reviews) - set(queue)
    return {"checked_at_utc": datetime.now(timezone.utc).isoformat(),
            "status": "passed" if all(checks.values()) else "failed", "checks": checks,
            "counts": {"claim_candidates": len(claims), "sessions_in_baseline_window": len(sessions),
                       "turns_including_lead_in": len(turns), "frozen_review_episodes": len(queue),
                       "initial_evidence_leads": sum(len(e["evidence"]) for e in bundle["episodes"]),
                       "saved_human_reviews": len(reviews), "invalid_evidence_leads": bad_leads,
                       "eligible_claim_session_pairs_updated_after_claim": future_updates},
            "turns_by_shard": dict(sorted(Counter(t["source_shard"] for t in turns).items())),
            "bundle_content_sha256": revision(bundle),
            "file_sha256": {name: digest(derived / name) for name in
                            ("review_queue.csv", "candidate_claims.jsonl", "window_sessions.jsonl",
                             "window_turns.jsonl", "baseline_links.jsonl", "semantic_links.jsonl")},
            "limits": ["Structural integrity is not correctness of agent claims or completeness of the export.",
                       "Converted turns come from a partial dataset; missing records remain unknown.",
                       "Session metadata reflects a snapshot; updated_at alone cannot prove field-level history.",
                       "This does not independently label any episode or validate a causal transmission link."]}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = audit(args.root)
    content = json.dumps(report, indent=2) + "\n"
    if args.output:
        args.output.write_text(content)
    print(content)
    raise SystemExit(0 if report["status"] == "passed" else 1)
