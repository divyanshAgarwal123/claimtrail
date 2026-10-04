"""Local-only ClaimTrail evidence review server; no outbound requests or model calls."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import re
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from claimtrail import bm25, rows
from case_summary import case_summary
from identifier_retrieval import is_claim_echo, parse_time
from review_bundle import excerpt, turn_text
from review_provenance import (SourceIntegrityError, SourceSnapshot, citation_metadata,
                               default_review_policy, integrity_notice, source_hash)


ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "web"
DERIVED = ROOT / "data/derived"
LABELS = DERIVED / "human_reviews.json"
LABELS_ALLOWED = {"", "supported", "contradicted", "mixed", "unresolved", "not_a_claim"}
CONFIDENCE_ALLOWED = {"", "high", "medium", "low"}
UUID = re.compile(r"^[0-9a-fA-F]{8}-(?:[0-9a-fA-F]{4}-){3}[0-9a-fA-F]{12}$")


def revision(value: dict | None) -> str | None:
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest() if value is not None else None


def validate_review(value: dict, claim_id: str) -> dict:
    if not isinstance(value, dict) or value.get("claim_id") != claim_id:
        raise ValueError("claim_id mismatch")
    units = value.get("units")
    if not isinstance(units, list) or not 1 <= len(units) <= 30:
        raise ValueError("provide 1–30 atomic claim units")
    out, seen = [], set()
    for unit in units:
        if not isinstance(unit, dict):
            raise ValueError("invalid unit")
        if any(not isinstance(unit.get(key, ""), str) for key in ("unit_id", "text", "status", "confidence", "notes")):
            raise ValueError("unit text fields must be strings")
        uid = unit.get("unit_id", "")
        claim_text = unit.get("text", "").strip()
        status = unit.get("status", "")
        confidence = unit.get("confidence", "")
        evidence_ids = unit.get("evidence_ids", [])
        notes = unit.get("notes", "")
        if len(notes) > 4000:
            raise ValueError("rationale exceeds 4000 characters; shorten it before saving")
        if not uid or len(uid) > 80 or uid in seen or not claim_text or len(claim_text) > 2000:
            raise ValueError("each unit needs a unique ID and 1–2000 characters of text")
        if status not in LABELS_ALLOWED or confidence not in CONFIDENCE_ALLOWED:
            raise ValueError("invalid status or confidence")
        if not isinstance(evidence_ids, list) or len(evidence_ids) > 30 or any(
            not isinstance(x, str) or not UUID.fullmatch(x) for x in evidence_ids
        ):
            raise ValueError("evidence IDs must be turn UUIDs")
        seen.add(uid)
        out.append({"unit_id": uid, "text": claim_text, "status": status,
                    "confidence": confidence, "evidence_ids": sorted(set(evidence_ids)),
                    "notes": notes})
    return {"claim_id": claim_id, "units": out,
            "reviewed_at_utc": datetime.now(timezone.utc).isoformat(),
            "source": "human entry in local review interface"}


def load_reviews(path: Path = LABELS) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def save_reviews(reviews: dict, path: Path = LABELS) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent,
                                     prefix=".claimtrail_reviews_", delete=False) as fh:
        temp_path = Path(fh.name)
        os.chmod(temp_path, 0o600)
        json.dump(reviews, fh, ensure_ascii=False, indent=2)
    os.replace(temp_path, path)


class ReviewServer(HTTPServer):
    def __init__(self, address, handler, bundle_path: Path | None, turns_path: Path | None,
                 labels_path: Path, sessions_path: Path | None = None, demo: bool = False,
                 development: bool = False, ai_review: bool = False):
        if sum((demo, development, ai_review)) > 1:
            raise ValueError("choose one review mode")
        self.mode = "synthetic_demo" if demo else "development_review" if development else "ai_assisted_review" if ai_review else "research"
        if self.mode != "research" and labels_path.resolve() == LABELS.resolve():
            raise ValueError("non-human annotations must not overwrite human reviews")
        sessions_path = sessions_path or ROOT / "data/raw/computer_use_sessions.jsonl"
        self.sources = SourceSnapshot({} if demo else {"bundle": bundle_path, "turns": turns_path,
                                                       "sessions": sessions_path})
        if demo:
            from demo_data import demo_records
            self.bundle, turn_rows, session_rows = demo_records()
        else:
            self.bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
            expected_bundle_mode = "research" if ai_review else self.mode
            if self.bundle.get("data_mode", "research") != expected_bundle_mode:
                raise ValueError("bundle mode differs from server mode; development cases require --development")
            turn_rows = list(rows(turns_path))
            session_rows = list(rows(sessions_path))
        self.episodes = {x["claim_id"]: x for x in self.bundle["episodes"]}
        self.agent_names = {x["agent_id"]: x["agent_name"] for x in self.bundle["episodes"]}
        self.turns = {x["id"]: x for x in turn_rows}
        self.owner = {x["id"]: x["agent_id"] for x in session_rows}
        if len(self.episodes) != len(self.bundle["episodes"]) or len(self.turns) != len(turn_rows):
            raise ValueError("duplicate episode or turn IDs")
        if any(t["session_id"] not in self.owner for t in turn_rows):
            raise ValueError("turn without a known session owner")
        for episode in self.episodes.values():
            for lead in episode["evidence"]:
                turn = self.turns.get(lead["turn_id"])
                if not turn or turn["session_id"] != lead["session_id"] or turn["created_at"] != lead["created_at"]:
                    raise ValueError("evidence lead does not match its source turn")
                if lead["same_agent"] != (self.owner[turn["session_id"]] == episode["agent_id"]):
                    raise ValueError("evidence actor attribution mismatch")
                if lead["phase"] != ("before" if parse_time(turn["created_at"]) <= parse_time(episode["created_at"]) else "after"):
                    raise ValueError("evidence timing mismatch")
                if "source_record_sha256" in lead and lead["source_record_sha256"] != source_hash(turn):
                    raise SourceIntegrityError("Evidence anchor source content changed: " + turn["id"])
        self.bundle_sha256 = revision(self.bundle)
        self.labels_path = labels_path
        self.sources.check()
        self.checked_reviews()
        # Bind only after input validation, so failed startup leaves no listening socket.
        super().__init__(address, handler)

    def checked_reviews(self) -> dict:
        self.sources.check()
        saved = load_reviews(self.labels_path)
        if not isinstance(saved, dict):
            raise SourceIntegrityError("Saved review file must contain an object.")
        for cid, review in saved.items():
            if not isinstance(review, dict):
                raise SourceIntegrityError("Saved assessment must contain an object.")
            if cid not in self.episodes or review.get("bundle_sha256") not in {None, self.bundle_sha256}:
                raise ValueError("saved reviews belong to a different bundle; choose a separate --labels path")
            if review.get("data_mode", "research") != self.mode:
                raise ValueError("saved review mode differs from server mode; use a separate labels file")
            validate_review(review, cid)
            self.validate_citations(review)
            if "assessment_policy" in review and not isinstance(review["assessment_policy"], dict):
                raise SourceIntegrityError("Saved assessment policy must contain an object.")
            if "provenance_history" in review and not isinstance(review["provenance_history"], dict):
                raise SourceIntegrityError("Saved provenance history must contain an object.")
            if "source_files_sha256" in review and review["source_files_sha256"] != self.sources.hashes:
                raise SourceIntegrityError("Saved assessment source files changed; restore the pinned inputs.")
        return saved

    def validate_citations(self, review: dict) -> None:
        actual = citation_metadata(self.episodes[review["claim_id"]], review, self.turns, self.owner)
        if "citations" in review and review["citations"] != actual:
            raise SourceIntegrityError("Saved citation metadata or source content changed; restore verified records before reviewing or saving.")

    def named_lead(self, lead: dict) -> dict:
        actor = self.owner.get(lead["session_id"])
        return {**lead, "actor_id": actor,
                "actor_name": self.agent_names.get(actor, "Agent " + str(actor)[:8])}

    def summary(self, episode: dict, review: dict | None) -> dict:
        return case_summary(episode, review, self.mode, self.turns, self.owner, self.agent_names)

    def cited_leads(self, episode: dict, review: dict | None) -> list[dict]:
        """Include saved citations without changing the frozen retrieval bundle."""
        cited = {tid for u in (review or {}).get("units", []) for tid in u["evidence_ids"]}
        leads = {e["turn_id"]: {**e, "retrieved_by": list(e["retrieved_by"])} for e in episode["evidence"]}
        when = parse_time(episode["created_at"])
        for tid in cited:
            turn = self.turns[tid]
            offset = (parse_time(turn["created_at"]) - when).total_seconds()
            if tid not in leads:
                leads[tid] = {"turn_id": tid, "session_id": turn["session_id"],
                              "created_at": turn["created_at"], "phase": "before" if offset <= 0 else "after",
                              "same_agent": self.owner[turn["session_id"]] == episode["agent_id"],
                              "retrieved_by": [], "source_shard": turn["source_shard"],
                              "screenshot_is_redacted": turn.get("screenshot_is_redacted"),
                              "action_excerpt": excerpt(json.dumps(turn.get("agent_action") or {}, ensure_ascii=False), episode["message"], 800),
                              "output_excerpt": excerpt(turn.get("output") or "", episode["message"], 1500),
                              "error_excerpt": excerpt(turn.get("error") or "", episode["message"], 1000)}
            leads[tid]["retrieved_by"].append("review citation")
        for lead in leads.values():
            lead["record_offset_seconds"] = round((parse_time(lead["created_at"]) - when).total_seconds(), 6)
        return [self.named_lead(e) for e in sorted(leads.values(), key=lambda e: (parse_time(e["created_at"]), e["turn_id"]))]


class Handler(BaseHTTPRequestHandler):
    server: ReviewServer

    def log_message(self, _format, *_args):
        # Search queries can contain gated text; keep them out of terminal logs.
        pass

    def _send(self, body: bytes, mime: str = "application/json", code: int = 200,
              extra_headers: dict | None = None) -> None:
        self.send_response(code)
        self.send_header("Content-Type", mime + ("; charset=utf-8" if mime.startswith("text/") or mime == "application/json" else ""))
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; img-src 'none'; base-uri 'none'; form-action 'none'")
        for key, value in (extra_headers or {}).items():
            self.send_header(key, value)
        self.end_headers()
        self.wfile.write(body)

    def _json(self, value, code: int = 200, extra_headers: dict | None = None) -> None:
        self._send(json.dumps(value, ensure_ascii=False).encode("utf-8"), code=code,
                   extra_headers=extra_headers)

    def _error(self, message: str, code: int = 400) -> None:
        self._json({"error": message}, code=code)

    def _safe_host(self) -> bool:
        return self.headers.get("Host") in {f"127.0.0.1:{self.server.server_port}",
                                            f"localhost:{self.server.server_port}"}

    def do_GET(self):
        if not self._safe_host():
            return self._error("local host only", 403)
        try:
            self.server.sources.check()
            return self._get()
        except ValueError as exc:
            return self._error(str(exc), 409)

    def _get(self):
        parsed = urlparse(self.path)
        path = parsed.path
        if path in {"/", "/review.js", "/review.css"}:
            name = {"/": "review.html", "/review.js": "review.js", "/review.css": "review.css"}[path]
            mime = "text/html" if name.endswith(".html") else "text/javascript" if name.endswith(".js") else "text/css"
            return self._send((WEB / name).read_bytes(), mime)
        if path == "/api/episodes":
            saved = self.server.checked_reviews()
            items = []
            for e in self.server.bundle["episodes"]:
                units = saved.get(e["claim_id"], {}).get("units", [])
                items.append({"claim_id": e["claim_id"], "created_at": e["created_at"],
                              "agent_name": e["agent_name"], "preview": e["message"][:135],
                              "labeled_units": sum(bool(u["status"]) for u in units),
                              "total_units": len(units)})
            return self._json({"items": items, "main_revision": self.server.bundle["main_revision"],
                               "parquet_revision": self.server.bundle["parquet_revision"],
                               "source_card": self.server.bundle["source_card"],
                               "mode": self.server.mode, "queue_seed": self.server.bundle.get("queue_seed"),
                               "bundle_sha256": self.server.bundle_sha256})
        if path.startswith("/api/episode/"):
            cid = path.removeprefix("/api/episode/")
            if cid not in self.server.episodes:
                return self._error("unknown episode", 404)
            review = self.server.checked_reviews().get(cid)
            episode = self.server.episodes[cid]
            return self._json({"episode": {**episode, "evidence": self.server.cited_leads(episode, review)}, "review": review,
                               "revision": revision(review), "integrity": integrity_notice(review),
                               "summary": self.server.summary(episode, review)})
        if path.startswith("/api/turn/"):
            tid = path.removeprefix("/api/turn/")
            turn = self.server.turns.get(tid)
            if turn is None:
                return self._error("unknown turn", 404)
            return self._json({"turn": turn})
        if path == "/api/search":
            args = parse_qs(parsed.query)
            cid = args.get("episode_id", [""])[0]
            if cid not in self.server.episodes:
                return self._error("unknown episode", 404)
            episode = self.server.episodes[cid]
            query = args.get("q", [""])[0].strip()[:500] or episode["message"][:500]
            scope = args.get("scope", ["claimant"])[0]
            phase = args.get("phase", ["before"])[0]
            if scope not in {"claimant", "all"} or phase not in {"before", "after", "both"}:
                return self._error("invalid search filter")
            when = parse_time(episode["created_at"])
            floor, ceiling = when - timedelta(hours=24), when + timedelta(hours=2)
            pool = []
            for turn in self.server.turns.values():
                t = parse_time(turn["created_at"])
                if not floor <= t <= ceiling or is_claim_echo(turn):
                    continue
                if scope == "claimant" and self.server.owner.get(turn["session_id"]) != episode["agent_id"]:
                    continue
                if phase == "before" and t > when or phase == "after" and t <= when:
                    continue
                if not turn_text(turn).strip("{}\n "):
                    continue
                pool.append(turn)
            scores = bm25(query, [turn_text(x)[:5000] for x in pool])
            ranked = sorted(zip(pool, scores), key=lambda x: (-x[1], x[0]["created_at"], x[0]["id"]))
            found = []
            for turn, score in ranked[:20]:
                if score <= 0:
                    break
                found.append({"turn_id": turn["id"], "session_id": turn["session_id"],
                              "created_at": turn["created_at"],
                              "phase": "before" if parse_time(turn["created_at"]) <= when else "after",
                              "same_agent": self.server.owner.get(turn["session_id"]) == episode["agent_id"],
                              "retrieved_by": ["search lexical turn"],
                              "action_excerpt": excerpt(json.dumps(turn.get("agent_action") or {}, ensure_ascii=False), query, 600),
                              "output_excerpt": excerpt(turn.get("output") or "", query),
                              "error_excerpt": excerpt(turn.get("error") or "", query, 650),
                              "screenshot_is_redacted": turn.get("screenshot_is_redacted"),
                              "source_shard": turn["source_shard"], "search_score": score})
            return self._json({"results": [self.server.named_lead(e) for e in found], "candidate_turns": len(pool),
                               "note": "Search returns evidence candidates, not support labels."})
        if path == "/api/export":
            name = {"synthetic_demo": "claimtrail-practice-labels.json", "development_review": "claimtrail-development-labels.json",
                    "ai_assisted_review": "claimtrail-ai-assessments.json",
                    "research": "claimtrail-human-reviews.json"}[self.server.mode]
            return self._json(self.server.checked_reviews(), extra_headers={
                "Content-Disposition": f'attachment; filename="{name}"'})
        return self._error("not found", 404)

    def do_POST(self):
        if not self._safe_host():
            return self._error("local host only", 403)
        origin = self.headers.get("Origin")
        if origin not in {f"http://127.0.0.1:{self.server.server_port}",
                          f"http://localhost:{self.server.server_port}"}:
            return self._error("same-origin request required", 403)
        if self.headers.get("Content-Type", "").split(";", 1)[0] != "application/json":
            return self._error("JSON required", 415)
        path = urlparse(self.path).path
        if not path.startswith("/api/review/"):
            return self._error("not found", 404)
        cid = path.removeprefix("/api/review/")
        if cid not in self.server.episodes:
            return self._error("unknown episode", 404)
        try:
            n = int(self.headers.get("Content-Length", "0"))
            if not 0 < n <= 120_000:
                raise ValueError("review body must be 1–120 KB")
            payload = json.loads(self.rfile.read(n))
            review = validate_review(payload, cid)
            self.server.validate_citations(review)
        except (ValueError, json.JSONDecodeError) as exc:
            return self._error(str(exc))
        try:
            saved = self.server.checked_reviews()
        except ValueError as exc:
            return self._error(str(exc), 409)
        if "base_revision" not in payload or payload["base_revision"] != revision(saved.get(cid)):
            return self._error("This review changed in another tab. Copy your edits, then reload the episode before saving.", 409)
        review["bundle_sha256"] = self.server.bundle_sha256
        review["data_mode"] = self.server.mode
        previous = saved.get(cid)
        review["citations"] = citation_metadata(self.server.episodes[cid], review,
                                                self.server.turns, self.server.owner)
        review["source_files_sha256"] = dict(self.server.sources.hashes)
        review["assessment_policy"] = copy.deepcopy((previous or {}).get(
            "assessment_policy", default_review_policy(self.server.mode)))
        review["provenance_history"] = copy.deepcopy((previous or {}).get("provenance_history", {
            "first_pinned_at_utc": (previous or {}).get("reviewed_at_utc") if previous and "citations" in previous else review["reviewed_at_utc"],
            "legacy_unpinned": previous is not None and "citations" not in previous,
        }))
        if self.server.mode == "synthetic_demo":
            review["source"] = "practice annotation of synthetic demo; not a research label"
        elif self.server.mode == "development_review":
            review["source"] = "annotation of development case; excluded from held-out evaluation"
        elif self.server.mode == "ai_assisted_review":
            review["source"] = "edited in AI-assisted assessment workspace; not independent human validation"
            review["assessment_origin"] = (previous or {}).get("assessment_origin", "AI-assisted; not independent human validation")
        # Check the disk snapshot again just before replacing the labels file.
        try:
            summary = self.server.summary(self.server.episodes[cid], review)
            self.server.sources.check()
        except ValueError as exc:
            return self._error(str(exc), 409)
        saved[cid] = review
        save_reviews(saved, self.server.labels_path)
        return self._json({"saved": True, "reviewed_at_utc": review["reviewed_at_utc"],
                           "revision": revision(review), "integrity": integrity_notice(review),
                           "summary": summary, "assessment_policy": review["assessment_policy"]})


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--bundle", type=Path)
    parser.add_argument("--turns", type=Path, default=DERIVED / "window_turns.jsonl")
    parser.add_argument("--sessions", type=Path, default=ROOT / "data/raw/computer_use_sessions.jsonl")
    parser.add_argument("--labels", type=Path)
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument("--demo", action="store_true", help="use invented examples; requires no dataset or ML packages")
    modes.add_argument("--development", action="store_true", help="inspect the two source-checked development cases; separate from the held-out queue")
    modes.add_argument("--ai-review", action="store_true", help="inspect AI-assisted assessments; never treated as human validation")
    args = parser.parse_args()
    bundle = args.bundle or DERIVED / ("development_bundle.json" if args.development else "review_bundle.json")
    if not args.demo and not bundle.exists():
        parser.error("review bundle missing; run python3 src/review_bundle.py first")
    labels = args.labels or (ROOT / "data/demo/reviews.json" if args.demo else DERIVED / "development_reviews.json" if args.development else DERIVED / "ai_reviews.json" if args.ai_review else LABELS)
    if (args.demo or args.development or args.ai_review) and labels.resolve() == LABELS.resolve():
        parser.error("demo/development/AI annotations must not overwrite human reviews")
    server = ReviewServer(("127.0.0.1", args.port), Handler, bundle, args.turns, labels,
                          args.sessions, args.demo, args.development, args.ai_review)
    print(f"ClaimTrail review: http://127.0.0.1:{server.server_port}/", flush=True)
    print(f"Mode: {server.mode}; labels: {labels} (created only after Save Review)", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
