"""Package captured cases and redacted native sessions; never fabricate outcomes."""
import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from scope_verification import write_json
from verification_report import load_report
from cli_paths import allowed_path
from scope_verification import relative


def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--controlled", type=Path, required=True)
    parser.add_argument("--goose", type=Path, required=True)
    parser.add_argument("--recipe-trials", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.controlled, args.goose, args.recipe_trials, args.output = (
        allowed_path(p) for p in [args.controlled, args.goose, args.recipe_trials, args.output])
    args.output.mkdir(parents=True, exist_ok=False)
    controlled = json.loads(args.controlled.read_text())
    goose = json.loads((args.goose / "report.json").read_text())
    if len(controlled["cases"]) != 30 or len(goose["cases"]) != 6:
        raise ValueError("expected all 30 controlled cases and six completed Goose stages")
    provenance = {"original_controlled_report_sha256": sha(args.controlled),
                  "original_goose_report_sha256": sha(args.goose / "report.json"), "sessions": [],
                  "transformations": ["Replace ClaimTrail and Goose workspace paths in session text with $CLAIMTRAIL and $WORKSPACE.",
                                      "Remove thinking blocks; retain messages, tool IDs, results and process exit codes.",
                                      "Update report source references to the redacted exports; execution receipts and snapshots remain unchanged."],
                  "limits": "Local capture and transformation provenance, not independent authenticity attestation."}
    sessions = args.output / "sessions"; sessions.mkdir()
    for case in goose["cases"]:
        relative(case["id"])
        if case["repository"] not in {"more-itertools", "itsdangerous"}:
            raise ValueError("unknown recorded repository")
        claim = case["goose_claim"]
        relative(claim["session_file"])
        original_path = allowed_path(args.goose / claim["session_file"], root=args.goose)
        original = json.loads(original_path.read_text())
        workspace = str((args.goose / "repos" / case["repository"]).resolve())
        def redact(value):
            if isinstance(value, str): return value.replace(workspace, "$WORKSPACE").replace(str(ROOT), "$CLAIMTRAIL")
            if isinstance(value, list): return [redact(v) for v in value]
            if isinstance(value, dict): return {k: redact(v) for k, v in value.items()}
            return value
        session = redact(original)
        for message in session["conversation"]:
            message["content"] = [c for c in message["content"] if c.get("type") != "thinking"]
        destination = sessions / (case["id"].replace("/", ".") + ".json")
        write_json(destination, session)
        claim["session_file"] = str(destination.relative_to(args.output))
        claim["session_sha256"] = sha(destination)
        claim["text"] = "\n".join(c["text"] for c in session["conversation"][claim["message_index"]]["content"] if c.get("type") == "text")
        stage = case["scenario"].removeprefix("goose_")
        tool_observation = json.loads((args.goose / case["repository"] / (stage + ".tool-observation.json")).read_text())
        # Older local captures need the explicit tool pin added from their original events.
        candidates = []
        for message in original["conversation"]:
            for block in message["content"]:
                if block.get("type") != "toolResponse": continue
                structured = block.get("toolResult", {}).get("value", {}).get("structuredContent", {})
                try: output = json.loads(structured.get("stdout", ""))
                except (ValueError, TypeError): continue
                if output.get("observation_sha256") == tool_observation["sha256"]:
                    candidates.append(block["id"])
        if len(candidates) != 1:
            raise ValueError("cannot uniquely pin the configured checker output")
        case["tool_observation"] = tool_observation
        case["goose_tool_call_id"] = candidates[0]
        provenance["sessions"].append({"file": claim["session_file"], "original_sha256": sha(original_path), "redacted_sha256": sha(destination)})
    trials = json.loads(args.recipe_trials.read_text())
    if [t["returncode"] for t in trials["trials"]] != [0, 1]:
        raise ValueError("native Goose recipe integration did not produce fresh=0, stale=1")
    provenance["original_recipe_trials_sha256"] = sha(args.recipe_trials)
    # Preserve visible stream events and native validation text, never thinking blocks.
    for trial in trials["trials"]:
        visible = []
        for line in trial["stdout"].splitlines():
            try: event = json.loads(line)
            except ValueError:
                visible.append(line); continue
            message = event.get("message")
            if isinstance(message, dict):
                if not message.get("metadata", {}).get("userVisible", True): continue
                message["content"] = [c for c in message.get("content", []) if c.get("type") != "thinking"]
                if not message["content"]: continue
            visible.append(json.dumps(event, ensure_ascii=False))
        trial["stdout"] = "\n".join(visible)
        for key in ["stdout", "stderr"]: trial[key] = trial[key].replace(str(ROOT), "$CLAIMTRAIL")
    write_json(args.output / "recipe-trials.json", trials)
    report = {**controlled, "title": "Scope and freshness: real repository evidence", "cases": controlled["cases"] + goose["cases"],
              "limits": list(dict.fromkeys(controlled["limits"] + goose["limits"] + [
                  "Some exact model responses paraphrase the coverage limit too strongly. The deterministic result is authoritative only for its stated contract."]))}
    write_json(args.output / "report.json", report)
    write_json(args.output / "provenance.json", provenance)
    replayed, _ = load_report(args.output / "report.json")
    if replayed["matching_cases"] != 36:
        raise ValueError("packaged evidence did not replay all expected outcomes")
    print("Packaged and replayed", replayed["matching_cases"], "cases in", args.output)


if __name__ == "__main__": main()
