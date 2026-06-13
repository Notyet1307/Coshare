# agent-bridge

`agent-bridge` is a local governance CLI for Phase 1, Phase 2, Phase 3, Phase 4, and Phase 5.

It does not call Codex, DeepSeek, GitLab, Multica, or any model API.

Phase 3 adds explicit read-only GitHub PR/CI evidence collection.

Phase 4 adds GitHub Issue execution ticket evidence. GitHub Issues are mirrors only and are not the canonical task source.

Phase 5 adds GitHub delivery linkage and acceptance publication evidence. GitHub comments and labels are publication surfaces only.

GitHub reads are never the default. Use offline fixture mode for tests.

GitHub writes are never the default. Use dry-run unless the user explicitly authorizes a live write.

## Commands

```bash
tools/agent-bridge/agent-bridge validate docs/milestones/M1.md
tools/agent-bridge/agent-bridge task-info --task M2-T05 --milestone docs/milestones/M2.md
tools/agent-bridge/agent-bridge diff-check --task M1-T04 --worktree
tools/agent-bridge/agent-bridge diff-check --task M3-T06 --base main --head HEAD --include-path tools/agent-bridge/**
tools/agent-bridge/agent-bridge evidence-init --task M2-T06 --milestone docs/milestones/M2.md --dry-run
tools/agent-bridge/agent-bridge prompt-pack --task M2-T07 --role builder --milestone docs/milestones/M2.md
tools/agent-bridge/agent-bridge github-evidence --task M3-T06 --milestone docs/milestones/M3.md --from-json tools/agent-bridge/tests/fixtures/github/pass.json --dry-run
tools/agent-bridge/agent-bridge github-evidence --task M3-T06 --milestone docs/milestones/M3.md --from-json tools/agent-bridge/tests/fixtures/github/pass.json --write-evidence
tools/agent-bridge/agent-bridge github-evidence --task M3-T09 --milestone docs/milestones/M3.md --repo Notyet1307/Coshare --pr <number> --dry-run
tools/agent-bridge/agent-bridge issue-plan --milestone docs/milestones/M4.md --repo Notyet1307/Coshare --json
tools/agent-bridge/agent-bridge issue-export --task M4-T06 --milestone docs/milestones/M4.md --repo Notyet1307/Coshare --json
tools/agent-bridge/agent-bridge issue-status --task M4-T11 --milestone docs/milestones/M4.md --from-json tools/agent-bridge/tests/fixtures/issues/pass.json --write-evidence --json
tools/agent-bridge/agent-bridge issue-comment --task M4-T11 --milestone docs/milestones/M4.md --repo Notyet1307/Coshare --issue <number> --write-evidence --json
tools/agent-bridge/agent-bridge delivery-plan --milestone docs/milestones/M5.md --repo Notyet1307/Coshare --json
tools/agent-bridge/agent-bridge delivery-link --task M5-T10 --milestone docs/milestones/M5.md --from-json tools/agent-bridge/tests/fixtures/delivery/pass.json --write-evidence --json
tools/agent-bridge/agent-bridge delivery-status --task M5-T10 --milestone docs/milestones/M5.md --json
tools/agent-bridge/agent-bridge publish-status --task M5-T10 --milestone docs/milestones/M5.md --target-surface both --write-evidence --json
tools/agent-bridge/agent-bridge delivery-closeout --milestone docs/milestones/M5.md --milestone-name M5 --dry-run --json
tools/agent-bridge/agent-bridge gate --task M3-T09
tools/agent-bridge/agent-bridge closeout --milestone M3 --milestone-name M3 --dry-run
tools/agent-bridge/agent-bridge gate --task M1-T08
tools/agent-bridge/agent-bridge closeout --task M1-T08
tools/agent-bridge/agent-bridge closeout --milestone-name M1 --dry-run --json
tools/agent-bridge/agent-bridge closeout --milestone-name M1
```

All commands support readable output.

These commands support `--json`:

- `validate`
- `task-info`
- `diff-check`
- `evidence-init`
- `prompt-pack`
- `github-evidence`
- `issue-plan`
- `issue-export`
- `issue-status`
- `issue-comment`
- `delivery-plan`
- `delivery-link`
- `delivery-status`
- `publish-status`
- `delivery-closeout`
- `gate`
- `closeout`

## Phase 2 Notes

Phase 2 keeps `docs/milestones/M1.md` as the default milestone for backward compatibility.

Use `--milestone docs/milestones/M2.md` for Phase 2 tasks.

Task-scoped commands may infer `docs/milestones/M2.md`, `docs/milestones/M3.md`, `docs/milestones/M4.md`, or `docs/milestones/M5.md` from task IDs such as `M2-T05`, `M3-T09`, `M4-T11`, or `M5-T10` when `--milestone` is omitted.

Milestone arguments also accept shorthand values such as `M2`, `M3`, `M4`, and `M5`.

`evidence-init` creates skeleton evidence only. It does not mark evidence as passing.

`prompt-pack` generates role prompt text only. It does not call model APIs.

`git_range` path-policy evidence may use `base_sha` / `head_sha`. The gate validates that both commits resolve and that claimed `changed_files` match the git range.

For multi-task commits, `diff-check` supports `--include-path` to validate only the path subset owned by the active task. The generated evidence records `source.include_paths`, and gate recomputes the same filtered source.

## Phase 3 Notes

Phase 3 keeps milestone docs as the canonical task source.

GitHub PR numbers, PR URLs, branches, and CI URLs are evidence references only.

`github-evidence` supports:

- `--from-json <fixture-path>` for offline fixture mode
- `--repo <owner/name> --pr <number>` for explicit live GitHub reads through `gh`
- `--dry-run` for preview
- `--write-evidence` to write normalized evidence files

Expected Phase 3 evidence files:

- `github-pr.yaml`
- `github-ci.yaml`
- `github-reviews.yaml`
- `github-branch-protection.yaml`

Live GitHub reads are read-only.

The command must not:

- create GitHub Issues
- sync GitHub Issues
- create PRs
- push branches
- merge PRs
- comment on PRs
- print or write tokens

If `gh` auth is missing for a live read, the command returns `inconclusive`.

Tests must use offline fixture mode and must not require live GitHub auth.

Gate consumes GitHub evidence only when a task contract declares `required_github_evidence`.

## Phase 4 Notes

Phase 4 keeps milestone docs as the canonical task source.

GitHub Issue numbers, URLs, labels, assignees, and comments are execution ticket references only.

`issue-plan` reads milestone contracts and reports issue mapping gaps or duplicate issue refs.

`issue-export` generates an issue title/body from a task contract. It defaults to dry-run. Live issue create/edit requires explicit `--write`.

`issue-status` supports:

- `--from-json <fixture-path>` for offline fixture mode
- `--repo <owner/name> --issue <number>` for explicit live GitHub reads through `gh`
- `--write-evidence` to write normalized `github-issue.yaml`

`issue-comment` generates a managed Bridge gate-summary comment body. It defaults to dry-run. Live comment posting requires explicit `--write`. It may write `github-issue-comment.yaml` when `--write-evidence` is provided.

Expected Phase 4 evidence files:

- `github-issue.yaml`
- `github-issue-comment.yaml`
- `issue-sync-report.yaml`

Live GitHub reads are read-only.

Live GitHub writes must be separately authorized by the user.

The Issue adapter must not:

- make GitHub Issues canonical
- sync GitHub Issues into milestone docs
- create issues by default
- close issues automatically
- create PRs
- push branches
- merge PRs
- print or write tokens

If `gh` auth is missing for a live read/write, the command returns `inconclusive`.

Tests must use offline fixture mode and must not require live GitHub auth.

Gate consumes issue evidence only when a task contract declares `required_issue_evidence`.

## Phase 5 Notes

Phase 5 keeps milestone docs as the canonical task source.

GitHub Issues, PRs, CI checks, reviews, comments, and labels are evidence or publication surfaces only.

`delivery-plan` reads milestone contracts and existing local evidence to show task -> issue -> PR -> CI/review -> gate -> closeout linkage. It performs no remote writes.

`delivery-link` creates or validates `delivery-linkage.yaml`. It supports offline fixture mode and local evidence mode.

`delivery-status` reports current delivery linkage status from structured evidence.

`publish-status` generates a managed status comment body. It defaults to dry-run. Live writes require explicit `--write` and separate user authorization.

`delivery-closeout` writes closeout with delivery linkage summaries.

Expected Phase 5 evidence files:

- `delivery-linkage.yaml`
- `acceptance-publication.yaml`
- `github-status-comment.yaml`

The delivery adapter must not:

- make GitHub Issues canonical
- update milestone docs from GitHub
- create PRs
- push branches
- merge PRs
- auto-close issues
- use closing keywords such as closes, fixes, or resolves
- print or write tokens

Gate consumes delivery evidence only when a task contract declares `required_delivery_evidence`.

## Phase 6 Notes

Phase 6 keeps Coshare as the governance and acceptance layer while treating external execution platforms as evidence sources only.

Bridge reads local `external-execution.yaml` when a task contract declares:

```yaml
required_external_execution_evidence:
  - execution
```

Expected Phase 6 evidence file:

- `external-execution.yaml`

External execution state is not final acceptance.

The Phase 6 external execution evidence support must not:

- call Multica APIs
- call model APIs
- create external execution items
- schedule workers
- run autonomous loops
- create PRs
- push branches
- merge PRs
- perform live GitHub writes
- print or write tokens

## Exit Codes

| Result | Exit code |
|---|---:|
| valid / pass / accepted | 0 |
| invalid / failed | 1 |
| inconclusive | 2 |
| tool error | 3 |

## Testing

```bash
python3 -m unittest discover tools/agent-bridge/tests
```
