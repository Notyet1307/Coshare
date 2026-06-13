# Multica Manual Trial

Phase 8 is a real manual Multica task trial.

Bridge does not call Multica APIs.

Bridge does not create, update, assign, comment on, close, or read live Multica tasks.

Bridge consumes local evidence only.

## Manual Checklist

1. Create or select a Multica workspace.
2. Create a Multica task manually.
3. Put this marker in the Multica task body:

   ```text
   Coshare task_id: M8-T01
   Canonical owner: repo-doc
   Bridge acceptance required: yes
   Multica completed does not mean accepted.
   ```

4. Assign the task to an agent in Multica.
5. Let Multica run the task.
6. Observe assigned/running/completed/failed/blocked state.
7. Record blocker comments if any.
8. Copy the final normalized state into `external-execution.yaml`.
9. Run Bridge gate.
10. Confirm completed-without-Bridge-evidence is inconclusive.
11. Add normal Bridge evidence only if it reflects real commands/review.
12. Rerun Bridge gate.
13. Record whether Multica reduced manual coordination.

## Evidence File

Store the manual export at:

```text
docs/milestones/evidence/M8-T01/external-execution.yaml
```

Template shape:

```yaml
schema_version: 1
task_id: M8-T01
backend: multica
external_id: "<real-multica-task-id>"
external_url: "<real-multica-task-url>"
execution_state: assigned | running | blocked | completed | failed
assigned_agent: "<agent-name>"
started_at: null
completed_at: null
blockers: []
result_summary: ""
produced_refs: []
conclusion: pass | fail | inconclusive
collection:
  mode: manual_export
  network: false
  source: copied_from_multica_ui
```

## Gate Rules

- missing external execution evidence -> `inconclusive` when required
- Multica failed -> `failed`
- Multica blocked -> `inconclusive`
- Multica completed with missing path-policy, verifier, or reviewer evidence -> `inconclusive`
- Multica completed can become `accepted` only when all required Bridge evidence passes
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

## Decision Outcomes

After the manual trial, choose one:

- Continue to Multica read-only export adapter.
- Continue manual-export only.
- Try OpenHands instead.
- Stay GitHub-only.
- Pause external platform work.
