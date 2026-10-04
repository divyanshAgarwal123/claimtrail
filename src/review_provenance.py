"""Canonical citation pins and local source-change checks; standard library only."""
from __future__ import annotations

import hashlib
import json
from datetime import timedelta
from pathlib import Path

from identifier_retrieval import is_claim_echo, parse_time


class SourceIntegrityError(ValueError):
    """A saved pin or the running source snapshot no longer matches."""


def source_hash(turn: dict) -> str:
    return hashlib.sha256(json.dumps(turn, ensure_ascii=False, sort_keys=True).encode()).hexdigest()


def citation_metadata(episode: dict, review: dict, turns: dict, owners: dict) -> dict:
    when = parse_time(episode["created_at"])
    checked = {}
    for tid in sorted({tid for unit in review["units"] for tid in unit["evidence_ids"]}):
        turn = turns.get(tid)
        if turn is None:
            raise ValueError("unknown cited turn: " + tid)
        if is_claim_echo(turn):
            raise ValueError("circular chat-send turns cannot serve as action/output evidence")
        at = parse_time(turn["created_at"])
        if not when - timedelta(hours=24) <= at <= when + timedelta(hours=2):
            raise ValueError("cited turn lies outside the review window (24h before to 2h after)")
        if turn["session_id"] not in owners:
            raise ValueError("citation has no known session owner")
        checked[tid] = {
            "source_record_sha256": source_hash(turn), "session_id": turn["session_id"],
            "actor_id": owners[turn["session_id"]], "created_at": turn["created_at"],
            "same_agent": owners[turn["session_id"]] == episode["agent_id"],
            "phase": "before" if at <= when else "after",
            "record_offset_seconds": round((at - when).total_seconds(), 6),
        }
    return checked


def default_review_policy(mode: str) -> dict:
    return {
        "origin": "Local review interface; policy recorded from this save onward",
        "independent_human_validation": False,
        "mode": mode,
        "assessment_time": "Assess support at claim time; distinguish later corroboration.",
        "limits": ["Missing evidence does not establish failure.",
                   "Record timing does not prove transmission or execution duration.",
                   "Source hashes check consistency, not the correctness of a judgment."],
    }


def integrity_notice(review: dict | None) -> dict:
    if review is None:
        return {"status": "unsaved", "message": "No saved assessment. Sources will be pinned when you save."}
    if "citations" not in review:
        return {"status": "legacy_unpinned", "message": "Earlier assessment has no source hashes. Its historical source content cannot be verified; saving will pin only the current records."}
    history = review.get("provenance_history", {})
    suffix = " Earlier unpinned source content cannot be verified." if history.get("legacy_unpinned") else ""
    return {"status": "verified", "message": "Saved citation hashes, actor and time match the loaded source records." + suffix}


class SourceSnapshot:
    """Hash inputs once; rehash if filesystem identity or metadata changes.

    Pins are integrity checks for an ordinary local workspace, not tamper-proof
    authentication against a process capable of modifying this application.
    """
    def __init__(self, paths: dict[str, Path]):
        self.paths = paths
        self.hashes, self.stamps = {}, {}
        for name, path in paths.items():
            self.hashes[name], self.stamps[name] = self._read(path)

    @staticmethod
    def _stamp(path: Path) -> tuple:
        s = path.stat()
        return s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns, s.st_ctime_ns

    @classmethod
    def _read(cls, path: Path) -> tuple[str, tuple]:
        before = cls._stamp(path)
        digest = hashlib.sha256()
        with path.open("rb") as fh:
            for chunk in iter(lambda: fh.read(1024 * 1024), b""):
                digest.update(chunk)
        after = cls._stamp(path)
        if before != after:
            raise SourceIntegrityError("Source changed while loading; restore verified inputs and restart.")
        return digest.hexdigest(), after

    def check(self) -> None:
        for name, path in self.paths.items():
            try:
                if self._stamp(path) == self.stamps[name]:
                    continue
                digest, stamp = self._read(path)
                if digest != self.hashes[name]:
                    raise SourceIntegrityError("Source file changed (" + name + "); restore verified inputs and restart. No review was saved.")
                self.stamps[name] = stamp
            except OSError as exc:
                raise SourceIntegrityError("Source file unavailable (" + name + "); restore verified inputs and restart.") from exc
