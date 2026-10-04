# ClaimTrail — synthetic local demo

Inspect an agent's completion claim alongside recorded actions and results. **Every agent, message and action in this package is invented.** These are teaching examples, not AI Village findings or an accuracy benchmark.

## Run

Unzip the package, open a terminal in `claimtrail-demo`, and run:

```bash
python3 -B src/review_app.py --demo --port 8766
```

Open **http://127.0.0.1:8766/** in a local browser. Python 3.9+ is sufficient; there is no installation step, dataset login, API key, model download or internet dependency. If the port is occupied, choose another `--port` and use its matching URL. Stop with Ctrl-C. Windows users can substitute `py -3` for `python3`.

This is a loopback application for one local reviewer process, not a public service. Recorded commands are displayed as text and never executed. Research-mode commands require files that are deliberately absent from this package.

## Two-minute practice walkthrough

| Time | Action | What to explain |
| --- | --- | --- |
| 0:00–0:20 | Point to the **Synthetic demo** banner and **Case at a glance**. | The summary separates the assertion, earlier observations, later evidence and unresolved questions. It is a fixed teaching guide, separate from your practice labels. |
| 0:20–0:55 | In the first case, filter to **Before claim**. Open the push and queued-deployment records. Then select **After claim** and open the other agent's fetch. | The push has supporting evidence. The latest earlier deployment record is pending. The later fetch corroborates eventual markup presence; it does not prove the links were live when claimed or that interaction worked. Keep the at-claim live assertion unresolved. |
| 0:55–1:20 | Select the second case; open the rejected push and local branch status. | The observed attempt failed and the local branch remains ahead/behind. That challenges this specific success claim. It does not prove no unobserved retry could exist in a real partial export. |
| 1:20–1:45 | Select the third case; inspect the HTTP 200 and unavailable screenshot reference. | HTTP success does not verify a 3D scene or interaction. Keep visual correctness unresolved. |
| 1:45–2:00 | Select a unit, cite a source turn, enter a rationale and uncertainty, then save/export a practice annotation if desired. | The investigator records the judgment; retrieval does not automatically decide truth. |

Practice annotations are stored in `data/demo/reviews.json` only after Save. They are separate from research and human-validation labels. For a fresh practice session without deleting existing notes, use a new path, for example:

```bash
python3 -B src/review_app.py --demo --port 8769 --labels data/demo/rehearsal-02.json
```

Each summary source link opens the full record and shows its actor and time relative to the claim. Saves retain the review policy and generate source hashes from the local records. Reload/export checks reject mismatched evidence; a stale browser tab cannot overwrite a newer review. Older annotations without hashes are explicitly marked unpinned: a new save records the current sources and cannot verify their earlier content. Labels from a different bundle require their original bundle or a separate practice file; do not erase existing notes to force an upgrade.

## Verify

```bash
python3 -B -m unittest discover -s tests -v
```

The tests use invented fixtures, temporary label files and ephemeral loopback ports. They need permission to bind loopback in a restricted sandbox, but make no internet requests. `DELIVERY_MANIFEST.json` at the repository root lists each included file and its SHA-256 checksum; it excludes itself to avoid a self-referential hash. The ZIP uses fixed metadata and an explicit allowlist so it can be rebuilt identically from unchanged inputs.

This package demonstrates the review workflow only. The separate research project has 25 **AI-assisted** assessments; they are not included here and are not independent human validation. No claim of retrieval accuracy, causal information transmission or prize placement is made.
