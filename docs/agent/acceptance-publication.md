# Acceptance Publication

Acceptance publication communicates Bridge gate and delivery status to GitHub surfaces.

It does not create acceptance.

Bridge gate remains the final acceptance authority.

---

## Evidence File

File:

```text
acceptance-publication.yaml
```

Minimum shape:

```yaml
schema_version: 1
task_id: M5-T01
repository: Notyet1307/Coshare
issue_number: 501
pr_number: 5
target_surface: both
mode: dry_run
managed_comment_found: false
managed_comment_url: null
comment_body_summary: "Task M5-T01 delivery status..."
labels_planned_or_applied: []
remote_write_performed: false
generated_at: "2026-06-13T00:00:00Z"
conclusion: pass
```

---

## Rules

Publication may target:

- GitHub Issue
- GitHub PR
- both

Default mode is dry-run.

Remote write requires explicit `--write` and a separate user request.

Publication must not:

- auto-close issues
- merge PRs
- create PRs
- push branches
- use closing keywords
- store raw logs
- store raw comments
- store tokens

Publication should use references such as:

- `Refs #123`
- `Related to #123`

Do not use:

- `closes`
- `fixes`
- `resolves`

---

## Gate

Missing required publication evidence is inconclusive.

Duplicate managed comments are inconclusive until resolved.

Live GitHub auth failures are inconclusive, not acceptance.
