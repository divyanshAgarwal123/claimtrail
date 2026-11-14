"""Check actual Goose retry.checks integration with a fresh and stale receipt."""
import argparse
import json
import os
import shlex
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from scope_verification import policy, run_check, write_json
from cli_paths import allowed_path, executable


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--goose", type=Path, required=True)
    p.add_argument("--repo", type=Path, required=True)
    p.add_argument("--policy", type=Path, required=True)
    p.add_argument("--source", required=True, help="Declared source file for a reversible, benign edit")
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    args.output, args.repo, args.policy = (allowed_path(p) for p in [args.output, args.repo, args.policy])
    args.goose = Path(executable(args.goose, "goose"))
    args.output.mkdir(parents=True, exist_ok=False)
    out, repo = args.output.resolve(), args.repo.resolve()
    spec = policy(json.loads(args.policy.read_text()))
    source = repo / args.source
    captured = run_check(repo, spec)
    if not source.resolve().is_relative_to(repo) or args.source not in {e["path"] for e in captured["after"]["files"]}:
        raise ValueError("choose a regular declared source file")
    receipt = out / "receipt.json"
    write_json(receipt, captured)
    gate = [sys.executable, "-B", str(ROOT / "src/scope_verification.py"), "verify", "--repo", str(repo),
            "--policy", str(args.policy.resolve()), "--receipt", str(receipt)]
    recipe = {"version": "1.0.0", "title": "ClaimTrail configured receipt gate", "description": "Native Goose shell success-check integration",
              "prompt": "Reply briefly that this turn is ready for host verification. Do not use tools or edit files. /no_think",
              "instructions": "The host performs verification. Do not claim that you ran tests.",
              "retry": {"max_retries": 1, "timeout_seconds": 30, "checks": [{"type": "shell", "command": shlex.join(gate)}]}}
    write_json(out / "recipe.json", recipe)
    env = {**os.environ, "GOOSE_PATH_ROOT": str(out / "runtime"), "GOOSE_TELEMETRY_ENABLED": "false", "GOOSE_DISABLE_SESSION_NAMING": "true",
           "GOOSE_MODE": "auto", "OLLAMA_HOST": "http://127.0.0.1:11434",
           "CLAIMTRAIL_ALLOWED_ROOT": os.environ.get("CLAIMTRAIL_ALLOWED_ROOT", str(Path.cwd()))}
    original = source.read_bytes()
    trials = []
    try:
        for name in ["fresh", "stale"]:
            if name == "stale": source.write_bytes(original + b"\n# ClaimTrail recipe-gate controlled edit.\n")
            command = [str(args.goose.resolve()), "run", "--no-profile", "--no-session", "--recipe", str(out / "recipe.json"),
                       "--provider", "ollama", "--model", "qwen3:8b", "--max-turns", "2", "--output-format", "stream-json"]
            print("Native Goose recipe", name, flush=True)
            with (out / (name + ".stdout")).open("w") as so, (out / (name + ".stderr")).open("w") as se:
                result = subprocess.run(command, cwd=repo, env=env, stdout=so, stderr=se, timeout=600)
            trials.append({"name": name, "returncode": result.returncode,
                           "stdout": (out / (name + ".stdout")).read_text(), "stderr": (out / (name + ".stderr")).read_text()})
            print(name, "exit", result.returncode, flush=True)
    finally:
        source.write_bytes(original)
        write_json(out / "trials.json", {"trials": trials, "note": "Actual Goose retry.checks runs, with max_retries=1; stale edit is controlled."})
    if trials[0]["returncode"] != 0 or trials[1]["returncode"] == 0:
        raise RuntimeError("Goose recipe results differ from expected fresh/pass and stale/reject; inspect retained logs")


if __name__ == "__main__": main()
