"""Reproduce controlled scope/freshness cases on two pinned, real OSS repositories."""
from __future__ import annotations

import argparse
import json
import platform
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from scope_verification import observe, policy, run_check, seal, verify, write_json

REPOS = [
    {"id": "more-itertools", "url": "https://github.com/more-itertools/more-itertools.git",
     "revision": "ceafee8ce96f4bc1eb74c528bc247c91d648a0bb",
     "scope": ["more_itertools", "tests", "pyproject.toml", "setup.cfg"],
     "source": "more_itertools/more.py", "test": "tests/test_more.py", "license": "LICENSE",
     "test_args": ["-m", "unittest", "discover", "-s", "tests", "-q"],
     "narrow_args": ["-m", "unittest", "tests.test_more.ChunkedTests", "-q"],
     "regression": "\n# ClaimTrail controlled mutation, not an upstream defect.\nfirst = lambda *args, **kwargs: None\n"},
    {"id": "itsdangerous", "url": "https://github.com/pallets/itsdangerous.git",
     "revision": "672971d66a2ef9f85151e53283113f33d642dabd",
     "scope": ["src", "tests", "pyproject.toml", "uv.lock"],
     "source": "src/itsdangerous/encoding.py", "test": "tests/test_itsdangerous/test_encoding.py", "license": "LICENSE.txt",
     "test_args": ["-m", "pytest", "-q", "-p", "no:cacheprovider"],
     "narrow_args": ["-m", "pytest", "-q", "-p", "no:cacheprovider", "tests/test_itsdangerous/test_encoding.py::test_want_bytes"],
     "regression": "\n# ClaimTrail controlled mutation, not an upstream defect.\nint_to_bytes = lambda num: b''\n"},
]


def prepare(repo: dict, directory: Path) -> Path:
    target = directory / repo["id"]
    if not target.exists():
        subprocess.run(["git", "clone", "--no-checkout", "--filter=blob:none", repo["url"], str(target)], check=True)
        subprocess.run(["git", "-C", str(target), "checkout", "--detach", repo["revision"]], check=True)
    actual = subprocess.check_output(["git", "-C", str(target), "rev-parse", "HEAD"], text=True).strip()
    dirty = subprocess.check_output(["git", "-C", str(target), "status", "--porcelain", "--untracked-files=all"], text=True)
    origin = subprocess.check_output(["git", "-C", str(target), "remote", "get-url", "origin"], text=True).strip()
    if actual != repo["revision"] or dirty or origin != repo["url"]:
        raise ValueError("Use a clean pinned clone; refusing to reset or overwrite " + str(target))
    return target.resolve()


def configured(repo: dict, python: str) -> dict:
    return policy({"check_id": repo["id"] + ".full-tests", "description": "Full upstream test command; declared source, tests and configuration",
                   "command": [python, "-B", *repo["test_args"]], "scope": repo["scope"],
                   "exclude": ["**/__pycache__", "**/.pytest_cache"],
                   "env": {"PYTHONPATH": "src" if repo["id"] == "itsdangerous" else "."}, "timeout_seconds": 120})


def evaluate(repo: dict, directory: Path, spec: dict) -> list[dict]:
    cases = []
    baseline = run_check(directory, spec)
    if baseline["execution"]["exit_code"] != 0:
        raise RuntimeError("Upstream baseline failed: " + baseline["execution"]["stderr"]["excerpt"])

    def add(name, expected, receipt=baseline, required=spec, note="", baseline_rerun=None, observation=None):
        observation = observation or observe(directory, required, receipt)
        result = verify(required, receipt, observation)
        if result["status"] != expected:
            raise AssertionError((repo["id"], name, expected, result))
        cases.append({"id": repo["id"] + "/" + name, "repository": repo["id"], "scenario": name,
                      "kind": "controlled intervention on real repository", "expected": expected, "note": note,
                      "policy": required, "receipt": receipt, "observation": observation,
                      "baseline_rerun": baseline_rerun})
        print(repo["id"], name, "→", result["status"], flush=True)

    add("unchanged_pass", "verified", note="Unmodified pinned upstream source and full test suite.")
    for name, relative in [("source_changed", repo["source"]), ("test_changed", repo["test"]), ("config_changed", "pyproject.toml")]:
        path = directory / relative
        original = path.read_bytes()
        try:
            path.write_bytes(original + b"\n# ClaimTrail benign controlled edit.\n")
            add(name, "stale", note="Even a benign byte change invalidates this content-bound receipt; this is conservative invalidation, not proof of broken behavior.")
        finally:
            path.write_bytes(original)
    added = directory / Path(repo["source"]).parent / "claimtrail_untracked.py"
    try:
        added.write_text("# Controlled untracked addition.\n")
        add("untracked_added", "stale", note="Untracked files inside scope are included regardless of Git status.")
    finally:
        added.unlink(missing_ok=True)
    path = directory / repo["test"]
    original = path.read_bytes()
    try:
        path.unlink()
        add("test_deleted", "stale")
    finally:
        path.write_bytes(original)
    cache = directory / Path(repo["source"]).parent / "__pycache__" / "claimtrail-only.pyc"
    cache.parent.mkdir(exist_ok=True)
    try:
        cache.write_bytes(b"explicitly excluded cache")
        add("excluded_cache", "verified", note="Policy explicitly excludes bytecode caches; they are not asserted as checked.")
    finally:
        cache.unlink()
    readme = directory / ("README.rst" if repo["id"] == "more-itertools" else "README.md")
    original_readme = readme.read_bytes()
    try:
        readme.write_bytes(original_readme + b"\nClaimTrail out-of-scope edit.\n")
        add("outside_declared_scope", "verified", note="README is outside this policy. Verified does not mean the whole repository is covered.")
    finally:
        readme.write_bytes(original_readme)
    path = directory / repo["source"]
    original = path.read_bytes()
    try:
        path.write_bytes(original + repo["regression"].encode())
        failed = run_check(directory, spec)
        if failed["execution"]["exit_code"] == 0:
            raise AssertionError("controlled regression did not fail upstream tests")
        add("regression_after_old_pass", "stale", note="A fresh full-suite baseline also detects the regression. ClaimTrail supplies the invalidated receipt and changed paths; it does not outperform correctly scoped rerunning.", baseline_rerun=failed)
        add("failing_check", "failed", receipt=failed)
        narrow = policy({**spec, "check_id": repo["id"] + ".subset", "command": [spec["command"][0], "-B", *repo["narrow_args"]],
                         "scope": [repo["test"]]})
        partial = run_check(directory, narrow)
        if partial["execution"]["exit_code"] != 0:
            raise AssertionError("narrow negative control unexpectedly failed: " + partial["execution"]["stderr"]["excerpt"])
        add("wrong_check_and_scope", "scope_mismatch", receipt=partial,
            note="An unrelated/narrow check passes despite the controlled regression. It cannot satisfy the configured full-suite policy.", baseline_rerun=partial)
    finally:
        path.write_bytes(original)
    repaired = run_check(directory, spec)
    add("rerun_after_restore", "verified", receipt=repaired, note="Restore upstream content and actually rerun its full tests.")
    wrapper = "import subprocess,sys; from pathlib import Path; r=subprocess.run(" + repr(spec["command"]) + "); p=Path(" + repr(repo["source"]) + "); p.write_bytes(p.read_bytes()+b'\\n# controlled edit during check\\n'); sys.exit(r.returncode)"
    mutating_spec = policy({**spec, "command": [spec["command"][0], "-B", "-c", wrapper]})
    try:
        mutating = run_check(directory, mutating_spec)
        add("changed_during_check", "changed_during_check", receipt=mutating, required=mutating_spec)
    finally:
        path.write_bytes(original)
    add("no_receipt", "missing", receipt=None)
    earlier = observe(directory, spec, None)
    later = run_check(directory, spec)
    earlier = seal({**earlier, "receipt_sha256": later["sha256"]})
    add("later_rerun", "later", receipt=later, observation=earlier,
        note="Observation captured before this rerun. Later passing tests cannot verify the earlier boundary.")
    return cases


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True, help="New output directory")
    parser.add_argument("--repositories", type=Path, default=ROOT / "data/real-repos")
    parser.add_argument("--python", default=sys.executable, help="Python with pytest and freezegun installed")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    report = {"schema": "claimtrail.verification-report.v1", "created_at": datetime.now(timezone.utc).isoformat(),
              "title": "Scope and freshness on real repositories", "python": subprocess.check_output([args.python, "--version"], text=True).strip(),
              "platform": platform.platform(), "repositories": REPOS, "cases": [],
              "limits": ["Controlled interventions, not natural agent failure prevalence or an independent benchmark.",
                         "Verified means this configured command passed on unchanged declared files, not semantic test coverage.",
                         "Local host captures are unsigned; hashes establish consistency, not authenticity against a compromised host.",
                         "External dependencies, services, ignored-by-policy paths and transient edit-and-restore races are outside this contract."]}
    try:
        for repo in REPOS:
            directory = prepare(repo, args.repositories)
            spec = configured(repo, str(Path(args.python).absolute()))
            write_json(args.output / (repo["id"] + ".policy.json"), spec)
            report["cases"].extend(evaluate(repo, directory, spec))
    finally:
        write_json(args.output / "report.json", report)
    print("Report:", args.output / "report.json")


if __name__ == "__main__":
    main()
