# GitHub Issue Adapter

Phase 4 introduces GitHub Issues as execution tickets.

Milestone docs remain canonical.

GitHub Issues are mirrors and coordination aids only. They do not own task scope, acceptance, lifecycle status, gate result, or closeout.

---

## Commands

Expected Bridge commands:

- `issue-plan`
- `issue-export`
- `issue-status`
- `issue-comment`

All remote write behavior must be explicit.

Offline and dry-run behavior is the default.

---

## Issue Body Markers

Every managed issue body must include:

```md
<!-- agent-bridge:task-id M4-T01 -->
<!-- agent-bridge:canonical-owner repo-doc -->
<!-- agent-bridge:task-revision 1 -->
```

Rules:

- `task-id` must match the active task contract.
- `canonical-owner` must be `repo-doc`.
- `task-revision` must match the milestone task revision.
- missing or stale revision makes gate inconclusive.
- task ID mismatch or owner mismatch fails gate.

---

## Evidence Files

Issue evidence lives under:

```text
docs/milestones/evidence/<task_id>/
```

Expected files:

- `github-issue.yaml`
- `github-issue-comment.yaml` when a managed comment is generated
- `issue-sync-report.yaml` when a sync/report step is generated

`github-issue.yaml` shape:

```yaml
schema_version: 1
task_id: M4-T01
source: github_issue
repository: Notyet1307/Coshare
issue_number: 44
issue_url: https://github.com/Notyet1307/Coshare/issues/44
issue_state: open
title: "[M4-T01] Example"
labels:
  - agent-bridge
milestone: M4
assignees: []
body_marker_task_id: M4-T01
body_marker_canonical_owner: repo-doc
body_marker_task_revision: "1"
task_revision: 1
sync_mode: offline_fixture
drift_detected: false
drift_reasons: []
duplicate_issue_numbers: []
conclusion: pass
collection:
  mode: offline_fixture
  network: false
  source: from-json
```

Collection metadata must not contain tokens, auth headers, cookies, or raw credential output.

---

## Gate Rules

Issue evidence passes only when:

- required issue evidence exists
- evidence `task_id` matches the active task
- `source` is `github_issue`
- body task marker matches the active task ID
- body canonical owner marker matches `repo-doc`
- body task revision marker matches the active task revision
- no duplicate issue for the task is reported
- conclusion is `pass`

Issue evidence fails when:

- task marker points to a different task
- canonical owner marker is not `repo-doc`
- duplicate issue numbers are reported
- evidence conclusion is `fail`

Issue evidence is inconclusive when:

- required issue evidence is missing
- task revision marker is missing or stale
- live GitHub read is unavailable
- issue is closed while Bridge gate is not accepted
- issue evidence conclusion is `inconclusive`

Issue evidence cannot override path-policy, verifier, reviewer, blocker, or PR/CI failures.

---

## Non-Goals

The adapter must not:

- make GitHub Issues canonical
- sync issue state back into milestone docs
- create issues by default
- comment by default
- call model APIs
- push, merge, or create PRs
- store secrets
