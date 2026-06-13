# Daily Operating Flow

This is the default manual Coshare flow.

It avoids the advanced adapter surface unless the task explicitly needs formal PR / CI / Issue / delivery evidence.

## Flow

1. Pick or create `task_id` in the milestone doc.
2. Create a Multica task manually using the `task_id`.
3. Let the Multica agent execute.
4. Copy normalized Multica state into `external-execution.yaml`.
5. Run `diff-check` to create path-policy evidence.
6. Add verifier evidence from real commands.
7. Add reviewer evidence from real review.
8. Run `gate`.
9. If accepted, write closeout.
10. If failed or inconclusive, handle the blocker or missing evidence.

## Daily Commands

Validate the milestone:

```bash
tools/agent-bridge/agent-bridge validate docs/milestones/M9.md --json
```

Inspect a task:

```bash
tools/agent-bridge/agent-bridge task-info --task M9-T01 --milestone docs/milestones/M9.md --json
```

Create path-policy evidence:

```bash
tools/agent-bridge/agent-bridge diff-check --task M9-T01 --milestone docs/milestones/M9.md --worktree --write-evidence --json
```

Compute the gate:

```bash
tools/agent-bridge/agent-bridge gate --task M9-T01 --milestone docs/milestones/M9.md --write-report --json
```

Write closeout after acceptance:

```bash
tools/agent-bridge/agent-bridge closeout --task M9-T01 --milestone docs/milestones/M9.md --milestone-name M9 --json
```

## Failure Handling

If `gate` returns `failed`, fix the blocking evidence or implementation issue.

If `gate` returns `inconclusive`, add missing evidence or resolve stale evidence.

Do not convert Multica completed, PR merged, CI passed, or issue closed into accepted without Bridge gate acceptance.
