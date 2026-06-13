# Advanced Evidence Adapters

These capabilities remain available, but they are optional.

They are not part of the default daily operating model.

Use them only for formal PR / CI / Issue / delivery workflows.

## GitHub PR / CI Evidence

Use when a task must prove PR, branch, head SHA, CI, check run, review, or branch protection facts.

Related command:

- `github-evidence`

Expected files:

- `github-pr.yaml`
- `github-ci.yaml`
- `github-reviews.yaml`
- `github-branch-protection.yaml`

## GitHub Issue Evidence

Use when a task has a GitHub Issue execution ticket or managed issue status comment.

Related commands:

- `issue-plan`
- `issue-export`
- `issue-status`
- `issue-comment`

Expected files:

- `github-issue.yaml`
- `github-issue-comment.yaml`
- `issue-sync-report.yaml`

## Delivery Linkage

Use when a task must connect issue, PR, CI/review, Bridge gate, and closeout into one delivery chain.

Related commands:

- `delivery-plan`
- `delivery-link`
- `delivery-status`
- `delivery-closeout`

Expected file:

- `delivery-linkage.yaml`

## Acceptance Publication

Use when a task must prepare a dry-run publication of Bridge gate and delivery status to GitHub surfaces.

Related command:

- `publish-status`

Expected file:

- `acceptance-publication.yaml`

## GitHub Status Comments

Use when a task needs a managed status comment body.

Related command:

- `publish-status`
- `issue-comment`

Expected files:

- `github-status-comment.yaml`
- `github-issue-comment.yaml`

## Default Rule

Do not start with these adapters.

Start with the default evidence packet and the five daily commands.

Add advanced evidence only when the task contract explicitly requires it.
