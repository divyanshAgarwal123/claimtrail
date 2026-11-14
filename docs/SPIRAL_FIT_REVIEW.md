# Spiral grant fit review

Grant sources checked 14 November 2026; implementation assessment updated after
the scope/freshness work. See the [results](VERIFICATION_RESULTS.md) and
[proposal](SPIRAL_PROPOSAL.md). Independent user validation is still pending.
This is project planning, not an application submission or prediction of an award.

## Decision

Worth a focused application after a short readiness pass. The current prototype
is a credible starting artifact for a discussion about a three-month first phase.
It does not yet justify treating a full-year grant as likely. Limit further
unfunded preparation to a short, bounded sprint; do not plan college or finances
around an award. The amount should remain open for discussion with Spiral.

The implementation now binds a configured check to declared file content and a
later observation, with explicit rejection of stale or mismatched evidence. The
session viewer remains the inspection interface. Automatic semantic scope
selection and dependency/environment attestation remain future work.

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

The implementation imports native Goose JSON, retains original tool events,
distinguishes process exit codes from successful response envelopes, separates
before/after evidence, and lets a reviewer save source-pinned citations and
uncertainty. It has 47 passing software tests. The UI was checked at desktop and
390 px mobile widths, including filters, raw records and navigation.

The new evidence package contains 30 controlled cases on pinned More Itertools
and ItsDangerous revisions, six actual Goose stages across two sessions, and
native recipe fresh/stale trials. The earlier toy example also remains available.
These establish contract behavior and integration, not natural failure frequency
or a validated automatic semantic detector. Existing research interpretations
are AI-assisted, not independent human labels. There is no secured external pilot
or maintainer endorsement.

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

The implementation and evidence are publicly reviewable in
[draft PR 1](https://github.com/divyanshAgarwal123/claimtrail/pull/1). They have not
been merged to the default branch. MIT licensing and separate dataset/upstream
notices are included.

## A bounded next step

The prototype and reproducible evidence are available for a focused proposal.
The strongest remaining improvement is feedback from an actual Goose user and
ordinary-use sessions with independently reviewed outcomes. Record counterexamples
and limits, not just demonstrations that succeed. These are recommendations,
not published Spiral requirements or secured commitments.

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
