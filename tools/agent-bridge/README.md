# agent-bridge

`agent-bridge` is a local governance CLI for Phase 1.

It does not call Codex, DeepSeek, GitHub, GitLab, Multica, or any model API.

## Commands

```bash
tools/agent-bridge/agent-bridge validate docs/milestones/M1.md
tools/agent-bridge/agent-bridge diff-check --task M1-T04 --worktree
tools/agent-bridge/agent-bridge gate --task M1-T08
tools/agent-bridge/agent-bridge closeout --task M1-T08
tools/agent-bridge/agent-bridge closeout --milestone-name M1
```

All commands support readable output. `validate`, `diff-check`, `gate`, and `closeout` support `--json`.

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
