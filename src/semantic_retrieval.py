"""Offline, pretrained MiniLM comparison on the *same* eligible session goals as BM25.

This script does inference only. It does not train/fine-tune on AI Village data,
make API calls, or classify claim truth. The model must already exist locally.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / ".deps"))
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"

import numpy as np  # noqa: E402
import torch  # noqa: E402
from transformers import AutoModel, AutoTokenizer  # noqa: E402

from claimtrail import eligible_sessions, rows, write_jsonl


MODEL_ID = "sentence-transformers/all-MiniLM-L6-v2"
MODEL_REVISION = "c9745ed1d9f207416be6d2e6f8de32d1f16199bf"
MODEL_PATH = (Path.home() / ".cache/huggingface/hub/models--sentence-transformers--all-MiniLM-L6-v2"
              / "snapshots" / MODEL_REVISION)


def local_model(path: Path = MODEL_PATH):
    if not (path / "model.safetensors").is_file() or not (path / "tokenizer.json").is_file():
        raise FileNotFoundError(f"cached MiniLM snapshot unavailable: {path}")
    tokenizer = AutoTokenizer.from_pretrained(str(path), local_files_only=True)
    model = AutoModel.from_pretrained(str(path), local_files_only=True)
    model.eval()
    return tokenizer, model


def embed(texts: list[str], tokenizer, model, batch_size: int = 32) -> np.ndarray:
    """Mean-pool the cached SentenceTransformers model, then L2-normalize."""
    vectors = []
    with torch.inference_mode():
        for offset in range(0, len(texts), batch_size):
            batch = texts[offset:offset + batch_size]
            encoded = tokenizer(batch, padding=True, truncation=True, max_length=256, return_tensors="pt")
            hidden = model(**encoded).last_hidden_state
            mask = encoded["attention_mask"].unsqueeze(-1)
            pooled = (hidden * mask).sum(dim=1) / mask.sum(dim=1).clamp(min=1)
            pooled = torch.nn.functional.normalize(pooled, p=2, dim=1)
            vectors.append(pooled.cpu().numpy())
    return np.concatenate(vectors, axis=0).astype("float32") if vectors else np.empty((0, 384), dtype="float32")


def rank_session_candidates(claim: dict, sessions: list[dict], session_vectors: np.ndarray,
                            claim_vector: np.ndarray, top_k: int = 3) -> dict:
    eligible = eligible_sessions(claim, sessions)
    id_to_position = {s["id"]: i for i, s in enumerate(sessions)}
    ranked = []
    for s in eligible:
        score = float(session_vectors[id_to_position[s["id"]]] @ claim_vector)
        ranked.append((s, score))
    ranked.sort(key=lambda x: (-x[1], x[0]["created_at"], x[0]["id"]))
    return {"claim_id": claim["id"], "candidates_24h": len(eligible),
            "top3": [{"session_id": s["id"], "created_at": s["created_at"],
                      "score": round(score, 6), "short_goal": s.get("short_displayed_session_goal")}
                     for s, score in ranked[:top_k]]}


def main():
    derived = ROOT / "data/derived"
    claims = list(rows(derived / "candidate_claims.jsonl"))
    sessions = list(rows(derived / "window_sessions.jsonl"))
    if len({s["id"] for s in sessions}) != len(sessions):
        raise ValueError("duplicate session IDs")
    torch.set_num_threads(min(4, os.cpu_count() or 1))
    tokenizer, model = local_model()
    session_texts = [(s.get("short_displayed_session_goal") or "") + " " + (s.get("session_goal") or "")
                     for s in sessions]
    session_vectors = embed(session_texts, tokenizer, model)
    claim_vectors = embed([c["content"] for c in claims], tokenizer, model)
    results = [rank_session_candidates(c, sessions, session_vectors, claim_vectors[i])
               for i, c in enumerate(claims)]
    write_jsonl(derived / "semantic_links.jsonl", results)
    np.savez_compressed(derived / "semantic_session_vectors.npz",
                        vectors=session_vectors, session_ids=np.array([s["id"] for s in sessions]))
    print(json.dumps({"model": MODEL_ID, "model_revision": MODEL_REVISION,
                      "mode": "offline pretrained inference, mean pooling, max 256 tokens",
                      "claims": len(claims), "sessions": len(sessions),
                      "semantic_links": str(derived / "semantic_links.jsonl")}))


if __name__ == "__main__":
    main()
