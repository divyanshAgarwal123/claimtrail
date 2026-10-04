# Research reproduction with separate authorized inputs

The runnable synthetic demo needs no research files. This optional path reconstructs candidate extraction, baseline/identifier retrieval, review bundles and the semantic session comparison. It requires approved AI Village access and the pinned files listed in `docs/provenance.json`. The delivery contains metadata and code, not those source files or original assessments.

Keep source files in `data/raw/` and outputs in `data/derived/`; both are ignored. For JSONL entries, the manifest hashes expanded copies, not the downloaded gzip containers. The ten `turns-0000.parquet` through `turns-0009.parquet` files are a partial converted export. This path does not download or log into anything.

Run from the repository root after providing the authorized files:

```bash
python3 -B src/claimtrail.py
# Extraction needs DuckDB 1.3.2 already installed in the environment or .deps:
python3 -B src/extract_turns.py
python3 -B src/identifier_retrieval.py
python3 -B src/review_bundle.py
python3 -B src/review_app.py --port 8765
```

`claimtrail.py` fixes the chat window to May 5–9, 2026 UTC, a shared-goal room, seed `20261003` and a maximum six sampled episodes per actor. Sessions and extracted turns include a May 4 lead-in. Two development IDs are excluded from the queue. Generic bundle generation creates review leads and editable suggestions; it does not create independent labels. Use a fresh working directory for a new analysis instead of overwriting saved annotations.

For the optional semantic comparison, NumPy/PyTorch and the versions in `requirements-semantic.txt` must already be available. The cached MiniLM revision must match `docs/model_provenance.json`; model weights are absent. The script forces offline mode and fails if its local snapshot is missing. No external model call or training occurs.

```bash
python3 -B src/semantic_retrieval.py
python3 -B src/retrieval_comparison.py
python3 -B src/audit_project.py
python3 -B src/evaluate_reviews.py
```

Without independent human labels, the evaluator reports pending review and computes no accuracy score. Source hashes in the manifest identify the original local copies; they do not authenticate semantic conclusions. Session-goal texts are agent statements, not independent outcome evidence.

The original assistant decisions, real development guides/anchor snippets and turn-ablation outputs are not included. Consequently this delivery does not claim to reproduce the complete assistant review or its case interpretations from public inputs alone. Authorized source access and further independent review are needed to inspect those findings. The included code makes the main retrieval/reviewer pipeline inspectable without redistributing gated records.

Dataset terms: research/analysis; no training/fine-tuning without written permission; no re-identification; AI Digest / AI Village attribution and publication notification. [AI Village dataset card](https://huggingface.co/datasets/aidigestorg/ai-village).
