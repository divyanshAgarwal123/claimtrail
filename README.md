# ClaimTrail

Investigate an agent's completion claim beside recorded computer actions and artifact checks. ClaimTrail separates evidence before the claim from later corroboration, shows actor/time/source context, and keeps unresolved scope visible.

**Start here:** [project overview and exploratory findings](docs/PROJECT_OVERVIEW.md). For a presentation with notes and a rehearsal timer, open `web/presentation.html` locally. Its workbench screenshot is synthetic; the separate research interpretations are explicitly AI-assisted.

## Run in one command

From the extracted repository root:

```bash
python3 -B src/review_app.py --demo --port 8766
```

Open **http://127.0.0.1:8766/**. Python 3.9+ and a local browser are sufficient. No installation, account, model download, API key or dataset access is needed for this mode. Windows users can use `py -3`. Stop the server with Ctrl-C; choose another `--port` if necessary.

Every demo agent, message and action is invented. These examples teach the review workflow and do not establish research results or accuracy. The [two-minute synthetic walkthrough](docs/SYNTHETIC_DEMO.md) explains the source links, before/after filters and save/export flow. The app is designed for one local reviewer process, not public multi-user hosting. Recorded commands are displayed as text and never executed.

## Review a Goose session

```bash
python3 -B src/review_app.py --goose-session examples/goose/local-session.redacted.json --port 8767
```

Open **http://127.0.0.1:8767/**. This redacted example records a real Goose 1.59.0 / local Qwen3 session on a constructed coding task. The agent reported a second test run passing before that run was recorded; a follow-up produced a passing result 118 seconds later. ClaimTrail preserves both messages and the before/after evidence. It does not automatically judge the claims.

The [Goose integration guide](docs/GOOSE_INTEGRATION.md) covers importing your own JSON export and running a new local session. Import and review use the standard library and make no model calls. Creating a new session requires Goose and an already-installed local Ollama model. The recorded example is an integration case, not an accuracy benchmark.

## Verify

```bash
python3 -B -m unittest discover -s tests -v
```

The 29 included tests passed locally with Python site packages disabled. They use invented records, the redacted Goose example, temporary annotations and loopback ports. Tests establish software behavior and source consistency, not the semantic truth of assessments. Hosted CI for this integration has not run.

`DELIVERY_MANIFEST.json` lists the included files, byte counts and SHA-256 hashes; it excludes itself. The redacted local Goose example and its provenance manifest are included. AI Village raw/derived dataset records, real annotations, research screenshots, model weights, credentials and council session logs remain excluded. An aggregate research overview and a synthetic UI screenshot are included.

## Research code and boundaries

The delivery includes the lexical candidate pipeline, identifier matching, review bundle generation, Parquet-window extraction, optional offline MiniLM retrieval, ranking comparison and independent-label evaluator. See [research reproduction](docs/REPRODUCE_RESEARCH.md). Research mode requires separately authorized source files and, for optional extraction/model steps, existing dependencies. The demo remains independent of those dependencies.

The 25 episode assessments were assistant-authored; independent human labels remain absent. The two development interpretations are separate from that queue. Ranking disagreement is not accuracy, later evidence is not proof of earlier success, and temporal proximity is not proof of transmission. The selected export is partial and screenshots were not inspected.

Research source: **AI Digest, “AI Village dataset,” 2026**, [dataset card](https://huggingface.co/datasets/aidigestorg/ai-village). Research/analysis terms, attribution and publication notification apply. No training or fine-tuning was performed. See [project overview](docs/PROJECT_OVERVIEW.md) for revisions and limitations.

Project documentation is AI-assisted. The participant must independently write submission-form responses; this README is project material, not a form-answer draft.
