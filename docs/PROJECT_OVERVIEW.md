# ClaimTrail — from completion claims to evidence

ClaimTrail helps investigators check whether an AI agent’s completion message is supported by recorded computer actions and artifacts. Its local workbench separates observations before the message from later corroboration, preserving the scope of repository, deployment and browser evidence.

Investigators can navigate episodes, filter by actor and time, search records, follow commit/PR identifiers and inspect full sources. Linked summaries highlight assertions, observations and unresolved questions. Reviewers can annotate claim units, cite evidence and export assessments. Saves preserve provenance, check source hashes and reject conflicting updates.

An exploratory **AI-assisted review of 25 selected episodes** produced 64 claim units with 74 distinct non-chat source citations. Two separate development investigations illustrate the workflow:

- **Repository presence versus live state:** integration was supported in repository records, while live state at claim time remained unresolved. A collaborator’s local-source check occurred 0.278 seconds later.
- **Eventual success versus earlier timing:** a rejected push and successful rebase were followed by remote corroboration 18.620 seconds after the claim. The earlier successful-push timing remained unverified.

The public demo includes three invented teaching cases and runs with Python 3.9+ and a local browser:

```bash
python3 -B src/review_app.py --demo --port 8766
```

Open http://127.0.0.1:8766/. The demo needs no dataset access or package installation. [Research instructions](REPRODUCE_RESEARCH.md) describe the separately authorized input path.

Reliability checks passed: **32 project tests, 23 tests in the delivered package and nine Chromium check groups**, including save/reload, conflicting edits and source-change rejection. The public repository’s automated tests also passed.

The research uses a partial export; screenshots were not inspected and independent human validation is absent. The assessments establish no accuracy or agent failure rate. Timestamp offsets describe record ordering, not transmission delays. Missing records leave questions unresolved. The published package excludes gated records and real annotations.

Source: **AI Digest, “AI Village dataset,” 2026**, [dataset card](https://huggingface.co/datasets/aidigestorg/ai-village). Pinned revisions and file hashes are in [the provenance manifest](provenance.json). No training or fine-tuning was performed.
