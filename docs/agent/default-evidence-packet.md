# Default Evidence Packet

The default task evidence folder is:

```text
docs/milestones/evidence/<task_id>/
  external-execution.yaml
  path-policy.yaml
  verifier.yaml
  reviewer.yaml
  gate-report.yaml
```

This packet is enough for the default manual operating model.

## `external-execution.yaml`

`external-execution.yaml` is copied manually from Multica or another execution surface.

It records execution state only.

It is not acceptance.

Expected content:

- backend
- external ID or URL
- execution state
- assigned agent
- blockers
- produced refs
- conclusion

## `path-policy.yaml`

`path-policy.yaml` records changed files and the allowed / forbidden path result.

It proves whether the task touched only paths allowed by the task contract.

Use `diff-check` to create or refresh it.

## `verifier.yaml`

`verifier.yaml` records real commands run by the verifier.

It must include:

- command
- exit code
- relevant stdout excerpt
- relevant stderr excerpt
- conclusion

Command success or failure is evidence. A summary without commands is not enough.

## `reviewer.yaml`

`reviewer.yaml` records real review findings.

It should include:

- findings
- severity
- status
- file and line when available
- required action
- conclusion

Open P0/P1 findings block acceptance.

## `gate-report.yaml`

`gate-report.yaml` records the Bridge final task gate result.

It is generated from evidence.

It is the file a later session should inspect before trusting a task as accepted.
