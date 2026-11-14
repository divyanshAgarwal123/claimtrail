# Scope and freshness results — 14 November 2026

The packaged evidence contains **30 controlled cases on real repositories** and
**six completed Goose stages across two sessions**. All 36 replay to their
predeclared expected contract outcomes. Separately, two actual Goose recipe
trials accepted a fresh receipt (exit 0) and rejected a stale one (exit 1 after
the configured one-retry limit). These are mechanism and integration checks, not
an independent accuracy benchmark or a natural agent failure rate.

## Repositories and environment

| Repository | Pinned revision | Captured unchanged full-suite outcome |
| --- | --- | --- |
| [More Itertools](https://github.com/more-itertools/more-itertools) | `ceafee8ce96f4bc1eb74c528bc247c91d648a0bb` | `unittest`: 936 tests, 5 skipped, exit 0 |
| [ItsDangerous](https://github.com/pallets/itsdangerous) | `672971d66a2ef9f85151e53283113f33d642dabd` | `pytest`: 297 passed, exit 0 |

Captured on macOS 27.2 / arm64, Python 3.13.17. Goose 1.59.0 used local Ollama
0.40.11 and an already-installed `qwen3:8b` model. No paid model/API calls were used.
The [test environment versions](../examples/verification/environment.txt) are
recorded. ClaimTrail and offline replay require only the Python standard library;
pytest/freezegun are dependencies of the upstream test runs.

## Controlled contract outcomes

Each row was exercised separately in each pinned repository. All source/test
mutations were introduced by the harness and restored. They are not upstream
bugs, contributor patches or examples of spontaneous agent behavior.

| Case per repository | Result |
| --- | --- |
| Unchanged passing full suite | Verified |
| Benign source, test or configuration edit after pass | Stale (three cases) |
| Untracked file added inside scope | Stale |
| Test file deleted after pass | Stale |
| Explicitly excluded bytecode cache changes | Verified for the declared scope |
| README changed outside the declared scope | Verified for the declared scope |
| Functional regression introduced after an old pass | Stale |
| Full suite run on the introduced regression | Failed |
| Passing unrelated/subset check offered for the full policy | Scope/policy mismatch |
| Restore upstream bytes and actually rerun | Verified |
| Command runs tests and then changes a scoped source file | Changed during check |
| No receipt | Missing |
| Passing rerun completed after the captured observation | Later; cannot verify earlier boundary |

Positive controls for excluded/outside paths demonstrate the policy boundary.
They do not establish whole-repository coverage. Even a harmless comment edit
invalidates the old content-bound receipt; that is conservative invalidation,
not evidence that the program is broken. Unit tests additionally exercise timeout,
cross-workspace reuse, malformed/altered records, symlink/path escape, renames,
executable-mode changes and output/source destination guards.

## What the baseline comparison shows

On each introduced functional regression, a fresh full-suite rerun also failed.
That is the correct existing-check baseline. In contrast, the selected unrelated
subset passed, while ClaimTrail rejected its receipt for the configured full
policy. The result shows explicit contract matching; it does not show that
ClaimTrail can automatically discover a sufficient test scope.

The practical addition is a reusable policy/receipt format, changed-path
invalidation, an offline audit view and a gate callable from Goose's existing
recipe checks. A custom Stop hook can implement similar logic. Existing
[DoneProof receipt work](https://github.com/giugiu-a11y/doneproof/pull/35) overlaps;
content-bound receipts are not claimed as a new invention.

## Actual Goose sessions and recipe gate

Each repository has one real Goose session with three completed stages:

1. Goose invokes the configured capture command: verified.
2. After a disclosed host comment edit, Goose invokes verification without a
   rerun: stale, with the source path returned.
3. The host restores the upstream source; Goose invokes a real rerun: verified.

The package pins each exact model message to a redacted native export, and pins
the actual shell tool response to the replayed tool observation. The separate
host observation occurs after Goose returns and is not backdated to the message.
The [provenance file](../examples/verification/recorded/provenance.json) records
original/redacted export hashes and transformations. Thinking blocks are removed.
Receipt policy argv retains the actual local interpreter path because it is part
of the captured policy identity; the runner generates a suitable policy on a
different machine.

Some model responses incorrectly paraphrased the limitation as confirming “no
semantic or dependency coverage changes.” The verifier does not establish that.
Those responses remain visible as source material; they are not accepted as
checker conclusions. This is why the interface shows the narrower host result.

The [native recipe trials](../examples/verification/recorded/recipe-trials.json)
retain visible stream output and error text. Their stale edit is likewise
controlled. See `scripts/check_goose_recipe.py` for the executed setup and command.

## Reproduce

Replay without any models, repository clones or upstream dependencies:

```bash
python3 -S -B -m unittest discover -s tests -v
python3 -B src/verification_report.py examples/verification/recorded/report.json
python3 -B src/review_app.py --verification-report examples/verification/recorded/report.json --port 8768
```

To create new real repository captures, install the recorded test dependencies in
an isolated environment and choose **new** output directories:

```bash
uv venv .tools/verification-venv --python python3
uv pip install --python .tools/verification-venv/bin/python -r examples/verification/environment.txt
python3 -B scripts/run_scope_examples.py --output data/scope-eval/new-run --python .tools/verification-venv/bin/python
```

The runner clones/verifies the exact upstream revisions and refuses to reset a
dirty or mismatched existing clone. With official Goose installed, Ollama running
and Qwen3 already available locally:

```bash
python3 -B scripts/run_goose_scope.py --output data/goose-real/new-run --goose /absolute/path/to/goose --python .tools/verification-venv/bin/python
python3 -B scripts/check_goose_recipe.py --goose /absolute/path/to/goose --repo data/real-repos/itsdangerous --policy data/scope-eval/new-run/itsdangerous.policy.json --source src/itsdangerous/encoding.py --output data/recipe-check/new-run
python3 -B scripts/package_verification.py --controlled data/scope-eval/new-run/report.json --goose data/goose-real/new-run --recipe-trials data/recipe-check/new-run/trials.json --output data/packaged/new-run
```

Model wording, timings, IDs and output hashes may differ. Exact test counts can
also vary with Python/platform. New captures must be inspected; a scripted prompt
is not evidence that the model followed it. No ordinary-use prevalence estimate,
independent review or external adoption is claimed. The [review guide](REVIEWER_GUIDE.md)
and [proposal](SPIRAL_PROPOSAL.md) describe those next validation steps.
