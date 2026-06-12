# Issue Sync Rules

Phase 4 does not implement bidirectional sync.

The word sync in this phase means controlled export/status/report behavior for execution tickets.

Milestone docs remain canonical.

---

## Allowed Flows

### Plan

`issue-plan` reads milestone task contracts and reports execution-ticket mapping.

It may report:

- missing `backend_refs.github_issue`
- duplicate issue references
- tasks that would need issue creation
- tasks that would update existing issues

It must not create, edit, or close issues.

### Export

`issue-export` turns a task contract into a managed issue title/body.

Default behavior is dry-run.

Live create/edit requires explicit `--write`.

### Status

`issue-status` reads an issue from offline fixture input or explicit live GitHub read.

It normalizes status into `github-issue.yaml`.

### Comment

`issue-comment` generates a managed gate-summary comment.

Default behavior is dry-run.

Live comment post requires explicit `--write`.

---

## Forbidden Flows

Do not implement:

- issue-to-doc sync
- GitHub Issue as task authority
- automatic status mutation from GitHub back to milestone docs
- automatic issue close/open from Bridge gate
- GitHub Projects sync
- label-driven task lifecycle changes
- comment parsing as acceptance evidence
- bulk issue writes without explicit user approval

---

## Drift Rules

Drift exists when issue evidence disagrees with the milestone task contract.

Blocking drift:

- issue task marker does not match task ID
- issue canonical owner marker is not `repo-doc`
- duplicate issues claim the same task ID

Inconclusive drift:

- issue task revision marker is missing
- issue task revision marker is stale
- issue is closed while Bridge gate is not accepted
- live read is unavailable

Drift must be recorded in `drift_reasons`.

Gate must use drift facts, not model confidence.

---

## Idempotency

Bridge-generated issue body and comment text must include stable markers.

Markers allow later tools to identify managed content without treating the whole issue as canonical.

Manual issue notes outside managed blocks should be preserved by any future live write design.

Phase 4 implementation may generate text, but it must not attempt full bidirectional merge logic.
