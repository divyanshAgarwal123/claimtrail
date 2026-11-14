# Scope and freshness verification

ClaimTrail captures an explicitly configured command and the declared files it
is intended to check. A later verification compares that receipt with another
filesystem observation. This is an executable evidence contract, not automatic
natural-language truth checking.

## Run and verify

No Python dependencies are required by ClaimTrail itself. From its repository:

```bash
python3 -B src/scope_verification.py run --repo . \
  --policy examples/verification/policy.example.json \
  --receipt data/receipts/claimtrail.json

python3 -B src/scope_verification.py verify --repo . \
  --policy examples/verification/policy.example.json \
  --receipt data/receipts/claimtrail.json \
  --observation data/receipts/claimtrail-observation.json
```

`run` actually executes the policy's argv in the named repository and atomically
updates the selected receipt. `verify` reads and hashes files; it never executes
the recorded command. Exit **0** means the configured contract verified, **1**
means it did not verify, and **2** means invalid input or capture failure. Keep
the policy, receipt and observation in separate files, and put capture outputs
outside the declared source scope.

CLI paths must resolve inside the host-approved root, which defaults to the
current working directory. A host running tools from a nested repository can set
`CLAIMTRAIL_ALLOWED_ROOT` in the tool's environment to an approved common parent
for the repository, policy and capture output. Absolute paths, `..` and symlinks
cannot escape that configured boundary. The reproduction runners propagate the
boundary when invoking Goose. They also validate executable names and model
identifiers before passing CLI arguments to subprocesses.

This guards against accidental agent-supplied paths/options. A process that can
change its environment, execute arbitrary shell commands or rewrite this program
can bypass it; OS/container isolation remains the host's responsibility. Library
import/report APIs also check the host root. A trusted library caller can supply
an explicit `allowed_root` for an isolated workspace; the command-line entrypoints
do not accept a model-supplied root override.

Choose a policy independently of the agent's completion prose. A policy contains
a check ID, literal scope roots, argv, explicit exclusions, environment overrides
and timeout. Relative argv paths and environment values are interpreted from the
repository root. Shell interpolation is not applied to argv. A user can explicitly
configure a shell as the executable, so policies are trusted executable input.

The receipt pins the entire normalized policy. A receipt from a different command,
scope, exclusion set, check ID or configured environment cannot satisfy it. Scope
is not inferred from a test name. The local workspace ID also prevents accidental
reuse across different checkout paths. For a moved/new checkout, rerun the check.

## What is captured

- Relative file paths, byte lengths, SHA-256 content hashes and executable flags,
  before and after execution. Untracked and Git-ignored files inside scope are
  included unless explicitly excluded. Git metadata is outside the content scope.
- Command completion, exit code, timeout/launch failure, duration, output byte
  counts and hashes, and bounded output excerpts.
- A separately hashed observation, bound to the selected receipt and required
  policy. The captured report can be replayed offline without the repositories.

An edit, addition, deletion, rename or executable-flag change in scope invalidates
a prior pass. Source, test and configuration files are treated the same. Changes
observed during execution are a separate rejection. Symlinks, special files,
outside paths and invalid captures fail closed. Content restored exactly to the
checked bytes can match again; this is a content contract, not edit-history proof.

Only `verified` is a successful gate result. Other results include `stale`,
`scope_mismatch`, `changed_during_check`, `failed`, `timeout`, `missing`, `later`,
`workspace_mismatch`, and `unresolved`. Changed paths are returned explicitly.
A check that finished after an observation cannot verify that earlier boundary.

## Goose integration and baseline

Use a host-owned policy and canonical receipt path. Let Goose invoke `run` when
it actually performs the configured check. Invoke `verify` as a recipe shell
success check or bounded Stop hook. Keep capture paths and the implementation
outside an untrusted agent's write authority if adversarial integrity matters;
this prototype does not impose that isolation.

Goose's existing [recipe retry checks](https://goose-docs.ai/docs/guides/recipes/recipe-reference/#retry)
already execute shell validation commands. ClaimTrail plugs into that mechanism:

```json
{
  "retry": {
    "max_retries": 1,
    "timeout_seconds": 30,
    "checks": [{
      "type": "shell",
      "command": "python3 /absolute/claimtrail/src/scope_verification.py verify --repo /absolute/repo --policy /absolute/host-policy.json --receipt /absolute/receipt.json"
    }]
  }
}
```

The paths are host configuration, not values to accept from an agent response.
The [recipe integration runner](../scripts/check_goose_recipe.py) tests actual
Goose acceptance/rejection. It intentionally uses a benign host edit to exercise
invalidation and restores the source afterward.

A correctly scoped fresh full-suite rerun can detect a regression too. ClaimTrail
adds a reusable capture format, policy/content binding, explicit invalidation and
an inspectable history. It does not introduce a new lifecycle hook. The related
[DoneProof receipt proposal](https://github.com/giugiu-a11y/doneproof/pull/35) is
prior art; receipts and Git scope should not be advertised as inventions here.

## Boundaries

“Verified” establishes that the configured command exited zero on the same
declared file content observed here. It does not establish that the host selected
a sufficient check, that every declared file was exercised, that all project tests
were selected, or that the agent's entire prose is true. External dependencies,
interpreter state, network/services, excluded paths, non-executable permissions
and directory metadata are not attested.

Snapshots are not atomic filesystem transactions. Transient edit-and-restore
races can evade before/after comparison. Receipts are unsigned local records;
hashes detect changed records relative to their pins, not fabrication by a process
that controls both records and verifier. This is not a sandbox or a security
boundary against a malicious same-host agent. A production deployment needs
appropriate host isolation and environment/dependency capture.

The Goose session report preserves the actual tool result and exact model text.
Its host observation is taken after the session returns. It is not backdated to
the model's message time. Plain historical Goose exports without these receipts
retain the original importer's “freshness unverified” boundary.
