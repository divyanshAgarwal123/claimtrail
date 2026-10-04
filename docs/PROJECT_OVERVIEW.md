# ClaimTrail — from completion claims to evidence

ClaimTrail is a local investigation workbench for tracing AI agents’ completion messages to recorded computer actions and artifacts. It brings messages, tool outputs and artifact checks into an inspectable timeline, with actor identity and claim-relative timestamps attached to each record.

Investigators can navigate episodes, search records, filter by actor and time, follow commit and pull-request identifiers, and open full sources. Linked summaries organize the assertion and its supporting context. Individual claim units can be annotated, connected to source citations and exported with their assessment rationale.

Separate before-and-after lanes preserve the sequence of events across collaborating agents. Repository operations, deployment checks and browser-related records retain their own source context, allowing an investigator to follow each stage of a task through the recorded workflow. Saved citations appear directly in the timeline and open their original records.

The application includes provenance-preserving saves, source-hash checks, conflict detection and structured exports. It checks citation IDs, record ownership and timestamp boundaries, preserves assessment origin and policy, and protects saved annotations when a source changes or another tab has saved a newer version.

The public demo contains three invented teaching cases and runs with Python 3.9+ and a local browser:

```bash
python3 -B src/review_app.py --demo --port 8766
```

Open http://127.0.0.1:8766/. The demo uses Python’s standard library and requires no account or package installation. [Research instructions](REPRODUCE_RESEARCH.md) describe the authorized dataset workflow and included analysis scripts.

Executed software checks passed: **32 project tests, 23 tests in the delivered package and nine Chromium check groups**, covering citation save/reload, conflicting edits, narrow layouts and source-change rejection. GitHub’s automated tests also passed.

Research source: **AI Digest, “AI Village dataset,” 2026**, [dataset card](https://huggingface.co/datasets/aidigestorg/ai-village). Pinned revisions and file hashes are recorded in [the provenance manifest](provenance.json). No training or fine-tuning was performed.
