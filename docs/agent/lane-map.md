# Lane Map

Phase 2 uses lane maps to make parallel work explicit.

Lane maps describe file ownership, role ownership, and merge order for a milestone or task group.

Lane maps do not replace task contracts.

The active milestone remains the canonical task source.

---

## Lane Map Goals

A lane map should answer:

- which task owns which files
- which role works on which task
- which tasks can run in parallel
- which tasks must wait
- what evidence each lane must produce
- what conflicts stop execution

---

## Minimal Shape

Use this shape inside milestone docs or a dedicated lane map section:

```yaml
lane_map:
  milestone: M2
  lanes:
    - lane_id: docs
      owner_role: builder
      task_ids:
        - M2-T01
        - M2-T02
      owned_paths:
        - phase-2-development-plan.md
        - docs/agent/git-execution.md
      depends_on: []
      evidence_required:
        - reviewer

    - lane_id: bridge
      owner_role: builder
      task_ids:
        - M2-T05
        - M2-T06
      owned_paths:
        - tools/agent-bridge/**
      depends_on:
        - docs
      evidence_required:
        - verifier
        - reviewer
```

---

## Ownership Rules

Rules:

- a file should have one primary lane owner.
- shared governance docs should be edited serially.
- tests may belong to the same lane as the implementation they verify.
- evidence paths belong to the task that generated them.
- closeout belongs to the verification / closeout lane.

If two lanes need the same file, record the dependency.

Do not rely on chat agreement for ownership.

---

## Parallel Work Rules

Parallel work is allowed only when:

- task contracts are clear.
- allowed paths do not overlap.
- one lane does not depend on unmerged output from another lane.
- each lane has explicit evidence requirements.

Parallel work must stop when:

- unassigned files are touched.
- a lane modifies another lane's owned file.
- repeated failed attempts occur without new evidence.
- worker output is vague or missing changed files.
- path policy cannot be computed.

---

## Merge Order

Suggested merge order:

1. docs and contract changes
2. Bridge command skeleton
3. command tests and fixtures
4. gate integration
5. dogfood task
6. independent verification
7. closeout

Do not merge a later lane to hide failure in an earlier lane.

---

## Reporting Rules

Lane reports should include:

- lane ID
- task IDs
- changed files
- commands run
- evidence paths
- blockers
- handoff notes

Reports are not final acceptance evidence unless converted into structured evidence and accepted by Bridge gate.
