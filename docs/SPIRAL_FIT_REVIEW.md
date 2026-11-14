# Spiral grant fit review

Checked 14 November 2026. This is project planning, not an application submission
or a prediction of an award.

## Decision

Worth a focused application after a short readiness pass. The current prototype
is a credible starting artifact for a discussion about a three-month first phase.
It does not yet justify treating a full-year grant as likely. Limit further
unfunded preparation to a short, bounded sprint; do not plan college or finances
around an award. The amount should remain open for discussion with Spiral.

The strongest proposed direction is a reusable way to connect a coding agent's
completion claims to checks on the relevant artifact revision, with an explicit
distinction between a check that happened before the claim and a later rerun.
The session viewer is the inspection interface. Revision binding and automatic
checking are still proposed work, not implemented features.

## Recent AI recipients

Spiral's [current grants page](https://spiral.xyz/grants/), with **AI** selected,
lists exactly these four recipients. April is the newest date shown in that
filter. The September 2026 entries in **All Grants** are Bitcoin recipients and
should not be used as recent AI comparisons. Dates are the page's listed grant
dates; they do not establish when a project started or what was complete at award.

| Listed recipient | Listed date | What the public evidence supports | Relevance to ClaimTrail |
| --- | --- | --- | --- |
| Abhijay Jain | April 2026 | AAIF describes him as a Goose maintainer, contributor and grant recipient. The exact funded work is not specified on the grant list. | A demonstrated contribution path exists. A useful upstream artifact and maintainer feedback would strengthen our case. |
| Larry McCay | April 2026 | Current AI grantee; the grant page gives no project description. | We cannot responsibly infer his funded scope or use it as a feature comparison. |
| Uchi Uchibeke | March 2026 | His own account identifies APort, an open agent-authorization specification, as funded by a Block grant. This is the recipient's statement, alongside Spiral's official recipient listing. | Agent trust infrastructure fits. APort checks permission before an action; ClaimTrail currently helps a reviewer assess evidence for a completion claim after actions. |
| Jerry Ochieng Anyumba | February 2026 | Goose's official winner profile describes the Jarida team's Goose In A Pond: a local home assistant plus reusable MCP components and a quarterly roadmap. | A clear user workflow and reusable ecosystem outputs are a stronger pitch than a standalone dashboard. |

Supporting sources:

- [AAIF's Goose project page](https://aaif.io/projects/goose), including its June 2026 Abhijay Jain program listing.
- [Uchi's description of APort and its funding](https://www.linkedin.com/posts/nickku_i-have-not-said-much-publicly-since-the-chimoney-activity-7508521257798090752-8gxk). His later reported benchmark results are not independent validation and are not evidence of what existed at award.
- [Official Goose In A Pond winner profile, 24 February 2026](https://goose-docs.ai/blog/2026/02/24/goose-grant-goose-in-a-pond/). This is a detailed official winner case, not the newest listed AI grant. Its roadmap includes future work; it does not imply that applicants must finish their whole project before applying.

These cases demonstrate plausible fit, not a selection rubric. A winner-only
sample contains no denominator of rejected applications, so it cannot produce an
acceptance probability.

## Where ClaimTrail stands

The local branch imports native Goose JSON, retains original tool events,
distinguishes process exit codes from successful response envelopes, separates
before/after evidence, and lets a reviewer save source-pinned citations and
uncertainty. It has 29 passing software tests. The UI was checked at desktop and
390 px mobile widths, including filters, raw records and episode navigation.

One constructed local task produced a completion claim before its successful
rerun was recorded; a second fresh run verified before claiming success. Both
used the same small task and local model. This establishes integration and
variation, not frequency, broad detection accuracy or a validated automatic
verifier. Existing research interpretations are AI-assisted, not independent
human labels. There is no secured external pilot or maintainer endorsement.

Goose already has configured completion checks. In
[issue 9708](https://github.com/aaif-goose/goose/issues/9708#issuecomment-5142623819),
the maintainer points to recipe `retry.checks` and bounded Stop hooks. The proposal
must show an increment over those mechanisms: how evidence is selected, which
artifact scope it covers, when a result becomes stale, and how errors are measured.
A general claim that agents need tests would not establish that increment.

The same discussion links [DoneProof's captured-evidence and Git-scope proposal](https://github.com/giugiu-a11y/doneproof/pull/35).
Revision-bound receipts alone should therefore not be pitched as novel. Compare
its actual behavior and limits before making a novelty claim; a proposed or open
pull request is neither proof of deployment nor evidence that the whole problem
is solved. ClaimTrail's value must be established through the Goose workflow and
measured review/checking benefits.

The integration and this UI pass are local work. They must be made publicly
reviewable before a proposal links to them. This checkout has no explicit project
license file; an appropriate license and data/third-party boundaries should be
resolved before presenting it as reusable open-source infrastructure.

## A bounded next step

Before sending the full proposal, publish the integration, reproducible example
and chosen license; collect feedback from at least one actual Goose user; and
add a few ordinary repository sessions with both successful and unsuccessful
checks. Record counterexamples and limits, not just a demonstration that succeeds.
These are recommendations, not published Spiral requirements.

At **20–25 hours per week**, a proposed 12-week first phase is about **240–300
hours**, including documentation and feedback:

1. Weeks 1–4: harden import and evidence inspection on ordinary repository tasks,
   document failure cases, and agree a narrow checker scope with users.
2. Weeks 5–8: prototype revision-bound receipts for one check type, including
   invalidation after edits and explicit unresolved cases. Evaluate against
   configured Goose checks rather than claiming all existing tools lack checks.
3. Weeks 9–12: have someone other than the author review a small frozen set;
   report false positives, misses and review effort; deliver a reproducible
   package and a continuation decision.

This is a proposed milestone budget, not a promise that independent reviewers or
an upstream pilot are already secured. A longer roadmap should depend on the
first phase's results.

## Current terms remain open

Spiral currently invites detailed proposals by email. Its grant page does not
publish a fixed AI award amount, acceptance rate, part-time/student conditions or
India payment arrangements. Older Goose announcements and a recipient's reported
award do not establish the terms of a new Spiral contract. State the student's
20–25 hour availability and that ClaimTrail has no current project funding, and
ask Spiral to confirm compatible terms if interested. No proposal has been sent
as part of this review.
