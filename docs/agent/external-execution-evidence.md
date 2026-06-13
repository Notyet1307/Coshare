# External Execution Evidence

External execution evidence records state from an execution substrate such as Multica, OpenHands, OpenCode, Goose, or another agent runtime.

The evidence is backend-neutral.

It is not final acceptance.

## Location

External execution evidence lives under:

```text
docs/milestones/evidence/<task_id>/external-execution.yaml
```

## Schema

```yaml
schema_version: 1
task_id: M6-T05
backend: multica-like-offline-fixture
external_id: multica-fixture-001
external_url: null
execution_state: completed
assigned_agent: fixture-agent
started_at: "2026-06-13T00:00:00Z"
completed_at: "2026-06-13T00:10:00Z"
blockers: []
result_summary: "External fixture reports execution completed."
produced_refs:
  - type: patch
    ref: local-fixture
conclusion: pass
```

## Required Fields

- `schema_version`
- `task_id`
- `backend`
- `external_id`
- `external_url`
- `execution_state`
- `assigned_agent`
- `started_at`
- `completed_at`
- `blockers`
- `result_summary`
- `produced_refs`
- `conclusion`

## Execution State

Recommended values:

- `assigned`
- `running`
- `blocked`
- `completed`
- `failed`
- `cancelled`

## Gate Rules

- missing required external execution evidence -> `inconclusive`
- `execution_state: failed` -> `failed`
- `conclusion: fail` -> `failed`
- `execution_state: blocked` -> `inconclusive`
- open blockers -> `inconclusive`
- `execution_state: completed` with `conclusion: pass` only passes the external execution evidence check

Passing external execution evidence does not imply final acceptance.

Final acceptance still requires normal Bridge evidence gates to pass:

- path-policy evidence
- verifier evidence when required
- reviewer evidence when required
- functional test evidence when required
- blocker evidence
- GitHub PR/CI evidence when required
- Issue evidence when required
- delivery evidence when required
- closeout when required by the workflow

## Security

Evidence must not contain:

- tokens
- auth headers
- cookies
- API keys
- production credentials
- raw private logs
- customer data

Use offline fixture data for Phase 6.
