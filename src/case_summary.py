"""Small source-linked overviews, with editorial and saved-review origins explicit."""
from __future__ import annotations

from copy import deepcopy

from review_provenance import citation_metadata


def case_summary(episode: dict, review: dict | None, mode: str, turns: dict, owners: dict,
                 agent_names: dict) -> dict:
    spec = episode.get("case_summary") if mode == "synthetic_demo" else None
    if mode == "development_review":
        # Research interpretations are deliberately excluded from the synthetic ZIP.
        from development_summaries import SUMMARIES
        spec = SUMMARIES.get(episode["claim_id"])
    if spec:
        summary = deepcopy(spec)
    else:
        cited = {tid for unit in (review or {}).get("units", []) for tid in unit["evidence_ids"]}
        chosen = cited if review is not None else {e["turn_id"] for e in episode["evidence"]}
        summary = {
            "assertion": episode["message"][:300] + ("…" if len(episode["message"]) > 300 else ""),
            "attribution": "Saved assessment overview" if review is not None else "Unreviewed retrieval overview",
            "note": "Selected source links only; labels belong to the saved reviewer. Read the full claim and records below.",
            "before": [], "later": [], "unresolved": [],
        }
        metadata = citation_metadata(episode, {"units": [{"evidence_ids": sorted(chosen)}]}, turns, owners)
        for tid in sorted(chosen, key=lambda tid: (turns[tid]["created_at"], tid)):
            group = "before" if metadata[tid]["phase"] == "before" else "later"
            if len(summary[group]) < 3:
                summary[group].append({"text": "Cited source record" if review is not None else "Retrieved lead; not a support judgment",
                                       "turn_ids": [tid]})
        uncertain = [u["text"] for u in (review or {}).get("units", [])
                     if u.get("status", "") in {"", "unresolved", "mixed"}]
        summary["unresolved"] = uncertain[:3]
        if len(uncertain) > 3:
            summary["unresolved"].append(f"{len(uncertain) - 3} additional units need inspection below.")
        if not uncertain:
            summary["unresolved"] = ["No unresolved unit is recorded in this saved assessment; this is not an independent completeness check." if review else
                                      "No reviewed conclusion. Retrieved matches alone do not establish completion."]
        summary["unresolved"].append("Later evidence does not establish state at claim time; uninspected screenshots remain outside this review.")
    for group, phase in (("before", "before"), ("later", "after")):
        for observation in summary[group]:
            pins = citation_metadata(episode, {"units": [{"evidence_ids": observation["turn_ids"]}]}, turns, owners)
            observation["sources"] = []
            for tid in sorted(pins, key=lambda tid: (pins[tid]["created_at"], tid)):
                metadata = pins[tid]
                if metadata["phase"] != phase:
                    raise ValueError("Case summary source is on the wrong side of claim time: " + tid)
                observation["sources"].append({"turn_id": tid, **metadata,
                    "actor_name": agent_names.get(metadata["actor_id"], "Agent " + str(metadata["actor_id"])[:8])})
    return summary
