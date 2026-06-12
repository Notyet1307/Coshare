# PR CI Gates

Phase 3 allows Bridge gate logic to consume normalized GitHub PR/CI evidence.

Milestone docs remain canonical.

GitHub state is evidence only.

---

## Gate Results

Valid gate results remain:

- `accepted`
- `failed`
- `inconclusive`

GitHub evidence can influence gate checks only when the active task contract requires it or when a Phase 3 command is explicitly evaluating GitHub evidence.

When required GitHub evidence is missing, the result is `inconclusive`, not accepted.

When present GitHub evidence contradicts task evidence, the result is `failed` unless the active task contract explicitly allows the mismatch.

---

## PR Gate Rules

PR evidence passes when:

- PR evidence exists.
- PR repo and PR number are present.
- PR state is compatible with the task requirement.
- PR is not draft unless draft is explicitly allowed.
- base/head branch and SHA are present.
- head SHA matches CI and review evidence when those files exist.
- head SHA matches task evidence head SHA when the task requires SHA consistency.

PR evidence fails when:

- required PR is closed without merge.
- required head SHA conflicts with CI evidence.
- required head SHA conflicts with task evidence.
- evidence `task_id` does not match.

PR evidence is inconclusive when:

- PR cannot be read.
- auth is unavailable.
- mergeability data is unavailable.
- PR is draft and task does not allow draft.
- required fields are missing.
- task evidence head SHA is required but unavailable.

---

## CI Gate Rules

CI evidence passes when:

- CI evidence exists.
- head SHA matches PR evidence when PR evidence exists.
- head SHA matches task evidence head SHA when the task requires SHA consistency.
- required checks are known or explicitly not required by the task.
- required checks are successful, skipped, or neutral according to the task policy.
- no failed required check exists.

CI evidence fails when:

- a required check failed.
- a required workflow conclusion is failure, cancelled, timed_out, or action_required.
- CI head SHA conflicts with PR head SHA.
- CI head SHA conflicts with task evidence head SHA.

CI evidence is inconclusive when:

- checks are pending.
- checks are missing.
- required checks are unknown.
- GitHub Actions data is unavailable.
- auth is unavailable.
- task evidence head SHA is required but unavailable.

---

## Review Gate Rules

Review evidence passes when:

- review evidence exists when required.
- no open blocking review exists.
- no unresolved requested changes exist.

Review evidence fails when:

- requested changes are open.
- blocking review evidence is unresolved.
- review evidence targets a different head SHA when commit ID is required.

Review evidence is inconclusive when:

- review data is unavailable.
- review data is missing when required.
- review state cannot be normalized.

---

## Branch Protection Rules

Branch protection evidence passes when:

- source is available.
- required checks are listed.
- required review policy is listed when available.
- CI evidence covers required checks.

Branch protection evidence is inconclusive when:

- source is unavailable.
- token lacks permission to read branch protection.
- repository does not expose branch protection through available API.

Branch protection evidence should not fail a task simply because read permission is missing.

---

## Closeout Rules

Closeout should include GitHub evidence summary:

- PR URL
- PR state
- head SHA
- CI conclusion
- CI/check result details
- review conclusion
- review summary
- branch protection availability
- evidence file references

Closeout must distinguish:

- accepted evidence
- failed evidence
- inconclusive evidence

Do not mark failed or inconclusive GitHub evidence as accepted.

Closeout must not include tokens, auth headers, credential helper output, or unredacted raw API responses.

---

## Non-Goals

PR/CI gates must not:

- create PRs
- merge PRs
- push branches
- sync GitHub Issues
- treat GitHub Issues as canonical tasks
- call model APIs
- run autonomous loops
- store tokens
- store raw auth output
