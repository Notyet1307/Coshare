# agent-bridge

`agent-bridge` is a local governance CLI for Phase 1 and Phase 2.

It does not call Codex, DeepSeek, GitHub, GitLab, Multica, or any model API.

## Commands

```bash
tools/agent-bridge/agent-bridge validate docs/milestones/M1.md
tools/agent-bridge/agent-bridge task-info --task M2-T05 --milestone docs/milestones/M2.md
tools/agent-bridge/agent-bridge diff-check --task M1-T04 --worktree
tools/agent-bridge/agent-bridge evidence-init --task M2-T06 --milestone docs/milestones/M2.md --dry-run
tools/agent-bridge/agent-bridge prompt-pack --task M2-T07 --role builder --milestone docs/milestones/M2.md
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
- `gate`
- `closeout`

## Phase 2 Notes

Phase 2 keeps `docs/milestones/M1.md` as the default milestone for backward compatibility.

Use `--milestone docs/milestones/M2.md` for Phase 2 tasks.

`evidence-init` creates skeleton evidence only. It does not mark evidence as passing.

`prompt-pack` generates role prompt text only. It does not call model APIs.

`git_range` path-policy evidence may use `base_sha` / `head_sha`. The gate validates that both commits resolve and that claimed `changed_files` match the git range.

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
