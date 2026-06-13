# Multica Live POC

Phase 7 uses Multica as an external execution substrate only.

Bridge does not call Multica APIs.

Bridge does not create, update, assign, comment on, or close Multica tasks.

## Manual Export Workflow

1. Create or select a Multica task outside Bridge.
2. Ensure the Multica task references the stable Coshare `task_id`.
3. Let Multica own execution state such as assigned, running, blocked, completed, or failed.
4. Manually copy the relevant Multica task state into local Coshare evidence.
5. Run Bridge gate from local evidence.

## Evidence File

Use:

```text
docs/milestones/evidence/<task_id>/external-execution.yaml
```

Minimum Multica-derived shape:

```yaml
schema_version: 1
task_id: M7-T01
backend: multica
external_id: multica-task-manual-001
external_url: https://multica.example/workspaces/example/tasks/manual-001
execution_state: completed
assigned_agent: codex-agent
started_at: "2026-06-13T00:00:00Z"
completed_at: "2026-06-13T00:10:00Z"
blockers: []
result_summary: "Manual export from Multica UI."
produced_refs: []
conclusion: pass
collection:
  mode: manual_export
  network: false
  source: copied_from_multica_ui
```

## Authority Rules

Multica task state is evidence only.

These do not mean accepted:

- Multica completed
- Multica comment says done
- Multica assignee reports success

Bridge gate remains the final acceptance authority.

## Gate Rules

- missing external execution evidence -> `inconclusive` when required
- Multica failed -> `failed`
- Multica blocked -> `inconclusive`
- Multica completed with missing path-policy, verifier, or reviewer evidence -> `inconclusive`
- Multica completed with normal Bridge evidence passing -> `accepted` only if all required gates pass
- Multica completed must never bypass Bridge gate

## Security

Do not store:

- Multica tokens
- API keys
- auth headers
- cookies
- secrets
- production credentials
- customer data

Manual exports should contain normalized state only.
