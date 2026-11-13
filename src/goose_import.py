"""Read a Goose JSON session export without executing its recorded commands."""

from __future__ import annotations

import hashlib
import json
import math
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5

from identifier_retrieval import parse_time
from review_bundle import excerpt, proposed_units
from review_provenance import record_phase, source_hash


def _time(value) -> str:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError("Goose message created must be a finite Unix timestamp")
    try:
        return datetime.fromtimestamp(value, timezone.utc).strftime("%Y-%m-%d %H:%M:%S.%f")
    except (ValueError, OverflowError, OSError) as exc:
        raise ValueError("Goose message timestamp is out of range") from exc


def _text(content: list) -> str:
    # Thinking and user prompts are not action evidence or completion claims.
    return "\n".join(c["text"] for c in content
                     if c.get("type") == "text" and isinstance(c.get("text"), str))


def _result(block: dict) -> tuple[str, str, dict]:
    result = block.get("toolResult")
    if not isinstance(result, dict) or result.get("status") not in {"success", "error"}:
        raise ValueError("Invalid Goose toolResult")
    value = result.get("value")
    info = {"result_status": result["status"], "process_exit_code": None,
            "tool_observation": "Tool response recorded"}
    if result["status"] == "error":
        info["tool_observation"] = "Tool returned an error"
        return "", json.dumps(value, ensure_ascii=False), info
    if not isinstance(value, dict):
        raise ValueError("Successful Goose toolResult must contain an object")
    content = value.get("content", [])
    if not isinstance(content, list) or any(not isinstance(c, dict) for c in content):
        raise ValueError("Invalid Goose tool output content")
    structured = value.get("structuredContent")
    structured = structured if isinstance(structured, dict) else {}
    output = structured.get("stdout")
    error = structured.get("stderr")
    output = output if isinstance(output, str) else _text(content)
    error = error if isinstance(error, str) else ""
    code = structured.get("exit_code")
    if code is not None:
        if isinstance(code, bool) or not isinstance(code, int):
            raise ValueError("Goose structured exit_code must be an integer")
        info["process_exit_code"] = code
        info["tool_observation"] = f"Process exit code {code}"
        if value.get("isError") is True:
            info["tool_observation"] += " · tool reported an error"
    elif value.get("isError") is True:
        info["tool_observation"] = "Tool reported an error"
    elif value.get("resultType") not in {None, "complete"}:
        info["tool_observation"] = "Non-final tool response recorded"
    # A success envelope means a response arrived; it does not mean tests passed.
    info["is_error"] = value.get("isError")
    info["result_type"] = value.get("resultType")
    return output, error, info


def import_session(path: Path) -> tuple[dict, list[dict], list[dict]]:
    raw = path.read_bytes()
    try:
        session = json.loads(raw)
    except (ValueError, UnicodeError) as exc:
        raise ValueError("Expected a Goose session JSON export, not a streaming run log") from exc
    if not isinstance(session, dict) or not isinstance(session.get("id"), str) or not session["id"]:
        raise ValueError("Goose export needs a nonempty session id")
    messages = session.get("conversation")
    if not isinstance(messages, list) or not messages:
        raise ValueError("Goose export needs a nonempty conversation array")
    digest = hashlib.sha256(raw).hexdigest()
    sid = session["id"]
    # Session IDs can repeat across isolated Goose databases.
    uid = lambda name: str(uuid5(NAMESPACE_URL, "claimtrail:goose:v1:" + digest + ":" + sid + ":" + name))
    local_sid, actor = uid("session"), uid("agent")
    provider = session.get("provider_name") or "unknown provider"
    model_config = session.get("model_config") or {}
    if not isinstance(model_config, dict):
        raise ValueError("Invalid Goose model_config")
    model = model_config.get("model_name") or "unknown model"
    agent_name = f"Goose · {provider} / {model}"
    requests, responses, claims, turns = {}, {}, [], []
    for mi, message in enumerate(messages):
        if not isinstance(message, dict) or message.get("role") not in {"user", "assistant"}:
            raise ValueError("Invalid Goose conversation message")
        created = _time(message.get("created"))
        content = message.get("content")
        if not isinstance(content, list) or any(not isinstance(c, dict) for c in content):
            raise ValueError("Goose message content must be an array of objects")
        metadata = message.get("metadata") or {}
        if not isinstance(metadata, dict):
            raise ValueError("Invalid Goose message metadata")
        for ci, block in enumerate(content):
            kind = block.get("type")
            if kind not in {"toolRequest", "toolResponse"}:
                continue
            if not isinstance(block.get("id"), str) or not block["id"]:
                raise ValueError("Goose tool event needs a nonempty id")
            event = {"block": block, "created_at": created, "sequence": [mi, ci],
                     "message_id": message.get("id")}
            pool = requests if kind == "toolRequest" else responses
            if block["id"] in pool:
                raise ValueError("Duplicate Goose " + kind + " id: " + block["id"])
            pool[block["id"]] = event
        text = _text(content)
        if message["role"] == "assistant" and text.strip() and metadata.get("userVisible", True):
            # Keep the whole message for review, including text alongside a tool call.
            claims.append({"claim_id": uid(f"message:{mi}"), "agent_id": actor,
                           "agent_name": agent_name, "created_at": created, "message": text,
                           "source_sequence": [mi, 0], "source_sequence_scope": digest,
                           "goose_message_id": message.get("id"),
                           "proposed_units": proposed_units(text), "baseline_top3_sessions": [],
                           "identifiers": [], "evidence": []})
    for call_id in requests.keys() | responses.keys():
        request, response = requests.get(call_id), responses.get(call_id)
        if request and response and response["sequence"] <= request["sequence"]:
            raise ValueError("Goose tool response precedes its request")
        event = response or request
        action = {"action": "goose_tool_call", "tool_call_id": call_id}
        if request:
            call = request["block"].get("toolCall")
            if not isinstance(call, dict) or call.get("status") not in {"success", "error"}:
                raise ValueError("Invalid Goose toolCall")
            value = call.get("value")
            if call["status"] == "success":
                if not isinstance(value, dict) or not isinstance(value.get("name"), str):
                    raise ValueError("Goose toolCall needs a tool name")
                action.update(tool_name=value["name"], arguments=value.get("arguments"))
            else:
                action["request_error"] = value
        else:
            action["action"] = "goose_orphan_tool_response"
        output, error, info = _result(response["block"]) if response else (
            "", "", {"tool_observation": "No result recorded", "process_exit_code": None})
        turns.append({"id": uid("call:" + call_id), "session_id": local_sid,
                      "created_at": event["created_at"], "agent_action": action,
                      "output": output, "error": error, "source_shard": path.name,
                      "screenshot_is_redacted": False, "has_redaction_been_overruled": False,
                      "source_sequence": event["sequence"], "source_sequence_scope": digest,
                      "goose": {"tool_call_id": call_id, "request": request, "response": response,
                                "request_missing": request is None, **info}})
    turns.sort(key=lambda t: t["source_sequence"])
    if not claims:
        raise ValueError("No visible assistant text to review in this Goose export")
    for claim in claims:
        when = parse_time(claim["created_at"])
        for turn in turns:
            if not when - timedelta(hours=24) <= parse_time(turn["created_at"]) <= when + timedelta(hours=2):
                continue
            action = json.dumps(turn["agent_action"], ensure_ascii=False)
            claim["evidence"].append({"turn_id": turn["id"], "session_id": local_sid,
                "created_at": turn["created_at"], "phase": record_phase(turn, claim), "same_agent": True,
                "retrieved_by": ["goose session tool record"], "source_shard": path.name,
                "action_excerpt": excerpt(action, claim["message"], 800),
                "output_excerpt": excerpt(turn["output"], claim["message"], 1500),
                "error_excerpt": excerpt(turn["error"], claim["message"], 1500),
                "tool_observation": turn["goose"]["tool_observation"],
                "process_exit_code": turn["goose"]["process_exit_code"],
                "source_record_sha256": source_hash(turn)})
    bundle = {"data_mode": "goose_session", "source_card": "Local Goose JSON session export",
              "main_revision": digest, "parquet_revision": "not applicable", "queue_seed": None,
              "source_description": f"Goose session {sid} · {provider} / {model} · SHA-256 {digest}",
              "goose_session_id": sid, "episodes": claims}
    sessions = [{"id": local_sid, "agent_id": actor, "created_at": _time(messages[0]["created"])}]
    return bundle, turns, sessions
