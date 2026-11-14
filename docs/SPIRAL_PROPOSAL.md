# ClaimTrail: scope-bound completion evidence for Goose

Applicant: Divyansh Agarwal. Commitment: 20–25 hours per week alongside college.
Funding request: amount and payment arrangements open for discussion. ClaimTrail
has no current employer, client, grant or other project funding.

## Problem and users

A successful command does not necessarily verify the code an agent later claims
is complete. The command may cover a different test selection, source/tests may
change afterward, or a later rerun may be mistaken for evidence available earlier.
Reviewers need to inspect the command, scope, state and timing together.

Goose already has recipe success checks and bounded Stop hooks. ClaimTrail builds
on that infrastructure rather than proposing another completion lifecycle. It
provides reusable evidence capture, explicit scope contracts and a review view
for developers using Goose on coding work. An initial user is a developer who
has a meaningful repository check and wants to know whether its receipt still
applies at completion/review time.

## Current artifact

The prototype imports native Goose JSON while retaining original tool events and
process exit codes. It separates recorded evidence before a claim from later
results and supports reviewer citations without assigning automatic truth labels.

The new standard-library verifier runs a host-selected argv, snapshots declared
source/test/configuration files before and after it, and records output hashes,
exit/timeout information and policy identity. A later gate rejects a changed
scope, a different policy or workspace, changes during execution, missing results
and checks completed after the observation. It returns concrete changed paths.
Captured reports can be replayed without executing the command or installing
the upstream repositories.

The repository includes pinned More Itertools and ItsDangerous reproduction
runners, controlled positive/negative cases, real local Goose shell sessions,
a native recipe integration check, source-linked records and explicit limits.
See [verification results](VERIFICATION_RESULTS.md) for observed counts, revisions
and reproduction commands. The original code is MIT licensed. Dataset terms and
upstream license notices are kept separate.

This is a working mechanism demonstration. It is not an independently validated
automatic claim detector or a measurement of how often ordinary Goose sessions
misreport completion. The stale stages are disclosed controlled edits; the model's
exact messages are retained even where they overstate the checker guarantee.

## What it adds and how it will be evaluated

The contribution is a usable Goose integration and auditable contract: which
configured command produced this receipt, which files it binds, whether they
changed, and what the verifier declined to establish. Correctly scoped fresh
tests remain a valid baseline. Existing DoneProof receipt/scope work is prior art;
we do not claim to have invented content-bound execution receipts.

Future evaluation will compare direct configured checks, receipt reuse with
invalidation, and the same receipt verifier inside Goose's existing gate. Tasks
and policies will be frozen before evaluation. Report incorrect acceptances,
incorrect rejections, unresolved outcomes, configuration/review effort and rerun
cost separately. Do not convert controlled-case success into a general accuracy
claim. Include independent review and ordinary tasks alongside interventions.

## Proposed first 12 weeks

At 20–25 hours per week, the first phase is approximately 240–300 hours, including
documentation and feedback. It is useful independently of a longer award:

1. **Weeks 1–4 — strengthen capture and integration.** Test on Linux and macOS,
   document policy selection and capture boundaries, improve interpreter/dependency
   provenance, and package the recipe gate for ordinary Goose users. Deliver a
   versioned evidence schema, compatibility checks and reproducible examples.
2. **Weeks 5–8 — ordinary-use evaluation.** Freeze a small task set across the two
   repositories, run approximately 30 ordinary sessions with available model
   configurations, and compare existing checks with receipt-based review. Seek
   an external reviewer and pilot feedback; neither is currently secured.
3. **Weeks 9–12 — publish results and decide continuation.** Release artifacts,
   failure cases, policy setup effort and limitations. Use independent review
   where obtained, explicitly reporting any missing review. Deliver a reproducible
   report and a continuation decision based on usefulness, not just test counts.

## Conditional longer roadmap

- **Quarter 2:** address the measured failure modes, improve host isolation and
  environment capture, and test another repository/language where justified.
- **Quarter 3:** refine Goose workflow integration and policy setup with pilot
  users; add CI/artifact use cases only where the evidence shows demand.
- **Quarter 4:** stabilize the release, documentation and evaluation package;
  publish maintenance and handoff guidance. Seek upstream feedback without
  promising that Goose maintainers will merge or endorse the work.

The 12-month schedule assumes roughly 48 working weeks plus a four-week college
and contingency buffer: approximately 960–1,200 hours. A part-time agreement and
milestone/payment schedule need to be agreed with Spiral. The proposed work
extends the existing unfunded prototype; it does not bill completed work again.

## Risks and open terms

The largest product risk is policy sufficiency: a content match does not prove
that a command actually exercises every relevant behavior. The prototype does
not automatically infer that relationship. External dependencies, services and
transient edit-and-restore races are outside its current contract. Local unsigned
receipts are not tamper-proof against an agent controlling the host.

External adoption and independent review remain unproven. These are first-phase
validation goals. If they show little practical value beyond existing checks,
the continuation decision should narrow or stop the project.

Spiral's current page invites detailed proposals but does not publish standard
AI award amounts or student/part-time and India payment terms. I would welcome
discussion of a first-phase grant compatible with the stated availability, with
the amount and any continuation contingent on agreed milestones.

This is an AI-assisted draft for applicant review. It has not been sent to Spiral.
