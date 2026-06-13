# Execution Platform Delegation

Phase 6 delegates execution coordination to an external substrate in principle, while keeping Coshare responsible for governance, evidence, gate calculation, and closeout.

The external substrate may be Multica, OpenHands, OpenCode, Goose, or a similar agent runtime.

## Ownership Split

External execution platform owns:

- task queue
- assignment
- runtime state
- progress comments
- blockers
- completed / failed execution state
- execution coordination

Coshare owns:

- stable `task_id`
- task contract shape
- canonical ownership rules
- allowed and forbidden paths
- evidence schemas
- evidence normalization
- deterministic Bridge gate
- closeout and handoff
- no-token and no-secret rules
- offline and dry-run defaults

## Authority Rules

External platform state is evidence only.

These states are not final acceptance:

- external completed
- agent says done
- GitHub Issue closed
- PR merged
- CI passed

Only Bridge gate `accepted` is final acceptance.

## Phase 6 Boundary

Phase 6 uses local evidence only.

Bridge must not:

- call Multica APIs
- call model APIs
- create external execution items
- schedule workers
- run autonomous loops
- write to GitHub
- store tokens or secrets

The POC proves whether Coshare can consume an external execution result while refusing to treat it as acceptance.
