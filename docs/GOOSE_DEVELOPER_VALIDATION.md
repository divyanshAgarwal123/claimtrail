# Establishing whether Goose developers would use ClaimTrail

Research checked 14 November 2026. This is a trial plan, not completed user
research. No participant, maintainer endorsement or repeat use is secured. The
existing package demonstrates a mechanism; the next evidence should concern a
developer's own work and what they choose to do afterward.

## Narrow hypothesis

A Goose developer reviewing a completed repository change can identify the
applicable check and any stale scope with less effort, or with fewer unsupported
acceptances, using ClaimTrail. That benefit must justify policy setup and reruns.
A fresh correctly scoped test remains a valid and potentially simpler answer.

Start with developers who already use Goose for multi-step coding tasks and
already have a repository check. Ask for a recent concrete example of reviewing
the final result. Do not recruit only people who like agent-safety ideas or ask
whether they like the demo.

## What the primary sources support

| Source and status when checked | Relevant signal | Consequence for this trial |
| --- | --- | --- |
| [Goose #9708](https://github.com/aaif-goose/goose/issues/9708), closed as not planned | A user reported unsupported completion claims. The final maintainer response explains existing recipe/Stop-hook options and uncertainty about selecting sufficient checks. | Test review effort and explicit host-selected scope. Do not pitch another generic completion gate or imply this issue endorses ClaimTrail. Earlier interest was in another contributor's proposal. |
| [Goose #11926](https://github.com/aaif-goose/goose/issues/11926), open | Contributors report difficulty following and revisiting tool-heavy conversations. A deployment user offered to test the proposed UI. | Evidence lookup is a plausible pain point. That offer concerns Goose's UI, not ClaimTrail, and is not a recruited participant. Avoid building a competing general transcript UI. |
| [Goose #13316](https://github.com/aaif-goose/goose/issues/13316), open/design discussion | A session-format proposal received a maintainer concern about maintaining more importers/exporters. | Keep the trial on native Goose exports. Ask whether a small receipt/evidence attachment is useful before promising another trace format. |
| [Goose #10951](https://github.com/aaif-goose/goose/issues/10951), closed as completed on 11 November | Export completeness and audit provenance were reported problems. | Historical motivation, not evidence that those gaps remain open or that ClaimTrail fixes them. Check the participant's actual Goose version/export. |
| [Goose #11051](https://github.com/aaif-goose/goose/issues/11051), open | Scheduled runs can report success despite provider failures; the discussion includes reproduction and corrections to the proposed cause. | Useful boundary case. ClaimTrail's check receipt does not establish scheduler/provider success or fix this bug. Do not expand the first trial to background-job reliability. |
| [Goose's evaluation workflow](https://goose-docs.ai/blog/2026/06/17/self-improving-agents-need-humans/) | The team compares trajectories and verifier outputs, then uses human review to identify a general failure mechanism. | A source-linked diagnostic case is more useful than another aggregate pass count. Existing Harbor runs are a later evaluation route, not a prerequisite for this small pilot. |

Public issues establish plausible problems, not their prevalence or willingness
to install our tool. Their authors have not been contacted for this work.

## Best ways to obtain stronger evidence, in order

1. **Own-change trial with an existing Goose user.** Observe uncoached setup,
   completion-evidence review and whether the user finds a concrete benefit.
   Retain failures and no-benefit outcomes. This is the first priority.
2. **Voluntary second use on a different change.** Ask once after the first trial
   whether they want the instructions for another run. Record choice separately
   from an actual returned second artifact. An intention to reuse is not reuse.
3. **Maintainer method review.** Present one small, redacted case with the policy,
   command, final state, exact original tool result and baseline comparison.
   Ask whether the artifact helps investigate the problem and what is redundant.
   Method feedback is not product adoption or endorsement.
4. **Existing long-session evidence.** With permission, inspect a genuine session
   where review was difficult. Keep missing outputs unresolved. Record actual
   task length/compaction if available; do not manufacture rollbacks, block tools
   or force context degradation to create an ordinary-use failure.

Recruitment routes are the official community linked from the
[Goose site](https://goose-docs.ai/blog/2026/07/30/issues-are-the-new-prs/) and
volunteers already using Goose on public repositories. An issue-specific design
question should follow the [contribution workflow](https://github.com/aaif-goose/goose/blob/main/CONTRIBUTING.md),
not duplicate a closed feature request. Upstream implementation waits for a
Ready issue. This work changes ClaimTrail, not Goose. No messages are sent by
this plan.

## One-week preparation budget

Cap this sprint at 20 core hours, with five hours available for contingencies:
three hours checking needs and source boundaries, four making/rehearsing the
trial kit, two for approved invitations and scheduling, seven for pilot support
and evidence inspection, four for analysis and a short results note. Recruitment
and participant availability may prevent completion within a week; publish that
shortfall instead of adding more self-tests. This is preparation before the
proposed funded 12-week study, not a replacement for its 30-session evaluation.

Target two independent users, at least one a regular Goose coding user. Neither
may have implemented ClaimTrail. Keep participant time and any assistance
separate from the author's time budget.

## Runnable first trial

**Offline orientation, about five minutes.** From a ClaimTrail checkout:

```bash
python3 -B src/verification_report.py examples/verification/recorded/report.json
python3 -B src/review_app.py --verification-report examples/verification/recorded/report.json --port 8768
```

Open http://127.0.0.1:8768/. Find one stale case, its changed path and the exact
original tool response. The examples disclose host edits and already include
verifier statuses. Treat this as orientation/presentation testing, not a Goose
without ClaimTrail control, independent discovery of a failure, or repeat use.

**Live own-change attempt, budget 20–30 minutes for setup and review.** Choose a
small public change the participant already intended to make with their existing
Goose installation. Task/test execution time is recorded separately. No feature
or provider purchase is required. Stop and record a setup failure if the time
budget is exceeded; any later assistance stays visible.

1. Before showing ClaimTrail, ask how they normally decide the task is complete
   and record the check they would normally run. Keep a baseline task/check
   record before intervention. A single retrospective answer is not a paired
   performance measurement.
2. Use an isolated clone, a host-approved common workspace for ClaimTrail,
   project and output, and a policy adapted from the
   [example](../examples/verification/policy.example.json). The participant must
   choose the real argv and literal source/test/configuration scope. Record time
   and rationale; the supplied ClaimTrail policy is not a policy for their repo.
3. When Goose would normally run that check, use the existing capture command
   from [the CLI guide](SCOPE_VERIFICATION.md#run-and-verify). Continue the real
   task normally. Do not introduce a later edit merely to obtain a stale label.
4. At review time, the host invokes `verify` against the same receipt and policy,
   saves the observation, and exports the native Goose session with the command
   in [the importer guide](GOOSE_INTEGRATION.md#import-your-own-session). The
   observation is later than the model's completion message; never backdate it.
   The current manual capture/import steps are part of the setup cost, not a
   claim that a seamless ordinary-session adapter already ships.
5. Ask the participant to identify which check applies, explain any rerun and
   make an accept/reject/unresolved decision for that narrow evidence question.
   Normal tests and fresh reruns stay available. Collect the actual reason the
   tool helped, did nothing or added work. Then offer the optional second use.

For the funded matched comparison, use the
[full protocol](REVIEWER_GUIDE.md): different comparable tasks, condition order
alternated, the same check access, and all original output in the baseline.
Historical artifact inspection measures presentation; a live trial measures
workflow cost. Do not combine their timing numbers. The captured fixture's raw
tool output must never be stripped to make the baseline weaker.

## What a useful result contains

Copy the [empty record](../examples/pilot/trial.template.json) for each attempted
task. It is a template, not a participant observation. Retain version, repository
revision, task, condition/order, policy, artifact hashes, assistance, setup and
review time, test runtime/reruns, decision, unresolved questions and second-use
artifact. Shared data needs participant permission and redaction; a private
session is not required. Inspect exports before uploading them anywhere.

A strong first signal is two specific accounts of a recent review problem, two
completed own-change attempts and at least one uncoached second use with a
concrete benefit and no unexplained incorrect acceptance. Those are internal
targets, not outcomes, statistical thresholds or Spiral requirements. A fresh
check being simpler is a valid negative result. If users see no benefit, narrow
the tool to evidence export/diagnostics or stop the workflow expansion.

## Draft invitation, not sent

> Do you use Goose for repository changes and spend time checking the final
> “tests passed” summary? I'm testing ClaimTrail, a small MIT-licensed tool that
> links a declared check to file content and shows whether its receipt still
> applies at review time. I'm looking for two developers to try setup and review
> on a small public change they already planned. Setup/review is budgeted at
> 20–30 minutes; task execution is separate. The offline demo needs no API. A
> live trial uses your normal Goose setup. I want failures and “this adds work”
> feedback too. A recent example of how you review completion would help decide
> whether this is relevant. A second use is optional; no endorsement is requested.
