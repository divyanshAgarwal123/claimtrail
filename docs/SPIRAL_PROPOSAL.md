# ClaimTrail: completion evidence that stays in scope for Goose

**Applicant:** Divyansh Agarwal, B.Tech AI/ML student in India.

**First phase:** 12 weeks at 20–25 hours per week alongside college.

**Funding:** amount and payment terms open for discussion. No current employer,
client, grant or other project funding.

## The Goose workflow

A developer asks Goose to change a repository and run its checks. The tests pass,
but Goose then edits a source file, test or configuration before reporting that
the task is complete. The earlier pass is still in the transcript. Does it apply
to the files the reviewer is now inspecting?

ClaimTrail makes that question explicit through a four-step workflow:

1. **Choose the check.** The developer declares a command and the source, test
   and configuration files whose content it should cover.
2. **Capture the run.** Goose runs the command through ClaimTrail, which records
   the result and hashes the declared files before and after execution.
3. **Check at completion.** Goose's existing recipe check calls the verifier.
   A changed file, different policy, failed run or missing receipt prevents the
   old pass from verifying the current observation; changed paths are returned.
4. **Review the evidence.** The developer sees the original Goose completion
   message and tool result alongside the receipt, scope and observation time.
   Missing links and unresolved cases remain visible.

The first users are developers already using Goose for repository changes with
a meaningful test command. The first-phase question is whether this workflow
helps them judge completion evidence at an acceptable setup and review cost.

Goose already provides recipe `retry.checks` and bounded Stop hooks. ClaimTrail
uses those mechanisms. Its contribution is reusable capture, freshness checking
and evidence review; a correctly scoped fresh test run remains the baseline.
[DoneProof's receipt/scope work](https://github.com/giugiu-a11y/doneproof/pull/35)
is relevant prior art. Content-bound receipts are not claimed as a new invention.

## What already works

The MIT-licensed prototype imports native Goose JSON, preserves original tool
events and process exit codes, and distinguishes evidence available before a
claim from later results. Its verifier binds a host-selected command and scope
to file content, rejects stale or mismatched receipts, and supports offline
review. Scripted captures already join receipts to Goose session and tool IDs;
native recipe trials accepted a fresh receipt and rejected a stale one.

The [published results](VERIFICATION_RESULTS.md) include 30 controlled cases on
pinned More Itertools and ItsDangerous revisions, plus six actual Goose stages
across two sessions. Captured full-suite runs recorded 936 tests with five skipped
and 297 passed, respectively. ClaimTrail has 47 passing software tests and CI on
the merged implementation. The [demo](../README.md#review-the-real-repository-evidence)
can replay these records without a model or API.

The stale stages used disclosed host edits. These results demonstrate the
specified contract, not ordinary agent failure rates or independent user value.
Original model messages remain visible, including overstatements of the
verifier's guarantee. No external pilot or maintainer endorsement is claimed.

## Funded work and 12-week deliverables

The grant would turn the scripted demonstration into an ordinary Goose session
workflow and test its usefulness. Existing receipts, importer and controlled
results are the starting point, not work to be funded again.

The core plan uses **240 hours: 20 hours per week**. Up to **60 additional hours**
within my stated availability are reserved for fixes, recruitment delays and
college contingencies. They do not carry extra feature commitments. Recruitment
and scheduling start in week 1.

| Period | Work and hour allocation | Deliverable and acceptance evidence |
| --- | --- | --- |
| **Weeks 1–4: usable Goose workflow — 80 h** | 50 h packaging and ordinary-session capture/linking; 20 h compatibility checks and setup docs; 10 h study protocol and recruitment. | A release candidate with an installable reference recipe/adapter, two repository policy examples, and a review export joining original Goose messages, tool IDs, receipts and observations. Ambiguous links must remain unresolved. Record interpreter/version and lockfile provenance without claiming dependency attestation. Publish macOS/Linux end-to-end results for available environments, unsupported combinations, and a frozen evaluation protocol. |
| **Weeks 5–8: ordinary sessions — 80 h** | 45 h running and inspecting 30 new sessions; 25 h baseline comparison and analysis; 10 h fixes and pilot scheduling. | An attempt log for 30 ordinary Goose coding sessions across two public Python repositories, with tasks and policies frozen before runs. Publish completed captures, failures, exclusions, configuration effort and timings. These sessions contain no harness-injected regressions; existing controlled cases remain a separate arm. Report exact available Goose/model configurations. |
| **Weeks 9–12: independent use and release — 80 h** | 35 h reviewer/pilot sessions and analysis; 25 h bounded usability fixes; 20 h final release, reproduction guide and continuation decision. | Target one independent technical reviewer and two independent Goose-capable pilot users. Publish their audit and usability findings, unresolved disagreements and any recruitment shortfall. Deliver a versioned release, reproducible results and a go/narrow/stop recommendation. |

## Independent testing and the baseline

Participants must not be the author or implementation collaborators. At least
one regular Goose user is a recruitment target; nobody is currently recruited.
The [review protocol](REVIEWER_GUIDE.md) specifies the tasks and reporting fields.

- **Technical audit:** one reviewer assesses 12 frozen captures, six ordinary
  and six controlled, from raw records before seeing ClaimTrail's outcome labels.
  Record agreement with the mechanical contract and judgments about policy
  sufficiency separately; the latter can remain unresolved.
- **User pilots:** each of two users attempts setup from the docs without live
  coaching, then reviews four matched tasks: two with baseline evidence and two
  with ClaimTrail. Alternate condition order and use different matched tasks to
  reduce learning effects. Invite an uncoached repeat on the user's own change.
- **Fair comparison:** the baseline includes Goose's configured checks,
  transcript and artifacts, with fresh reruns when normally required. ClaimTrail
  adds its joined receipt/scope view. An old exit code alone is not the baseline.

Measure setup completion/time, policy configuration effort, hands-on review time,
check execution time, incorrect acceptances/rejections against the frozen
contract reference, unresolved decisions and repeat-use choice. Publish negative
findings, missing data and denominators. This is a small usability study, not an
accuracy benchmark or estimate of agent failure prevalence.

Continuation targets are an independently audited set, two uncoached pilot
completions, at least one uncoached repeat, and concrete review benefit without
unexplained incorrect acceptances. These are proposed decision criteria, not
guaranteed outcomes or Spiral requirements. If recruitment is incomplete by
week 10, report that limitation in the final release; do not substitute author
testing for independent validation. Little benefit should lead to narrowing or
stopping the work.

## Boundaries, public outputs and continuation

A matching receipt establishes content freshness for a declared policy, not
semantic test coverage. Policy selection remains a human responsibility. External
dependencies/services, transient edit-and-restore races and an agent controlling
the host are outside the current contract. Local receipts are unsigned; runtime
metadata would improve provenance without making the environment hermetic.

Code, recipe examples, the evidence format, documentation and evaluation tooling
will remain open source under MIT, with third-party terms separate. Shared study
records require participant permission and redaction. Goose remains the target
integration; this phase does not promise additional agents or language support.

Any extension through month 12 should follow the independent-use results: address
measured Goose workflow problems, validate repeat use, then stabilize maintenance
and handoff. New languages, stronger isolation or upstream integration would
require a justified, separately agreed scope. Upstream acceptance is not promised.

I would welcome a milestone-based first-phase grant compatible with this part-time
commitment. The award amount, payment arrangements for India, milestone terms and
any continuation remain open for discussion with Spiral.

*Prepared for applicant review; not sent to Spiral.*
