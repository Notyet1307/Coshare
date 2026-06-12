# agent-bridge

`agent-bridge` is a local governance CLI for Phase 1, Phase 2, and Phase 3.

It does not call Codex, DeepSeek, GitLab, Multica, or any model API.

Phase 3 adds explicit read-only GitHub PR/CI evidence collection.

GitHub reads are never the default. Use offline fixture mode for tests.

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
- `gate`
- `closeout`

## Phase 2 Notes

Phase 2 keeps `docs/milestones/M1.md` as the default milestone for backward compatibility.

Use `--milestone docs/milestones/M2.md` for Phase 2 tasks.

Task-scoped commands may infer `docs/milestones/M2.md` or `docs/milestones/M3.md` from task IDs such as `M2-T05` or `M3-T09` when `--milestone` is omitted.

Milestone arguments also accept shorthand values such as `M2` and `M3`.

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
