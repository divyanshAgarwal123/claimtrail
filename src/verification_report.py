"""Validate and replay a captured verification report without running its commands."""
import hashlib
import json
from pathlib import Path

from scope_verification import RECEIPT, validate_record, verify


def load_report(path: Path) -> tuple[dict, dict[str, Path]]:
    report = json.loads(path.read_text())
    if report.get("schema") != "claimtrail.verification-report.v1" or not isinstance(report.get("cases"), list) or not report["cases"]:
        raise ValueError("expected a nonempty ClaimTrail verification report")
    seen, sources, cases = set(), {}, []
    for case in report["cases"]:
        cid = case["id"]
        if not isinstance(cid, str) or cid in seen:
            raise ValueError("invalid or duplicate verification case id")
        seen.add(cid)
        result = verify(case["policy"], case.get("receipt"), case["observation"])
        baseline = case.get("baseline_rerun")
        if baseline is not None:
            validate_record(baseline, RECEIPT)
        claim = case.get("goose_claim")
        if claim:
            session_path = path.parent / claim["session_file"]
            if not session_path.resolve().is_relative_to(path.parent.resolve()):
                raise ValueError("Goose session must be inside the report directory")
            raw = session_path.read_bytes()
            if hashlib.sha256(raw).hexdigest() != claim["session_sha256"]:
                raise ValueError("Goose session source changed")
            session = json.loads(raw)
            message = session["conversation"][claim["message_index"]]
            text = "\n".join(c["text"] for c in message["content"] if c.get("type") == "text")
            if message["role"] != "assistant" or text != claim["text"] or message.get("id") != claim["message_id"] or message["created"] != claim["created"]:
                raise ValueError("Goose claim differs from the pinned source message")
            if case.get("tool_observation"):
                tool_result = verify(case["policy"], case["receipt"], case["tool_observation"])
                responses = [c for m in session["conversation"] for c in m["content"] if c.get("type") == "toolResponse" and c.get("id") == case["goose_tool_call_id"]]
                if len(responses) != 1:
                    raise ValueError("expected exactly one pinned Goose tool response")
                value = responses[0]["toolResult"]["value"]
                structured = value.get("structuredContent", {})
                stdout = structured.get("stdout", "")
                if json.loads(stdout.strip()) != tool_result or structured.get("exit_code") != (0 if tool_result["status"] == "verified" else 1):
                    raise ValueError("Goose tool output differs from replayed verification")
            sources[claim["session_file"]] = session_path
        cases.append({**case, "result": result, "matches_expected": result["status"] == case["expected"]})
    return {**report, "cases": cases, "replayed_cases": len(cases),
            "matching_cases": sum(c["matches_expected"] for c in cases)}, sources


if __name__ == "__main__":
    import argparse
    from cli_paths import allowed_path
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report", type=Path)
    args = parser.parse_args()
    report, _ = load_report(allowed_path(args.report))
    print(json.dumps({"cases": report["replayed_cases"], "matching": report["matching_cases"],
                      "note": "Deterministic contract replay, not an independent accuracy benchmark."}))
    raise SystemExit(0 if report["replayed_cases"] == report["matching_cases"] else 1)
