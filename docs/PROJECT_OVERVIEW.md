# ClaimTrail

ClaimTrail is a local evidence workbench for investigating task-completion claims in collaborating agent groups. It places an agent's message beside recorded actions, outputs and artifact checks, with separate lanes for observations before the claim and later corroboration. A repository change, a deployment and functioning browser behavior need different evidence.

This project overview is AI-assisted project documentation, not a response to the participant-only submission form. The accompanying presentation is a rehearsal asset; no submission or publication has occurred.

## What works

The reviewer provides episode navigation, actor/time/source filters, searchable records, exact identifier leads, source-linked summaries, atomic claim annotations and exports. Source dialogs expose the full recorded context. Save/reload preserves assessment origin and policy, verifies source bindings and rejects conflicting or changed-source saves. Synthetic, AI-assisted, development and independent-human annotations are kept separate. The application serves one local reviewer on loopback; it is not a public multi-user service.

The synthetic demo needs Python 3.9+ and a browser, with no account, package installation or dataset download:

```bash
python3 -B src/review_app.py --demo --port 8766
```

Open http://127.0.0.1:8766/. Its three examples are explicitly invented. They demonstrate the workflow, not research findings. Real research inputs are deliberately absent from this delivery candidate.

## Exploratory evidence

The authorized local investigation used a four-day shared-goal window from a partial AI Village export, with a one-day lead-in. There are 25 frozen review episodes and two separate development cases. The assistant reviewed selected assertions in those 25 episodes: 64 units with 74 distinct non-chat source citations. Its classifications were 29 supported, 32 unresolved, one internal arithmetic contradiction and two not completion claims. These are AI-assisted judgments about selected units, not independent gold labels, prevalence estimates or system accuracy.

Two development reconstructions illustrate the tool's purpose. One distinguishes supported repository integration from unresolved live state at claim time; a collaborator's local-source check is actually 0.278 seconds later. The other distinguishes a rejected push and successful rebase from eventual remote corroboration 18.620 seconds after the claim. Both preserve uncertainty about the earlier outcome. These are timestamp offsets in exported records, not action durations or transmission delays. Eleven source anchors were checked locally; the underlying gated records are not included here.

## Methods and feasibility

BM25 provides a simple lexical session-goal baseline. An offline pretrained MiniLM comparison uses the identical same-agent, preceding-24-hour session pool; the two top choices agree in 9/25 episodes. That measures ranking disagreement, not which method is better. Literal commit/PR matching supplies another evidence channel. Turn-level ablations showed ranking sensitivity to tool outputs and expanded actor/time pools. Semantic retrieval remains optional: the demo runs without model weights or external APIs, and no training or fine-tuning was performed.

The independent-human evaluator rejects AI-assisted, synthetic and development labels. Independent labels are absent, so retrieval accuracy, verifier accuracy and improvement over searchable logs remain unestablished. Screenshots were not inspected. Missing actions in a partial export do not prove that those actions never occurred, and temporal proximity does not prove information transmission.

## Verification and provenance

Executed checks passed: 32 project tests, 23 tests in an isolated synthetic package and nine Chromium check groups. Browser checks include citation save/reload, stale tabs, edits during a pending save, narrow screens, source mutation rejection and research demonstrations using disposable annotation copies. They establish software behavior and source consistency, not semantic truth. The original research assessments were preserved.

Research source: **AI Digest, “AI Village dataset,” 2026**, [dataset card](https://huggingface.co/datasets/aidigestorg/ai-village). Main revision: `838b4150303ca8228e8edb432d8b8ccae353d258`; converted Parquet revision: `d74780cb71b790c68cc8d949f63b06c922573e83`. The converted export is partial. Dataset terms permit research/analysis, restrict training/fine-tuning without written permission and re-identification, and require attribution and publication notification. Review publication handling before distributing research material. No dataset content, model weights, credentials or real annotations are in this candidate.

The event asks for tools that illuminate agent groups, including trajectories and digital forensics. Our project choice is to make a narrow investigation traceable and inspectable. This is our interpretation of the theme, not a published scoring rubric or prediction of a prize. [Official project themes](https://swarmchasing.com/), [submission and judging logistics](https://swarmchasing.com/logistics/).
