# Task Contract

Task contracts are the canonical task shape for Phase 1.

Contracts live in `docs/milestones/M1.md` inside fenced blocks with this exact info string:

````text
```yaml task-contract
...
```
````

## Required Fields

Every task contract must include:

- `schema_version`
- `task_id`
- `title`
- `canonical_owner`
- `revision`
- `mode`
- `risk`
- `lifecycle_status`
- `allowed_paths`
- `forbidden_paths`
- `managed_artifact_paths`
- `acceptance`
- `required_evidence`
- `backend_refs`
- `stop_conditions`

## Valid Values

```yaml
canonical_owner:
  - repo-doc

mode:
  - direct
  - subagent
  - borderline

risk:
  - low
  - medium
  - high

lifecycle_status:
  - proposed
  - ready
  - in_progress
  - blocked
  - reviewing
  - verifying
  - closed

required_evidence:
  verifier:
    - required
    - not_applicable
  reviewer:
    - required
    - not_applicable
  functional_test:
    - required
    - not_applicable
```

Do not use `done` as lifecycle status or gate status.

## Path Policy

All paths are repo-relative POSIX paths.

Rules:

- `forbidden_paths` override `allowed_paths`.
- `managed_artifact_paths` are for Bridge-generated evidence and closeout artifacts.
- Empty `allowed_paths` means no implementation file changes are allowed.
- To allow all paths, use `**` explicitly.
- Rename operations must check old and new paths.
- Delete operations must check deleted paths.
- Worktree checks must include untracked files.

## Primary ID

Use stable task IDs such as `M1-T01`.

Do not use GitHub issue numbers, GitLab issue numbers, Multica IDs, branch names, or chat IDs as primary task IDs.
