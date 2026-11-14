# Independent review and user testing protocol

This is the proposed protocol for the [12-week first phase](SPIRAL_PROPOSAL.md),
not a completed study. No independent reviewer or pilot user is currently
recruited. Author-written tests and scripted demonstrations remain separate.

## Freeze before collecting results

Publish a dated protocol revision before the ordinary-session runs, covering:

- 30 coding tasks across two public Python repositories, their starting revisions,
  expected artifacts, check commands and declared source/test/configuration scope;
- Goose, model, runtime and platform versions, session limits and a fixed rule
  for recording unsuccessful runs and exclusions;
- the contract reference rules and sampling rule for the 12-capture audit;
- matched pilot tasks, condition order, timing boundaries and result fields.

Keep a log of every attempted ordinary session, including failed or incomplete
runs. Do not silently replace failures to reach 30 successful captures. Changes
to tasks or policies after results are visible must be recorded as deviations.
Ordinary sessions contain no harness-injected regressions. Controlled stale,
mismatch and outside-scope cases stay in a separate arm.

## Technical audit: one independent reviewer

Recruit a developer who did not implement ClaimTrail. Select 12 captures using
the published sampling rule: six ordinary and six controlled. Include fresh,
stale, policy mismatch and outside-scope outcomes in the controlled selection.

1. Provide raw Goose exports, command results, policy, receipt, observation,
   repository revision and changed artifacts. Hide ClaimTrail's summary labels
   and author interpretations on the first pass. Scripted interventions must be
   disclosed in the reference material, not represented as ordinary agent errors.
2. Ask whether each receipt satisfies the mechanical contract at that observation
   boundary. Separately ask whether the chosen check/scope is sufficient for the
   narrow completion claim. Allow unresolved answers to either question.
3. Reveal ClaimTrail's result and explanation. Preserve the first assessment,
   disagreement, any revised assessment and reason. The author must not resolve
   disagreements silently or treat agreement on freshness as semantic validation.
4. For an unexpected acceptance/rejection, preserve a minimal reproduction and
   classify it as a contract bug, insufficient policy, missing evidence or an
   unresolved dispute. Fixes require a new version and a disclosed rerun.

## User pilots: two independent developers

Recruit two developers who can run Goose and did not implement ClaimTrail; target
at least one regular Goose user. Begin recruitment in week 1. Participation and
publication of redacted findings require permission; no private repository or
session content is required.

Each participant performs:

1. **Uncoached setup.** Start from the published docs in an isolated clone, choose
   the supplied repository policy and run one Goose capture/check/review cycle.
   Record setup time, completion, blockers and any assistance. If assistance is
   needed, record the uncoached attempt as incomplete before continuing.
2. **Four matched review tasks.** Review two baseline tasks and two ClaimTrail
   tasks. Alternate the first condition between participants and use different
   tasks of comparable difficulty so a remembered answer cannot decide the
   second condition. Ask whether the presented check evidence applies at the
   captured completion boundary, with an explicit unresolved option.
3. **Optional repeat.** Invite an uncoached run on their own public change.
   Record whether they choose to repeat, whether they complete it, setup/policy
   work and why they would or would not use the workflow again.

The baseline supplies Goose's configured checks, transcript and artifacts, with
a fresh correctly scoped rerun when normal review calls for it. ClaimTrail adds
the receipt, changed-path explanation and joined evidence view. Both conditions
must permit the same repository checks; record every extra rerun and its cost.

## Record and publish

For each attempt, record participant role (pseudonymous if requested), task ID,
condition/order, versions, policy, check executions, assistance, decision and
reason. Report setup/configuration effort, hands-on review time and check runtime
separately. Compare acceptance/rejection decisions to the frozen mechanical
reference, retaining unresolved cases and policy-sufficiency judgments separately.
Collect feedback on explanations and intent to reuse without treating that intent
as observed adoption.

Publish denominators, exclusions, failures, disagreements, redaction omissions and
protocol deviations. This small study supports usability case studies, not
statistical accuracy or general agent failure rates.

By week 10, assess recruitment. Missing reviewer or pilot participation must be
reported as incomplete independent validation in the week-12 release. The
continuation targets are 12 independently audited captures, two uncoached pilot
completions, at least one uncoached repeat and concrete review benefit without
unexplained incorrect acceptances. These are decision targets, not results already
obtained. Negative findings should support a narrower scope or a stop decision.
