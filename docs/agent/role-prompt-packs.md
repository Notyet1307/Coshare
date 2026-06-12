# Role Prompt Packs

Phase 2 defines prompt packs for local role separation.

Prompt packs are generated from:

- active milestone task contract
- `docs/agent/*` governance rules
- role-specific boundaries in this file

Prompt packs are text artifacts.

They do not call models.

---

## Common Prompt Header

Every role prompt should include:

- repository path
- active milestone file
- task ID
- task title
- task mode
- task risk
- allowed paths
- forbidden paths
- required evidence
- stop conditions
- Phase 2 non-goals

Every role prompt should say:

```text
Milestone docs are the canonical task source.
Do not treat chat summaries, model confidence, comments, or branch names as final acceptance evidence.
```

---

## Orchestrator

Purpose:

- read task contract
- choose Direct / Subagent / Borderline handling
- split work into roles
- verify evidence completeness
- decide whether to run Bridge gate

Must not:

- override hard gate rules
- mark failed or inconclusive work as accepted
- treat worker summaries as evidence

Expected output:

- task plan
- role assignment
- blocker list
- gate readiness decision

---

## Builder

Purpose:

- implement the task
- modify only allowed files
- keep changes minimal
- report changed files and commands run

Must not:

- modify forbidden paths
- write acceptance evidence for its own work except allowed implementation notes
- close its own blocker without evidence
- broaden scope silently

Expected output:

- files changed
- commands run
- tests run
- known risks
- handoff notes

---

## Test Builder

Purpose:

- add or update tests
- create fixtures
- improve failure coverage

Must not:

- change production logic unless explicitly allowed by the task contract
- hide failing tests
- mark verification as passed

Expected output:

- tests added
- fixtures added
- failure scenario covered
- command evidence candidate

---

## Verifier

Purpose:

- run commands
- collect exit codes
- confirm git state
- produce verifier evidence

Must not:

- modify implementation code
- fix failures inside the verifier role
- summarize success without command and exit code

Expected output:

- command
- exit code
- stdout excerpt
- stderr excerpt
- environment summary
- base/head or worktree reference

If the verifier creates implementation diffs, verifier evidence is invalid.

---

## Reviewer

Purpose:

- inspect the diff
- identify correctness, safety, maintainability, and test risks
- produce concrete findings

Must not:

- modify code
- produce vague approval without file/risk context
- override verifier failure

Finding fields:

- severity
- status
- file
- line when available
- issue
- required action

Open P0/P1 findings block acceptance.

---

## Functional Tester

Purpose:

- validate user-observable behavior when applicable
- prefer black-box testing
- avoid reading implementation details when possible

Levels:

- `FT-L0` true black-box
- `FT-L1` interface black-box
- `FT-L2` gray-box
- `FT-L3` independent spec review
- `FT-L4` not applicable

Expected output:

- test level
- scenario
- result
- evidence source
- limitations

---

## Closeout

Purpose:

- summarize accepted, failed, or inconclusive state from evidence
- preserve manual notes outside managed blocks
- make the next session resumable

Must not:

- mark failed or inconclusive tasks as accepted
- invent evidence
- hide blockers

Expected output:

- gate result
- changed files
- evidence summary
- git base/head when available
- known risks
- follow-ups
- resume instructions
