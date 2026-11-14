# Independent review guide

No external reviewer or pilot is claimed yet. This guide makes the next review
concrete without treating author-written tests as independent validation.

1. Run the packaged report viewer and inspect a stale case, a policy mismatch,
   an unchanged pass and an outside-scope control. Check raw captured records;
   do not treat the green label or the model's prose as the conclusion.
2. In an isolated clone of a repository you know, choose a meaningful check and
   its source/test/configuration scope. Document why the scope is sufficient for
   that narrow claim. Use the capture CLI, then change a declared source file,
   a test and an untracked file. Verify again before rerunning tests.
3. Try a passing but unrelated command under a different policy. Confirm that
   its receipt is rejected by the required policy. Also test a correctly scoped
   fresh test command: it remains the baseline, not a competing failure case.
4. Record any unexpected acceptance or rejection, the policy, receipt,
   observation, exact repository revision and minimal reproduction. Distinguish
   a bug in the contract implementation from insufficient policy/dependency scope.
5. Report whether the changed-path and source view helped you review completion,
   how long it took, and whether configuring the scope was practical. Identify
   any extra work it imposed, especially benign edits that forced a rerun.

For an evaluation, freeze the tasks and policies before running, use someone
other than the author to review outcomes, and report denominators, exclusions,
misses, incorrect acceptances, incorrect rejections and effort. The included
controlled cases only validate specified contract behaviors. They do not estimate
ordinary agent error frequency or automatic claim-classification accuracy.
