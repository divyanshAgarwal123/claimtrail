"""Capture configured checks and verify their declared filesystem scope. No ML required."""
from __future__ import annotations

import argparse
import fnmatch
import hashlib
import json
import os
import re
import signal
import stat
import subprocess
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from uuid import uuid4

from cli_paths import allowed_path


RECEIPT = "claimtrail.check-receipt.v1"
OBSERVATION = "claimtrail.scope-observation.v1"


def digest(value) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                     ensure_ascii=False, allow_nan=False).encode()).hexdigest()


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def at(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        raise ValueError("timestamps require an explicit timezone")
    return parsed


def relative(value: str, pattern=False) -> str:
    if not isinstance(value, str) or not value or "\\" in value or "\0" in value:
        raise ValueError("scope paths must be nonempty relative POSIX paths")
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts or path.as_posix() != value or value == ".git" or ".git" in path.parts:
        raise ValueError("scope paths must stay inside the workspace, outside .git")
    if not pattern and any(c in value for c in "*?["):
        raise ValueError("scope roots must be literal paths, not globs")
    return value


def policy(value: dict) -> dict:
    if not isinstance(value, dict) or set(value) - {"check_id", "description", "command", "scope", "exclude", "env", "timeout_seconds"}:
        raise ValueError("unknown or invalid policy fields")
    if not isinstance(value.get("check_id"), str) or not re.fullmatch(r"[a-zA-Z0-9_.-]{1,100}", value["check_id"]):
        raise ValueError("provide a stable check_id")
    command = value.get("command")
    if not isinstance(command, list) or not command or any(not isinstance(s, str) or not s or "\0" in s for s in command):
        raise ValueError("command must be an argv array; no shell interpolation")
    scope, exclude, env = value.get("scope"), value.get("exclude", []), value.get("env", {})
    if not isinstance(scope, list) or not scope or not isinstance(exclude, list):
        raise ValueError("provide literal scope roots and an optional exclude array")
    scope = sorted(set(relative(p) for p in scope))
    exclude = sorted(set(relative(p, pattern=True) for p in exclude))
    if any(root in exclude for root in scope):
        raise ValueError("a scope root cannot be excluded entirely")
    if not isinstance(env, dict) or any(not isinstance(k, str) or not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", k) or
                                        not isinstance(v, str) or "\0" in v for k, v in env.items()):
        raise ValueError("env must map environment variable names to strings")
    env = {**env, "PYTHONDONTWRITEBYTECODE": "1"}
    timeout = value.get("timeout_seconds", 120)
    if type(timeout) not in {int, float} or not 0 < timeout <= 3600:
        raise ValueError("timeout_seconds must be between 0 and 3600")
    description = value.get("description", value["check_id"])
    if not isinstance(description, str) or not description.strip():
        raise ValueError("description must be text")
    return {"check_id": value["check_id"], "description": description, "command": command,
            "scope": scope, "exclude": exclude, "env": env, "timeout_seconds": timeout}


def workspace_id(root: Path) -> str:
    return hashlib.sha256(str(root.resolve()).encode()).hexdigest()


def snapshot(root: Path, spec: dict) -> dict:
    """Hash all files, including untracked/ignored files, except explicit exclusions."""
    root = root.resolve(strict=True)
    found = {}

    def visit(path: Path):
        name = path.relative_to(root).as_posix()
        if ".git" in path.relative_to(root).parts or any(fnmatch.fnmatchcase(name, p) for p in spec["exclude"]):
            return
        if path.is_symlink():
            raise ValueError("symlink in declared scope: " + name)
        try:
            before = path.stat()
        except FileNotFoundError:
            found[name] = {"path": name, "missing": True}
            return
        if stat.S_ISDIR(before.st_mode):
            for child in sorted(path.iterdir()):
                visit(child)
            return
        if not stat.S_ISREG(before.st_mode):
            raise ValueError("non-regular file in scope: " + name)
        if before.st_size > 50_000_000 or len(found) >= 20_000:
            raise ValueError("scope exceeds local capture limits")
        data = path.read_bytes()
        after = path.stat()
        if (before.st_ino, before.st_size, before.st_mtime_ns) != (after.st_ino, after.st_size, after.st_mtime_ns):
            raise ValueError("file changed while hashing: " + name)
        found[name] = {"path": name, "sha256": hashlib.sha256(data).hexdigest(),
                       "bytes": len(data), "executable": bool(after.st_mode & 0o111)}

    for name in spec["scope"]:
        target = root / name
        # Reject symlink ancestors as well as symlink leaves, even if they point inward.
        if any(p.is_symlink() for p in [target, *target.parents] if p != root and root in p.parents):
            raise ValueError("symlink ancestor in declared scope: " + name)
        visit(target)
    files = [found[k] for k in sorted(found)]
    return {"files": files, "sha256": digest(files)}


def seal(value: dict) -> dict:
    return {**value, "sha256": digest({k: v for k, v in value.items() if k != "sha256"})}


def validate_record(value: dict, schema: str):
    if not isinstance(value, dict) or value.get("schema") != schema or value.get("sha256") != seal(value)["sha256"]:
        raise ValueError("invalid or altered " + schema)
    for key in (["before", "after"] if schema == RECEIPT else ["snapshot"]):
        snap = value[key]
        if not isinstance(snap, dict) or not isinstance(snap.get("files"), list) or snap.get("sha256") != digest(snap["files"]):
            raise ValueError("invalid snapshot digest")
        names = []
        for entry in snap["files"]:
            names.append(relative(entry["path"]))
            if not entry.get("missing") and (not re.fullmatch("[0-9a-f]{64}", entry.get("sha256", "")) or
                                             type(entry.get("bytes")) is not int or entry["bytes"] < 0 or
                                             type(entry.get("executable")) is not bool):
                raise ValueError("invalid snapshot entry")
        if names != sorted(set(names)):
            raise ValueError("snapshot entries must be unique and sorted")
    if schema == RECEIPT:
        spec = policy(value["policy"])
        execution = value["execution"]
        if spec != value["policy"] or digest(spec) != value["policy_sha256"]:
            raise ValueError("receipt policy digest mismatch")
        if type(execution.get("timed_out")) is not bool or (execution.get("exit_code") is not None and type(execution["exit_code"]) is not int):
            raise ValueError("invalid process result")
        if at(value["finished_at"]) < at(value["started_at"]):
            raise ValueError("check finished before it started")
    else:
        at(value["observed_at"])


def _output(stream) -> dict:
    stream.seek(0)
    h, length, preview = hashlib.sha256(), 0, b""
    for chunk in iter(lambda: stream.read(65536), b""):
        h.update(chunk); length += len(chunk)
        if len(preview) < 1800:
            preview += chunk[:1800 - len(preview)]
    return {"sha256": h.hexdigest(), "bytes": length, "excerpt": preview.decode("utf-8", errors="replace")}


def run_check(root: Path, spec: dict) -> dict:
    spec = policy(spec)
    root = root.resolve(strict=True)
    before = snapshot(root, spec)
    if not before["files"] or any(e.get("missing") for e in before["files"]):
        raise ValueError("check scope must contain files and all roots must exist")
    started, monotonic = now(), time.monotonic()
    execution = {"exit_code": None, "timed_out": False, "launch_error": None}
    env = {**os.environ, **spec["env"], "PYTHONDONTWRITEBYTECODE": "1"}
    with tempfile.TemporaryFile() as stdout, tempfile.TemporaryFile() as stderr:
        try:
            process = subprocess.Popen(spec["command"], cwd=root, env=env, stdout=stdout, stderr=stderr,
                                       start_new_session=True)
            try:
                execution["exit_code"] = process.wait(timeout=spec["timeout_seconds"])
            except subprocess.TimeoutExpired:
                execution["timed_out"] = True
                if os.name == "posix":
                    os.killpg(process.pid, signal.SIGKILL)
                else:
                    process.kill()
                execution["exit_code"] = process.wait()
        except OSError as exc:
            execution["launch_error"] = str(exc)
        execution.update(stdout=_output(stdout), stderr=_output(stderr),
                         duration_seconds=round(time.monotonic() - monotonic, 6))
    after = snapshot(root, spec)
    return seal({"schema": RECEIPT, "receipt_id": str(uuid4()), "workspace_id": workspace_id(root),
                 "policy": spec, "policy_sha256": digest(spec), "started_at": started,
                 "finished_at": now(), "before": before, "after": after, "execution": execution})


def observe(root: Path, spec: dict, receipt: dict | None) -> dict:
    spec = policy(spec)
    snap = snapshot(root, spec)
    return seal({"schema": OBSERVATION, "workspace_id": workspace_id(root), "policy_sha256": digest(spec),
                 "observed_at": now(), "snapshot": snap,
                 "receipt_sha256": receipt.get("sha256") if receipt else None})


def changed(old: dict, current: dict) -> list[str]:
    left, right = ({e["path"]: e for e in snap["files"]} for snap in (old, current))
    return sorted(p for p in left.keys() | right.keys() if left.get(p) != right.get(p))


def verify(spec: dict, receipt: dict | None, observation: dict) -> dict:
    """Pure, offline replay of a host observation, never a natural-language truth label."""
    spec = policy(spec)
    validate_record(observation, OBSERVATION)
    if observation["policy_sha256"] != digest(spec):
        raise ValueError("observation belongs to another configured policy")

    def result(status, reason, paths=None):
        return {"status": status, "reason": reason, "changed_paths": paths or [],
                "check_id": spec["check_id"], "policy_sha256": digest(spec),
                "observation_sha256": observation["sha256"], "observed_at": observation["observed_at"]}

    if receipt is None:
        return result("missing", "No check receipt was supplied. Importing a transcript does not create one.")
    validate_record(receipt, RECEIPT)
    if observation["receipt_sha256"] != receipt["sha256"]:
        raise ValueError("observation pins a different receipt")
    if receipt["workspace_id"] != observation["workspace_id"]:
        return result("workspace_mismatch", "Receipt came from a different workspace.")
    if receipt["policy_sha256"] != digest(spec):
        return result("scope_mismatch", "Receipt command, declared scope, exclusions or environment differ from the required policy.")
    if at(receipt["finished_at"]) > at(observation["observed_at"]):
        return result("later", "Check finished after this observation; it cannot verify the earlier state.")
    ex = receipt["execution"]
    if ex["timed_out"]:
        return result("timeout", "The configured check timed out.")
    if ex.get("launch_error") or ex["exit_code"] is None:
        return result("unresolved", "The configured check did not produce a completed process result.")
    if ex["exit_code"] != 0:
        return result("failed", f"The configured check exited {ex['exit_code']}.")
    during = changed(receipt["before"], receipt["after"])
    if during:
        return result("changed_during_check", "Declared files changed while the check ran; rerun on a stable scope.", during)
    paths = changed(receipt["after"], observation["snapshot"])
    if paths:
        return result("stale", "Declared files changed after the passing check; its result does not verify this state.", paths)
    if not observation["snapshot"]["files"] or any(e.get("missing") for e in observation["snapshot"]["files"]):
        return result("unresolved", "The declared scope is empty or a required root is missing.")
    return result("verified", "Configured check passed on the same declared file content observed here. This is not semantic or dependency coverage.")


def write_json(path: Path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=".claimtrail-", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(value, stream, indent=2, ensure_ascii=False, allow_nan=False)
            stream.write("\n")
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["run", "verify"])
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--policy", type=Path, required=True, help="Host-chosen policy, not inferred from agent prose")
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--observation", type=Path, help="Save a replayable verification observation")
    args = parser.parse_args()
    try:
        args.repo, args.policy, args.receipt = (allowed_path(p) for p in [args.repo, args.policy, args.receipt])
        if args.observation:
            args.observation = allowed_path(args.observation)
        destinations = [args.receipt, *([args.observation] if args.observation else [])]
        if len({p.resolve() for p in [args.policy, *destinations]}) != 1 + len(destinations):
            raise ValueError("policy, receipt and observation must use separate files")
        spec = policy(json.loads(args.policy.read_text(encoding="utf-8")))
        if args.action == "run":
            receipt = run_check(args.repo, spec)
            write_json(args.receipt, receipt)
        else:
            receipt = json.loads(args.receipt.read_text(encoding="utf-8")) if args.receipt.exists() else None
        observation = observe(args.repo, spec, receipt)
        if args.observation:
            write_json(args.observation, observation)
        verdict = verify(spec, receipt, observation)
        print(json.dumps(verdict))
        return 0 if verdict["status"] == "verified" else 1
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(json.dumps({"status": "invalid", "reason": str(exc)}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
