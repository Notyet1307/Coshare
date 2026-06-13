# Bridge Lite

Bridge Lite is the default mental model for daily Coshare use.

```text
Coshare Bridge only answers:
"Can this task be accepted?"
```

## What Bridge Is

Bridge is the acceptance gate.

It consumes local evidence and computes one result:

- `accepted`
- `failed`
- `inconclusive`

Bridge is not an execution platform.

Bridge is not a scheduler, dashboard, worker registry, Multica client, GitHub client, or model runner.

## Ownership Split

Repo docs own:

- task contract
- allowed and forbidden paths
- acceptance rules
- required evidence

Multica owns:

- execution visibility
- task assignment
- running / blocked / completed state
- execution comments and progress

GitHub owns:

- code
- branches
- pull requests
- CI
- review facts

Bridge owns:

- local evidence validation
- gate calculation
- closeout from evidence

## Acceptance Rule

Multica completed does not mean accepted.

GitHub Issue closed does not mean accepted.

PR merged does not mean accepted.

CI passed does not mean accepted.

Bridge gate `accepted` means accepted.

## Daily Commands

Daily users only need these commands:

```bash
tools/agent-bridge/agent-bridge validate docs/milestones/M9.md --json
tools/agent-bridge/agent-bridge task-info --task M9-T01 --milestone docs/milestones/M9.md --json
tools/agent-bridge/agent-bridge diff-check --task M9-T01 --milestone docs/milestones/M9.md --worktree --json
tools/agent-bridge/agent-bridge gate --task M9-T01 --milestone docs/milestones/M9.md --json
tools/agent-bridge/agent-bridge closeout --task M9-T01 --milestone docs/milestones/M9.md --milestone-name M9 --dry-run --json
```

Everything else is optional unless the task contract requires it.
