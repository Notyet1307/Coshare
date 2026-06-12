# Git Execution

Phase 2 adds Git-backed execution governance.

Milestone docs remain the canonical task source.

Git is the source of truth for code facts:

- branch
- commit SHA
- base/head range
- changed files
- dirty worktree state

Git does not replace task contracts, evidence, or gate rules.

---

## Execution Sources

Every path-policy evidence record must declare a source.

Supported source modes:

```yaml
source:
  mode: worktree
```

```yaml
source:
  mode: git_range
  base_sha: <sha>
  head_sha: <sha>
```

Phase 1 evidence may use `base` and `head`.

Phase 2 evidence should prefer `base_sha` and `head_sha`.

---

## Worktree Evidence

Worktree evidence describes the current dirty working tree.

It must include:

- tracked changes
- untracked files
- renamed paths
- deleted paths

Worktree evidence is only valid for the current repo state.

If the worktree changes after evidence is generated, the evidence is stale.

Stale worktree evidence must be `inconclusive`.

---

## Git Range Evidence

Git range evidence describes a fixed commit range.

It must include:

- `base_sha`
- `head_sha`
- changed files from `git diff --name-status base_sha head_sha`

Rules:

- `base_sha` must resolve.
- `head_sha` must resolve.
- claimed `changed_files` must match the git range.
- a non-empty claimed diff with `base_sha == head_sha` is invalid.
- an empty range can prove no committed diff, but it does not prove dirty worktree safety.

---

## Path Policy

Task contracts own path policy:

- `allowed_paths`
- `forbidden_paths`
- `managed_artifact_paths`

Rules:

- forbidden paths override allowed paths.
- managed artifact paths are allowed only for evidence and closeout artifacts.
- files outside allowed and managed paths fail path policy.
- renamed files must check both old and new paths.
- deleted files must check the deleted path.

Forbidden path violations are `failed`.

Stale or inconsistent evidence is `inconclusive`.

---

## Branches

Branch names are useful execution metadata.

Branch names are not primary task IDs.

Use stable task IDs such as:

```text
M2-T05
```

Do not use branch names as acceptance evidence.

---

## Base And Head Selection

For a task implementation, prefer:

```text
base_sha = commit before the task starts
head_sha = commit after the task implementation is complete
```

For a worktree-only task, use worktree evidence before commit.

For final closeout, prefer git range evidence where possible.

---

## Invalid Evidence Cases

The gate should reject or block these cases:

- evidence `task_id` does not match the task.
- evidence source mode is missing.
- `base_sha` does not resolve.
- `head_sha` does not resolve.
- claimed changed files differ from git.
- forbidden paths changed.
- worktree evidence claims old dirty state after the worktree changed.
- verifier command references a different commit than the path-policy evidence.

---

## Resume Requirements

Git-aware closeout should let a new session resume without chat history.

Closeout should include:

- task ID
- gate result
- branch when available
- base/head when available
- changed files
- commands run
- unresolved risks
- next action

---

## Dogfood Requirement

At least one Phase 2 task should make a small real repo change and prove it with Git-backed evidence.

The dogfood change should be intentionally narrow.

It should record:

- task ID
- source mode
- base/head or worktree state
- changed files
- commands run
- reviewer result
- final gate result

The dogfood evidence should stay small enough for a later session to audit without reading unrelated task history.
