# Goose session integration

ClaimTrail imports JSON exported by Goose and displays assistant messages beside
their recorded tool calls and results. The integration was exercised with Goose
1.59.0 and an existing local Ollama `qwen3:8b` model on 14 November 2026 in India.
It requires no Python packages. Importing and reviewing a session makes no model
requests and never executes recorded commands.

## Review the recorded example

From the repository root:

```bash
python3 -B src/review_app.py \
  --goose-session examples/goose/local-session.redacted.json --port 8767
```

Open http://127.0.0.1:8767/. The example contains real model messages and tool
results from a deliberately constructed two-test coding task. The workspace path
was replaced with `$WORKSPACE` and thinking blocks were removed for distribution.
[The provenance manifest](../examples/goose/local-session.provenance.json) records
the original and redacted export hashes and the transformations. Hashes establish
consistency, not independent authenticity or verification accuracy.

In the first message, Goose says that a second test run passed. Before that
message, the export records only a failed test command (exit 1) and a file edit.
A follow-up explicitly requested another test run. That recorded run exited 0,
118 seconds after the earlier message. ClaimTrail keeps it in **Later evidence**
for the first message and **Before / at claim** for the second message.

Use the Time filter to compare these views. Open **Full record** to inspect the
original request, response, and structured process exit code. An outer
`toolResult.status: success` can contain `exit_code: 1` and `isError: true`.
That envelope indicates receipt of a tool response, not that tests passed.

The first claim was unsupported by the recorded rerun evidence available at that
time. The later result supports eventual passing tests. This example establishes
an import and review workflow; it is not an accuracy benchmark or an estimate of
how frequently Goose makes misleading claims. Model behavior can differ on reruns.

## Import your own session

Export complete JSON from Goose, rather than the token-by-token `stream-json`
run log:

```bash
goose session export --session-id YOUR_SESSION_ID --format json -o session.json
python3 -B src/review_app.py --goose-session session.json --port 8767
```

Annotations default to `session.claimtrail-reviews.json` beside the export and are
created only after **Save review**. Use `--labels PATH` for a separate annotation
file. The server rejects the source export as a labels destination. Keep the
export unchanged while reviewing; source changes block reload, export, and save.

Goose annotations carry `data_mode: goose_session`, the source hash and citation
pins, and `independent_human_validation: false`. They are excluded from the
existing research evaluator. A reviewer must assess claims; import does not
automatically assign supported or contradicted labels.

## Run a new local session

Install an official Goose release and start Ollama with an already-installed
model. The example runner uses only the local Ollama endpoint and refuses to
download a missing model:

```bash
ollama serve
```

In another terminal:

```bash
python3 -B scripts/run_goose_example.py --goose /absolute/path/to/goose --model qwen3:8b
```

The runner creates a new workspace under `data/goose/`, introduces the small add
function bug, and asks Goose to run tests, repair the function, and rerun tests.
It then requests a separate later verification. Both the initial and final JSON
exports, logs, task prompts, runtime version, and final source artifacts are
retained. Goose configuration and session storage stay inside that run directory
through `GOOSE_PATH_ROOT`; your default Goose configuration is unchanged.
The script prints the command to review the resulting session. `--output PATH`
selects a new output directory; an existing directory is never overwritten.

## Scope and verification

- Tested input is the Goose 1.59.0 JSON export with a `conversation` array.
- Tool request/response IDs are paired within one session. Duplicate IDs and
  responses preceding their requests are rejected.
- Missing responses stay explicit. Orphan responses retain their original data
  without acquiring invented tool arguments or process exit codes.
- Conversation order resolves equal-second timestamps. Displayed UTC timestamps
  remain unchanged; zero-second offsets can still be ordered before or after.
- Assistant thinking, prompts, and hidden assistant text are excluded from claim
  candidates. Original tool events remain inspectable.
- The existing 24-hour-before / two-hour-after review window still applies.
- Plain session import does not establish filesystem freshness. The separate
  [scope verifier](SCOPE_VERIFICATION.md) needs a captured receipt and observation
  and can run inside an existing recipe check. Cross-session linking remains
  outside this importer.

```bash
python3 -S -B -m unittest discover -s tests -v
node --check web/review.js
```

The integration tests exercise source validation, failed process results inside
successful response envelopes, missing results, equal timestamps, search,
save/reload/export, conflicting edits, and source-change rejection. The recorded
example also provides an offline regression fixture.
