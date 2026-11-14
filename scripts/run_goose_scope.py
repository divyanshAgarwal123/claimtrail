"""Exercise receipt run/verify through real Goose shell tools on pinned OSS repos."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shlex
import subprocess
import sys
from pathlib import Path

from run_scope_examples import REPOS, ROOT, configured, prepare
sys.path.insert(0, str(ROOT / "src"))
from scope_verification import at, now, observe, verify, write_json


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--goose", type=Path, required=True)
    parser.add_argument("--python", type=Path, required=True)
    parser.add_argument("--model", default="qwen3:8b")
    args = parser.parse_args()
    output = args.output.resolve(); output.mkdir(parents=True, exist_ok=False)
    goose, python = str(args.goose.resolve()), str(args.python.absolute())
    env = {**os.environ, "GOOSE_PATH_ROOT": str(output / "runtime"), "GOOSE_MODE": "auto",
           "GOOSE_DISABLE_SESSION_NAMING": "true", "GOOSE_TELEMETRY_ENABLED": "false",
           "OLLAMA_HOST": "http://127.0.0.1:11434", "PYTHONDONTWRITEBYTECODE": "1"}
    report = {"schema": "claimtrail.verification-report.v1", "title": "Goose using scope and freshness receipts",
              "repositories": REPOS, "cases": [], "limits": [
                  "Real Goose 1.59.0 / local Qwen3:8b tool sessions; one session per repository.",
                  "The stale stage is a disclosed host-controlled edit, not an organic agent failure.",
                  "Observations in this report are post-session host snapshots, not retrospective proof of claim-time state.",
                  "No independent human review, dependency attestation or semantic coverage claim."]}
    try:
        for repo in REPOS:
            directory = prepare(repo, output / "repos")
            spec = configured(repo, python)
            path = output / repo["id"]; path.mkdir()
            policy_path, receipt_path, observation_path = [path / (n + ".json") for n in ["policy", "receipt", "observation"]]
            write_json(policy_path, spec)
            original = (directory / repo["source"]).read_bytes()
            name = "claimtrail-scope-" + repo["id"]
            previous_count = 0
            try:
                for index, (stage, action, expected) in enumerate([
                        ("fresh", "run", "verified"), ("after_edit", "verify", "stale"), ("rerun", "run", "verified")]):
                    if stage == "after_edit":
                        (directory / repo["source"]).write_bytes(original + b"\n# ClaimTrail disclosed host edit after the passing check.\n")
                    elif stage == "rerun":
                        (directory / repo["source"]).write_bytes(original)
                    command = [python, "-B", str(ROOT / "src/scope_verification.py"), action, "--repo", str(directory),
                               "--policy", str(policy_path), "--receipt", str(receipt_path), "--observation", str(observation_path)]
                    context = "A host has deliberately edited a source file since the earlier passing check. " if stage == "after_edit" else ""
                    prompt = (context + "Use the shell tool to execute exactly this configured verification command once, wait for the completed result, "
                              "then report its actual status and any changed paths. Do not edit files, install packages, use the network, or commit. "
                              "Do not replace this command with your own test command. A nonzero verify exit is an expected reportable outcome.\n" + shlex.join(command) + "\n/no_think")
                    argv = [goose, "run", "--no-profile", "--with-builtin", "developer", "--provider", "ollama", "--model", args.model,
                            "--max-turns", "6", "--max-tool-repetitions", "2", "--output-format", "stream-json", "--name", name, "--text", prompt]
                    if index: argv.append("--resume")
                    stage_started = now()
                    previous_receipt = json.loads(receipt_path.read_text())["sha256"] if receipt_path.exists() else None
                    print("Goose", repo["id"], stage, flush=True)
                    with (path / (stage + ".log")).open("w") as so, (path / (stage + ".stderr")).open("w") as se:
                        result = subprocess.run(argv, cwd=directory, env=env, stdout=so, stderr=se, timeout=600)
                    exported = path / (stage + ".session.json")
                    subprocess.run([goose, "session", "export", "--name", name, "--format", "json", "--output", str(exported)], env=env, check=True, timeout=30, capture_output=True)
                    if result.returncode or not receipt_path.exists() or not observation_path.exists():
                        raise RuntimeError(f"Goose stage incomplete: {repo['id']} {stage}; inspect retained logs")
                    receipt = json.loads(receipt_path.read_text())
                    tool_observation = json.loads(observation_path.read_text())
                    if at(tool_observation["observed_at"]) < at(stage_started) or (action == "run" and receipt["sha256"] == previous_receipt):
                        raise RuntimeError("Goose did not produce a new stage result")
                    host_observation = observe(directory, spec, receipt)
                    verdict = verify(spec, receipt, host_observation)
                    if verdict["status"] != expected:
                        raise AssertionError((repo["id"], stage, verdict))
                    write_json(path / (stage + ".receipt.json"), receipt)
                    write_json(path / (stage + ".tool-observation.json"), json.loads(observation_path.read_text()))
                    write_json(path / (stage + ".host-observation.json"), host_observation)
                    session = json.loads(exported.read_text())
                    new_messages = session["conversation"][previous_count:]
                    calls = [c for m in new_messages for c in m["content"] if c.get("type") == "toolRequest" and
                             c.get("toolCall", {}).get("value", {}).get("name") == "shell" and
                             shlex.join(command) in c["toolCall"]["value"].get("arguments", {}).get("command", "")]
                    if not calls:
                        raise RuntimeError("Configured command is absent from this stage's Goose tool requests")
                    previous_count = len(session["conversation"])
                    visible = [(i, m) for i, m in enumerate(session["conversation"]) if m["role"] == "assistant" and any(c.get("type") == "text" for c in m["content"])]
                    mi, message = visible[-1]
                    report["cases"].append({"id": repo["id"] + "/goose_" + stage, "repository": repo["id"], "scenario": "goose_" + stage,
                        "kind": "Goose tool session" if stage == "fresh" else "Goose session with controlled edit/restore",
                        "expected": expected, "note": "Host observation taken after Goose returned. The exact model message is a source record, not a truth label.",
                        "policy": spec, "receipt": receipt, "observation": host_observation, "baseline_rerun": None,
                        "tool_observation": tool_observation, "goose_tool_call_id": calls[-1]["id"],
                        "goose_claim": {"message_index": mi, "message_id": message.get("id"), "created": message["created"],
                                        "text": "\n".join(c["text"] for c in message["content"] if c.get("type") == "text"),
                                        "session_file": str(exported.relative_to(output)),
                                        "session_sha256": hashlib.sha256(exported.read_bytes()).hexdigest()}})
                    write_json(output / "report.json", report)
                    print(repo["id"], stage, "→", verdict["status"], flush=True)
            finally:
                (directory / repo["source"]).write_bytes(original)
    finally:
        write_json(output / "report.json", report)


if __name__ == "__main__":
    main()
