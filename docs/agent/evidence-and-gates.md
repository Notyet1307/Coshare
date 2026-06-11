# Evidence And Gates

Phase 1 acceptance is evidence-based.

Bridge computes gate results from task contracts, path-policy results, verifier evidence, reviewer evidence, functional test evidence, blocker records, and closeout state.

Valid gate results:

- `accepted`
- `failed`
- `inconclusive`

## Evidence Location

Evidence lives under:

```text
docs/milestones/evidence/<task_id>/
```

Expected files:

- `verifier.yaml`
- `reviewer.yaml`
- `functional-test.yaml`
- `blockers.yaml`
- `path-policy.yaml`
- `gate-report.yaml`

All evidence files should include:

```yaml
schema_version: 1
task_id: M1-T01
```

## Verifier Evidence

Verifier evidence must include commands and exit codes when verification is required.

Minimum shape:

```yaml
schema_version: 1
task_id: M1-T01
verifier:
  commands:
    - command: "python3 -m unittest discover tools/agent-bridge/tests"
      exit_code: 0
      stdout_excerpt: ""
      stderr_excerpt: ""
  conclusion: pass
```

Rules:

- Missing verifier evidence when required means `inconclusive`.
- Missing command or `exit_code` means `inconclusive`.
- Any non-zero verifier exit code means `failed`.
- Verifier-created code diffs invalidate verifier evidence.
- `"tests passed"` without command and exit code is invalid.

## Path Policy Evidence

Path policy evidence must include an explicit result.

Rules:

- Missing path-policy evidence means `inconclusive`.
- Empty path-policy evidence means `inconclusive`.
- Only explicit `result: pass` satisfies the path-policy gate.
- `result: fail`, `result: failed`, or forbidden path violations mean `failed`.

## Reviewer Evidence

Minimum shape:

```yaml
schema_version: 1
task_id: M1-T01
reviewer:
  findings: []
  conclusion: pass
```

Findings should include:

- `severity`
- `status`
- `file`
- `line` when available
- `issue`
- `required_action`

Rules:

- Open P0 or P1 reviewer findings block acceptance.
- Missing reviewer evidence when required means `inconclusive`.
- Reviewer evidence must include an explicit `reviewer.conclusion`.
- Empty reviewer evidence does not count as a pass.
- Reviewer pass cannot override verifier failure.

## Functional Test Evidence

Functional test levels:

- `FT-L0` true black-box
- `FT-L1` interface black-box
- `FT-L2` gray-box
- `FT-L3` independent spec review
- `FT-L4` not applicable

If functional test evidence is required and missing, the gate is `inconclusive`.

If functional test evidence fails, the gate is `failed`.

## Final Gate

A task is accepted only when:

- task contract is valid
- required evidence exists
- path-policy evidence exists and result is pass
- verifier evidence passes when required
- reviewer evidence has no open P0/P1 findings
- functional test passes when required
- no unresolved blocking blocker exists
- closeout exists when final acceptance requires it

Model confidence and chat summaries do not count as evidence.
