# AGENTS.md

## Project

This repository builds an agent workflow governance system for agent-assisted software development.

The system defines how agents receive tasks, respect path boundaries, produce evidence, pass verification/review, and generate closeout or handoff records.

This repository is a workflow/governance project, not a production runtime platform.

## Read first

Before making changes, read:

- `chatgpt-pro-agent-workflow-roadmap.md`
- the active phase plan named by the user, such as `phase-1-development-plan.md`
- the active milestone file, such as `docs/milestones/M1.md`
- relevant files under `docs/agent/*`

If the roadmap or active phase plan is missing, stop and report a blocker before structural changes.

## Source of truth

Use repo files as the source of truth.

- Governance rules live in `AGENTS.md` and `docs/agent/*`.
- Task scope and acceptance live in the active milestone doc.
- Evidence lives under the active milestone evidence directory.
- Closeout and handoff live under the active milestone closeout directory.

Do not treat chat summaries, model confidence, comments, or issue tracker status as final acceptance evidence.

## Task rules

Every implementation task must have a stable task ID, such as `M1-T01`.

Do not use GitHub issue numbers, GitLab issue numbers, Multica IDs, branch names, or chat IDs as primary task IDs.

Follow the active milestone task contract exactly.

Do not use `done` as an acceptance state.

Use lifecycle status for workflow progress only:

- proposed
- ready
- in_progress
- blocked
- reviewing
- verifying
- closed

Gate result must be evidence-based:

- accepted
- failed
- inconclusive

## Work process

Before structural changes, follow:

1. SCAN: inspect repo state, existing files, active plan, active milestone, and git status.
2. PLAN: list files to create/modify, assumptions, blockers, and scope boundaries.
3. EXECUTE: make minimal focused changes.

Do not duplicate equivalent governance files.

Keep diffs small and reviewable.

Stop and report a blocker if the task requires destructive changes, missing source-of-truth files, unclear scope, or work outside the active phase plan.

## Path and safety rules

Never modify these paths unless the active task contract explicitly allows it:

- `.env`
- `.env.*`
- `secrets/**`
- `infra/prod/**`

Do not read, print, copy, or write secrets into docs, evidence, logs, tests, or closeout files.

Do not use production credentials or access production systems.

Do not assume VPN or internal network access unless explicitly allowed by the active task.

## Role boundaries

Builder may only modify files allowed by the task contract.

Test Builder may only modify tests or explicitly allowed files.

Verifier must not modify code.

Reviewer must not modify code.

Functional Tester should avoid implementation details when black-box testing is possible.

Orchestrator cannot override hard gate rules.

## Bridge boundaries

`tools/agent-bridge` is a governance tool.

It may validate task contracts, check path policy, read structured evidence, compute gate results, and write managed closeout.

It must not call model APIs, create external issues, merge code, push branches, or run autonomous loops unless the active phase plan explicitly allows it.

## Evidence rules

Evidence must be structured.

Verifier evidence must include actual command evidence and exit codes when verification is required.

Reviewer evidence must include concrete findings when issues are found.

Open P0/P1 reviewer findings block acceptance.

Missing required evidence makes the gate inconclusive.

Non-zero verifier command exit code makes the gate failed.

Model confidence alone is never evidence.

## Closeout rules

Closeout must be generated from evidence, not confidence.

Do not mark failed or inconclusive work as accepted.

Closeout should let a new session resume without chat history.

Preserve manual notes outside managed blocks.

## Implementation preferences

Prefer the repository's existing technology stack.

If no dominant stack exists, prefer a small Python 3 CLI for local tools.

Prefer small dependencies.

Document new dependencies and why they are necessary.

## Final response expectations

After implementation work, report:

- files changed
- commands run
- test results
- evidence produced or missing
- blockers
- follow-ups
- gate status if known
