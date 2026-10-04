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

## Verify

```bash
python3 -B -m unittest discover -s tests -v
```

The 23 included tests passed in this candidate with Python site packages disabled. They use invented records, temporary annotations and loopback ports. The broader local project passed 32 tests and nine Chromium check groups. Tests establish software behavior and source consistency, not the semantic truth of assessments. Hosted CI is prepared but has not run yet.

`DELIVERY_MANIFEST.json` lists the included files, byte counts and SHA-256 hashes; it excludes itself. No raw/derived dataset records, real annotations, research screenshots, model weights, credentials or council session logs are included. An aggregate research overview and a synthetic UI screenshot are included.

## Research code and boundaries

The delivery includes the lexical candidate pipeline, identifier matching, review bundle generation, Parquet-window extraction, optional offline MiniLM retrieval, ranking comparison and independent-label evaluator. See [research reproduction](docs/REPRODUCE_RESEARCH.md). Research mode requires separately authorized source files and, for optional extraction/model steps, existing dependencies. The demo remains independent of those dependencies.

The 25 episode assessments were assistant-authored; independent human labels remain absent. The two development interpretations are separate from that queue. Ranking disagreement is not accuracy, later evidence is not proof of earlier success, and temporal proximity is not proof of transmission. The selected export is partial and screenshots were not inspected.

Research source: **AI Digest, “AI Village dataset,” 2026**, [dataset card](https://huggingface.co/datasets/aidigestorg/ai-village). Research/analysis terms, attribution and publication notification apply. No training or fine-tuning was performed. See [project overview](docs/PROJECT_OVERVIEW.md) for revisions and limitations.

Project documentation is AI-assisted. The participant must independently write submission-form responses; this README is project material, not a form-answer draft.
