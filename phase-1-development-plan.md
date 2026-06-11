# Phase 1 Development Plan

Version: 0.2  
Phase: Local Governance Baseline  
Canonical task source: repo milestone doc  
Execution backend: local only  
Platform integrations: none in Phase 1

---

## 0. Phase 1 Decision

Phase 1 builds the first usable local governance baseline for the agent workflow system.

Phase 1 is **not** a platform build.

It does not integrate Multica, GitHub Issues, GitLab, dashboards, auto-merge, long-running loops, or model APIs.

Phase 1 builds the minimum local layer that can answer these questions reliably:

1. What is the task?
2. Who is allowed to change what?
3. What evidence proves the task is complete?
4. Who decides accepted vs failed vs inconclusive?

The answer must come from repo files and structured evidence, not from chat memory or model confidence.

---

## 1. Source Material

Roadmap reference:

```text
chatgpt-pro-agent-workflow-roadmap.md
```

Phase 1 follows this roadmap position:

```text
milestone doc is the canonical task source
Codex Direct Mode is the default execution mode
Subagent Mode is used only for isolated roles
DeepSeek V4 Pro may provide independent reviewer evidence
Bridge only validates task contracts, path policy, evidence, gate results, and closeout
```

If the roadmap file is missing, stop and report blocker before structural changes.

---

## 2. Phase 1 Principles

### 2.1 One canonical task source

Phase 1 has one canonical task source:

```text
docs/milestones/M1.md
```

This file owns:

- task scope
- acceptance criteria
- allowed paths
- forbidden paths
- required evidence
- lifecycle status
- task revision

GitHub Issues, Multica Issues, GitLab Issues, comments, and chat summaries are not canonical in Phase 1.

### 2.2 Evidence over confidence

A task is not accepted because an AI says it is complete.

A task is accepted only when Bridge computes acceptance from structured evidence:

```text
task contract
+ path policy result
+ verifier evidence
+ reviewer evidence
+ functional test evidence if required
+ blocker state
+ closeout state
```

### 2.3 Bridge is not an agent runner

Phase 1 Bridge does **not**:

- call Codex
- call DeepSeek
- call any model API
- create GitHub Issues
- create Multica Issues
- create GitLab Issues
- run autonomous loops
- merge code
- push branches
- modify branch protection
- execute production workflows

Bridge only validates local files and git state.

### 2.4 No `done` status

Do not use `done` as an acceptance state.

Valid gate results are:

```text
accepted
failed
inconclusive
```

---

## 3. Non-Goals

Do not build these in Phase 1:

- Multica integration
- GitHub Issue as canonical task source
- GitHub Issue sync
- GitLab integration
- dashboard
- automatic merge
- automatic PR creation
- automatic long-running agent loop
- worker metrics routing
- bidirectional sync
- production secret handling
- VPN or internal network automation
- direct model API integration inside Bridge
- secret scanning platform
- deployment automation
- runtime agent scheduler

If an implementation task appears to require any of these, stop and report blocker.

---

## 4. Target Repository Shape

Create or extend the minimal governance structure:

```text
AGENTS.md

chatgpt-pro-agent-workflow-roadmap.md
phase-1-development-plan.md

docs/
  agent/
    task-contract.md
    evidence-and-gates.md
    execution-modes.md
    security-boundaries.md

  milestones/
    _template.md
    M1.md

    evidence/
      <task_id>/
        verifier.yaml
        reviewer.yaml
        functional-test.yaml
        blockers.yaml
        path-policy.yaml
        gate-report.yaml

    closeout/
      M1.md

tools/
  agent-bridge/
    README.md
    agent-bridge
    agent_bridge.py
    tests/
      fixtures/
```

If the repo already has equivalent files, extend existing files instead of duplicating.

If `AGENTS.md` is absent, create a short root `AGENTS.md` that points to the roadmap, active phase plan, active milestone, and `docs/agent/*`.

If `AGENTS.md` exists, keep it short and operational. Do not duplicate the full phase plan inside root `AGENTS.md`.

---

## 5. Canonical Ownership and State

### 5.1 Ownership table

| Information type | Phase 1 source of truth |
|---|---|
| Task scope | `docs/milestones/M1.md` |
| Acceptance criteria | `docs/milestones/M1.md` |
| Allowed / forbidden paths | `docs/milestones/M1.md` |
| Lifecycle status | `docs/milestones/M1.md` |
| Verifier evidence | `docs/milestones/evidence/<task_id>/verifier.yaml` |
| Reviewer evidence | `docs/milestones/evidence/<task_id>/reviewer.yaml` |
| Functional test evidence | `docs/milestones/evidence/<task_id>/functional-test.yaml` |
| Blockers | `docs/milestones/evidence/<task_id>/blockers.yaml` |
| Path policy result | `docs/milestones/evidence/<task_id>/path-policy.yaml` |
| Gate report | `docs/milestones/evidence/<task_id>/gate-report.yaml` |
| Closeout | `docs/milestones/closeout/M1.md` |
| Code diff | local git |
| Final acceptance | Bridge gate result |

### 5.2 Lifecycle status vs gate status

Task contract may contain:

```yaml
lifecycle_status: ready
```

Valid lifecycle statuses:

```text
proposed
ready
in_progress
blocked
reviewing
verifying
closed
```

Bridge computes gate status. Gate status is not manually authored as task scope.

Valid gate statuses:

```text
accepted
failed
inconclusive
```

Do not manually mark a task as accepted inside the task contract.

### 5.3 Stable task ID

Every task must have a stable `task_id`.

Example:

```text
M1-T01
M1-T02
M1-T03
```

Do not use GitHub issue numbers, Multica issue IDs, GitLab issue IDs, or chat message IDs as primary task IDs.

---

## 6. Task Contract Format

Tasks are written inside `docs/milestones/M1.md`.

Each task must use a fenced YAML block with this exact info string:

```text
yaml task-contract
```

Example:

```yaml task-contract
schema_version: 1
task_id: M1-T01
title: Repository scan and file plan
canonical_owner: repo-doc
revision: 1
mode: direct
risk: low
lifecycle_status: ready

allowed_paths:
  - AGENTS.md
  - docs/**
  - tools/agent-bridge/**

forbidden_paths:
  - .env
  - .env.*
  - secrets/**
  - infra/prod/**

managed_artifact_paths:
  - docs/milestones/evidence/M1-T01/**
  - docs/milestones/closeout/**

acceptance:
  - Existing governance files are inspected before edits.
  - The final file plan lists create/modify decisions.
  - No duplicate governance files are created.

required_evidence:
  verifier: not_applicable
  reviewer: required
  functional_test: not_applicable

backend_refs:
  github_issue: null
  gitlab_issue: null
  multica_issue: null
  pr: null
  branch: null
  commit: null

stop_conditions:
  - roadmap file is missing
  - existing governance files conflict with Phase 1 ownership rules
  - implementation requires a Phase 1 non-goal
```

### 6.1 Required fields

Every task contract must include:

```text
schema_version
task_id
title
canonical_owner
revision
mode
risk
lifecycle_status
allowed_paths
forbidden_paths
managed_artifact_paths
acceptance
required_evidence
backend_refs
stop_conditions
```

### 6.2 Valid enum values

```yaml
canonical_owner:
  - repo-doc

mode:
  - direct
  - subagent
  - borderline

risk:
  - low
  - medium
  - high

lifecycle_status:
  - proposed
  - ready
  - in_progress
  - blocked
  - reviewing
  - verifying
  - closed

required_evidence:
  verifier:
    - required
    - not_applicable
  reviewer:
    - required
    - not_applicable
  functional_test:
    - required
    - not_applicable
```

Phase 1 should avoid `conditional` evidence. If the need for evidence is unclear, the task should remain `proposed` or `blocked` until clarified.

### 6.3 Path policy semantics

All paths are repo-relative POSIX-style paths.

Rules:

1. `forbidden_paths` override `allowed_paths`.
2. `managed_artifact_paths` are allowed only for Bridge-generated evidence and closeout artifacts.
3. Empty `allowed_paths` means no implementation file changes are allowed.
4. To allow all paths, write `**` explicitly.
5. Any file outside `allowed_paths` fails unless explicitly allowed.
6. Rename operations must check both old path and new path.
7. Delete operations must check the deleted path.
8. Worktree mode must include untracked files.
9. Path checks must be deterministic and explain violations.

---

## 7. Roles

Use the smallest role set in Phase 1.

| Role | Tool | Responsibility | May modify code? |
|---|---|---|---|
| Orchestrator | main Codex session | Plan, dispatch, run Bridge, summarize result | Only when acting as Builder |
| Builder | Codex | Implement changes within allowed paths | Yes |
| Test Builder | Codex | Add or update tests within allowed paths | Yes, tests only unless task allows otherwise |
| Verifier | Codex or local shell session | Run commands and record evidence | No |
| Reviewer-B | DeepSeek V4 Pro or equivalent external reviewer | Adversarial review/spec critique | No |
| Functional Tester | Codex, DeepSeek, or manual black-box process | Validate user-observable behavior | No source changes |

### 7.1 Hard role boundaries

- Builder may change only files allowed by the task contract.
- Test Builder may add or update tests only within allowed paths.
- Verifier must not change code.
- Reviewer must not change code.
- Functional Tester should avoid reading implementation details when black-box testing is possible.
- Orchestrator cannot override hard gate rules.
- Bridge computes acceptance from evidence.

### 7.2 DeepSeek usage boundary

DeepSeek V4 Pro may be used as an external reviewer/spec critic.

In Phase 1:

```text
DeepSeek evidence is generated outside Bridge.
Bridge only reads reviewer.yaml.
Bridge does not call DeepSeek API.
```

---

## 8. Evidence Storage

Structured evidence is stored under:

```text
docs/milestones/evidence/<task_id>/
```

Recommended files:

```text
verifier.yaml
reviewer.yaml
functional-test.yaml
blockers.yaml
path-policy.yaml
gate-report.yaml
```

Raw logs are optional and are not required for Phase 1.

If raw logs are kept, store them outside version-controlled docs by default:

```text
.agent/runs/<task_id>/
```

Raw logs should not be required for acceptance unless the task contract explicitly requires them.

Chat summaries do not count as evidence.

---

## 9. Evidence Schemas

All evidence files should include:

```yaml
schema_version: 1
task_id: M1-T01
```

### 9.1 Verifier evidence

File:

```text
docs/milestones/evidence/<task_id>/verifier.yaml
```

Schema:

```yaml
schema_version: 1
verifier:
  task_id: M1-T01
  branch: ""
  base_sha: ""
  head_sha: ""
  commit: ""

  environment:
    os: ""
    runtime: ""
    package_manager: ""

  commands:
    - command: ""
      exit_code: 0
      started_at: ""
      duration_sec: 0
      stdout_excerpt: ""
      stderr_excerpt: ""

  git_status_before: clean
  git_status_after: clean

  conclusion: pass
```

Valid conclusions:

```text
pass
fail
inconclusive
```

Hard rules:

- Command not run means `inconclusive`.
- Missing command evidence means invalid verifier evidence.
- Exit code non-zero means `failed`.
- Verifier-created code diff invalidates evidence.
- `"Tests passed"` without command and exit code is invalid.
- Final acceptance should prefer evidence with `base_sha` and `head_sha`.

### 9.2 Reviewer evidence

File:

```text
docs/milestones/evidence/<task_id>/reviewer.yaml
```

Schema:

```yaml
schema_version: 1
reviewer:
  task_id: M1-T01
  reviewer: deepseek-v4-pro
  base_sha: ""
  head_sha: ""

  checklist:
    scope_match: pass
    forbidden_paths: pass
    tests_added_or_updated: pass
    security_risk: pass
    backward_compatibility: pass
    error_handling: pass
    observability: not_applicable

  findings:
    - severity: P2
      status: open
      file: ""
      line: ""
      issue: ""
      required_action: ""
      resolution_ref: null

  conclusion: pass
```

Valid checklist values:

```text
pass
fail
unknown
not_applicable
```

Valid finding severities:

```text
P0
P1
P2
P3
```

Valid finding statuses:

```text
open
resolved
waived
```

Phase 1 waiver rule:

```text
P0/P1 findings cannot be waived.
P0/P1 must be resolved or the gate fails.
P2/P3 may remain open only if recorded as known risk or follow-up.
```

Hard rules:

- Open P0 means `failed`.
- Open P1 means `failed`.
- Reviewer pass cannot override verifier failure.
- Generic advice without file, line, and risk does not count as a blocking finding.
- Reviewer evidence must include `base_sha` and `head_sha` for medium/high risk tasks.

### 9.3 Functional test evidence

File:

```text
docs/milestones/evidence/<task_id>/functional-test.yaml
```

Schema:

```yaml
schema_version: 1
functional_test:
  task_id: M1-T01
  level: FT-L4
  entrypoint: ""
  scenario: ""
  steps:
    - ""
  expected: ""
  observed: ""
  result: ""
  artifacts: []
  conclusion: not_applicable
```

Valid levels:

```text
FT-L0 true black-box
FT-L1 interface black-box
FT-L2 gray-box
FT-L3 independent spec review
FT-L4 not applicable
```

Valid conclusions:

```text
pass
fail
inconclusive
not_applicable
```

Hard rules:

- If functional test is required and missing, gate is `inconclusive`.
- If functional test is required and failed, gate is `failed`.
- If functional test is not applicable, evidence may be absent or marked FT-L4.
- Functional Tester should not rely on Builder’s self-summary as evidence.

### 9.4 Blocker evidence

File:

```text
docs/milestones/evidence/<task_id>/blockers.yaml
```

Schema:

```yaml
schema_version: 1
task_id: M1-T01
blockers:
  - id: B1
    severity: P1
    status: open
    source: verifier
    description: ""
    required_action: ""
    resolution_ref: null
```

Valid blocker statuses:

```text
open
resolved
```

Rules:

- Open P0 blocker means `failed`.
- Open P1 blocker means `failed`.
- Open P2/P3 blocker means `inconclusive`.
- Resolved blockers do not block acceptance.

### 9.5 Path policy evidence

File:

```text
docs/milestones/evidence/<task_id>/path-policy.yaml
```

Schema:

```yaml
schema_version: 1
path_policy:
  task_id: M1-T01
  mode: base_head
  base_sha: ""
  head_sha: ""
  result: pass
  changed_files:
    - path: ""
      status: modified
  violations:
    - code: forbidden_path_changed
      path: ""
      reason: ""
```

Valid modes:

```text
base_head
worktree
```

Valid results:

```text
pass
fail
inconclusive
```

---

## 10. Bridge Implementation Boundary

Bridge is a local CLI tool.

Default implementation:

```text
Use the repository's dominant language if obvious.
If not obvious, implement as Python 3 under tools/agent-bridge/.
Prefer small dependencies.
If YAML parsing is required, use PyYAML and document it.
Do not introduce heavy frameworks.
```

Recommended files:

```text
tools/agent-bridge/
  README.md
  agent-bridge
  agent_bridge.py
  tests/
    test_validate.py
    test_diff_check.py
    test_gate.py
    test_closeout.py
    fixtures/
```

The `agent-bridge` wrapper should call the implementation script.

Example:

```bash
tools/agent-bridge/agent-bridge validate docs/milestones/M1.md
```

Optional convenience:

```bash
agent-bridge validate docs/milestones/M1.md
```

only if PATH or project packaging supports it.

---

## 11. Bridge Commands

Required Phase 1 commands:

```bash
agent-bridge validate docs/milestones/M1.md
agent-bridge diff-check --task M1-T01 --base <base_sha> --head <head_sha>
agent-bridge diff-check --task M1-T01 --worktree
agent-bridge gate --task M1-T01
agent-bridge closeout --task M1-T01
agent-bridge closeout --milestone M1
```

### 11.1 Command write boundaries

| Command | Default writes files? | Notes |
|---|---:|---|
| `validate` | No | Read-only |
| `diff-check` | No | Read-only unless `--write-evidence` is added |
| `gate` | No | Read-only unless `--write-report` is added |
| `closeout --task` | Yes | Writes managed closeout block |
| `closeout --milestone` | Yes | Writes managed milestone closeout |
| model calls | No | Not allowed in Phase 1 |

### 11.2 Exit codes

| Result | Exit code |
|---|---:|
| valid / pass / accepted | 0 |
| invalid / failed | 1 |
| inconclusive | 2 |
| tool error | 3 |

Examples:

```text
validate invalid -> 1
diff-check fail -> 1
diff-check inconclusive -> 2
gate failed -> 1
gate inconclusive -> 2
```

### 11.3 Output formats

All commands should produce readable text by default.

All commands should support:

```bash
--json
```

JSON output should include:

```json
{
  "result": "failed",
  "reasons": [
    {
      "code": "forbidden_path_changed",
      "path": "infra/prod/deploy.yaml",
      "message": "Changed file is under forbidden_paths."
    }
  ]
}
```

---

## 12. Command Details

### 12.1 `validate`

Command:

```bash
agent-bridge validate docs/milestones/M1.md
```

Checks:

- milestone file exists
- fenced `yaml task-contract` blocks can be parsed
- each task has required fields
- each task has unique `task_id`
- `schema_version` is supported
- enum values are valid
- `canonical_owner` is `repo-doc`
- `revision` is positive integer
- `allowed_paths` is list
- `forbidden_paths` is list
- `managed_artifact_paths` is list
- `acceptance` is non-empty list
- `required_evidence` values are valid
- `backend_refs` exists
- no task uses `done` as status
- path strings are repo-relative
- no duplicate task IDs exist

Output:

```text
valid
invalid
list of missing or malformed fields
```

JSON output example:

```json
{
  "milestone": "M1",
  "result": "invalid",
  "tasks_checked": 6,
  "errors": [
    {
      "task_id": "M1-T03",
      "field": "acceptance",
      "code": "missing_required_field"
    }
  ]
}
```

Acceptance:

- detects missing task fields
- detects duplicate task IDs
- detects invalid enum values
- returns non-zero exit code on invalid milestone
- produces readable error output

---

### 12.2 `diff-check`

Commands:

```bash
agent-bridge diff-check --task M1-T01 --base <base_sha> --head <head_sha>
agent-bridge diff-check --task M1-T01 --worktree
```

Inputs:

```text
task_id
task path policy
git changed files
base/head or worktree state
```

Rules:

- `--base/--head` is preferred for final gate evidence.
- `--worktree` is for local in-progress checks.
- Any changed file under `forbidden_paths` fails.
- Any changed file outside `allowed_paths` fails unless explicitly allowed.
- `managed_artifact_paths` are allowed only for evidence/closeout artifacts.
- If git state cannot be read, result is `inconclusive`.
- Worktree mode must include untracked files.
- Rename checks must include old path and new path.
- Delete checks must include deleted path.

Optional write:

```bash
agent-bridge diff-check --task M1-T01 --base <base_sha> --head <head_sha> --write-evidence
```

Writes:

```text
docs/milestones/evidence/M1-T01/path-policy.yaml
```

Output:

```text
pass
fail
inconclusive
changed files
violations
```

JSON output example:

```json
{
  "task_id": "M1-T01",
  "result": "fail",
  "changed_files": [
    {
      "path": "infra/prod/deploy.yaml",
      "status": "modified"
    }
  ],
  "violations": [
    {
      "code": "forbidden_path_changed",
      "path": "infra/prod/deploy.yaml"
    }
  ]
}
```

Acceptance:

- reads changed files from git
- supports base/head mode
- supports worktree mode
- includes untracked files in worktree mode
- checks allowed paths
- checks forbidden paths
- fails on forbidden path changes
- returns inconclusive if git state is unavailable

---

### 12.3 `gate`

Command:

```bash
agent-bridge gate --task M1-T01
```

Optional:

```bash
agent-bridge gate --task M1-T01 --write-report
agent-bridge gate --task M1-T01 --json
```

Inputs:

```text
task contract
path-policy evidence or live diff-check result
verifier evidence
reviewer evidence
functional test evidence
blocker evidence
closeout state
```

Gate has two layers:

```text
evidence_gate
final_gate
```

### Evidence gate

Evidence gate checks:

- task contract is valid
- path policy passed
- required verifier evidence exists
- verifier commands exist
- verifier command exit codes are zero
- verifier did not create code diff
- required reviewer evidence exists
- reviewer has no open P0/P1 findings
- required functional test evidence exists
- functional test did not fail
- no open blocking P0/P1 blocker exists

Evidence gate results:

```text
pass
fail
inconclusive
```

### Final gate

Final gate checks:

```text
evidence_gate
+ closeout presence
```

Final gate results:

```text
accepted
failed
inconclusive
```

Rules:

- If evidence gate fails, final gate is `failed`.
- If evidence gate is inconclusive, final gate is `inconclusive`.
- If evidence gate passes but closeout is missing, final gate is `inconclusive`.
- If evidence gate passes and closeout exists, final gate is `accepted`.

Hard gate rules:

- Missing verifier evidence when required means `inconclusive`.
- Verifier command missing means `inconclusive`.
- Verifier exit code non-zero means `failed`.
- Missing reviewer evidence when required means `inconclusive`.
- Open P0/P1 reviewer finding means `failed`.
- Functional test failed means `failed`.
- Functional test missing when required means `inconclusive`.
- Forbidden path violation means `failed`.
- Open P0/P1 blocker means `failed`.
- Open P2/P3 blocker means `inconclusive`.
- Closeout missing means final gate `inconclusive`.

Output example:

```yaml
task_id: M1-T01
evidence_gate: pass
closeout_present: false
final_gate: inconclusive
reasons:
  - code: closeout_missing
    message: Evidence passed, but closeout block is missing.
```

JSON output example:

```json
{
  "task_id": "M1-T01",
  "evidence_gate": "pass",
  "closeout_present": false,
  "final_gate": "inconclusive",
  "reasons": [
    {
      "code": "closeout_missing",
      "message": "Evidence passed, but closeout block is missing."
    }
  ]
}
```

Acceptance:

- reads task contract
- reads structured evidence files
- applies hard gate rules
- produces `accepted`, `failed`, or `inconclusive`
- includes reason list
- does not use model confidence as evidence

---

### 12.4 `closeout`

Commands:

```bash
agent-bridge closeout --task M1-T01
agent-bridge closeout --milestone M1
```

Writes:

```text
docs/milestones/closeout/M1.md
```

Closeout must use managed blocks:

```md
<!-- agent-bridge:closeout:start M1-T01 -->
...
<!-- agent-bridge:closeout:end M1-T01 -->
```

Manual notes outside managed blocks must be preserved.

Minimum task closeout fields:

```yaml
task_id:
final_gate:
evidence_gate:
commit:
base_sha:
head_sha:
changed_files:
verifier_summary:
reviewer_summary:
functional_test_summary:
known_risks:
followups:
generated_at:
```

Rules:

- Closeout must not mark failed tasks as accepted.
- Closeout must not mark inconclusive tasks as accepted.
- Closeout should include known P2/P3 risks.
- Closeout should include follow-ups.
- Closeout must be idempotent.
- Re-running closeout should update only managed blocks.

Acceptance:

- produces structured closeout output
- preserves manual notes outside managed blocks
- does not mark failed/inconclusive tasks as accepted
- includes evidence summaries
- includes known risks and follow-ups
- rerun is idempotent

---

## 13. Security Boundaries

Phase 1 is local-only, but the governance docs must define safe defaults.

Minimum rules:

- Agents must not use production credentials.
- Agents must not access production systems.
- Agents must not inherit personal SSH, cloud, kube, or database credentials.
- Reviewer and Verifier should run read-only where possible.
- Functional Test should use local, staging, or sandbox resources.
- High-value secrets must not be placed in evidence files.
- Evidence files must not include raw secrets.
- `.env`, `.env.*`, `secrets/**`, and production infra paths should be forbidden by default.
- If a task requires VPN or internal network access, stop and report blocker in Phase 1.

Default forbidden paths:

```yaml
forbidden_paths:
  - .env
  - .env.*
  - secrets/**
  - infra/prod/**
```

---

## 14. Execution Modes

Phase 1 supports three modes at the task contract level.

### Direct Mode

Use when:

- task is small
- risk is low
- allowed paths are narrow
- acceptance is clear
- no cross-boundary coordination is required

### Subagent Mode

Use when:

- task requires isolated verifier/reviewer/test role
- risk is medium/high
- implementation and validation should be separated
- Functional Test is required

In Phase 1, Subagent Mode means role separation by prompt/session. It does not require a platform.

### Borderline Mode

Use when:

- scope is unclear
- path boundary is uncertain
- required evidence is unclear
- risk may be high but not yet assessed

Borderline tasks should not start implementation until clarified.

---

## 15. Implementation Order

### Step 1: Repository scan and file plan

Goal:

Inspect existing repo structure before creating files.

Actions:

- read `AGENTS.md` if present
- read `chatgpt-pro-agent-workflow-roadmap.md`
- inspect `docs/`
- inspect `tools/`
- identify existing governance files
- produce concrete create/modify plan

Acceptance:

- file plan lists each file to create or modify
- equivalent files are extended, not duplicated
- blocker is reported if roadmap is missing
- no edits are made before scan is complete unless repo is empty and obvious

---

### Step 2: Add governance docs

Create or update:

```text
AGENTS.md
docs/agent/task-contract.md
docs/agent/evidence-and-gates.md
docs/agent/execution-modes.md
docs/agent/security-boundaries.md
docs/milestones/_template.md
```

Acceptance:

- docs are short and operational
- no platform-specific assumptions leak into task contract
- task contract format is machine-parseable
- evidence and gate rules are clear
- new session can understand accepted vs failed vs inconclusive

---

### Step 3: Create M1 milestone

Create:

```text
docs/milestones/M1.md
```

Include:

- scope
- non-goals
- execution assumptions
- task list
- task contracts
- risk table
- evidence storage pointer
- closeout pointer

Acceptance:

- at least 8 executable Phase 1 tasks exist
- each task has stable `task_id`
- each task uses fenced `yaml task-contract`
- each task declares allowed paths
- each task declares forbidden paths
- each task declares required evidence
- at least one task is low-risk Direct Mode
- at least one task requires reviewer evidence
- at least one task exercises failure scenario validation
- Functional Test is marked required or not_applicable explicitly

---

### Step 4: Implement Bridge CLI skeleton and parser

Create:

```text
tools/agent-bridge/README.md
tools/agent-bridge/agent-bridge
tools/agent-bridge/agent_bridge.py
```

Acceptance:

- executable entrypoint exists
- CLI has subcommands:
  - validate
  - diff-check
  - gate
  - closeout
- parser extracts fenced `yaml task-contract` blocks
- malformed YAML produces readable errors
- `--json` option exists or is stubbed with documented behavior
- no model API integration is added

---

### Step 5: Implement `validate`

Acceptance:

- detects missing required fields
- detects duplicate task IDs
- validates enum values
- validates evidence requirement values
- validates path list shape
- rejects `done` as status
- returns non-zero exit code on invalid milestone
- includes readable reason list

---

### Step 6: Implement `diff-check`

Acceptance:

- supports `--base` and `--head`
- supports `--worktree`
- reads changed files from git
- includes untracked files in worktree mode
- checks `allowed_paths`
- checks `forbidden_paths`
- checks managed artifact paths
- forbidden paths override allowed paths
- rename/delete paths are handled
- result includes changed files and violations
- returns inconclusive if git state is unavailable

---

### Step 7: Implement evidence schema validation

Acceptance:

- verifier evidence requires command and exit code
- verifier evidence rejects commandless “tests passed”
- reviewer evidence requires conclusion
- reviewer findings support severity and status
- functional test evidence supports FT-L0 through FT-L4
- blocker evidence supports severity and status
- invalid evidence produces clear reason codes

---

### Step 8: Implement `gate`

Acceptance:

- reads task contract
- reads evidence files
- applies hard gate rules
- distinguishes evidence gate from final gate
- missing required verifier evidence returns inconclusive
- verifier non-zero exit code returns failed
- missing required reviewer evidence returns inconclusive
- open reviewer P0/P1 returns failed
- forbidden path violation returns failed
- missing closeout makes final gate inconclusive
- output includes machine-readable reason list

---

### Step 9: Implement `closeout`

Acceptance:

- writes managed closeout blocks
- supports task closeout
- supports milestone closeout
- does not mark failed or inconclusive tasks as accepted
- includes changed files, evidence summaries, known risks, followups
- is idempotent
- preserves manual notes outside managed blocks

---

### Step 10: Add minimal tests and fixtures

Create:

```text
tools/agent-bridge/tests/
  test_validate.py
  test_diff_check.py
  test_gate.py
  test_closeout.py
  fixtures/
    valid-milestone.md
    invalid-missing-fields.md
    invalid-duplicate-task-id.md
    evidence/
      verifier-pass.yaml
      verifier-fail.yaml
      reviewer-p1-open.yaml
      functional-test-pass.yaml
```

Acceptance:

- validate tests pass
- diff-check path policy tests pass
- gate failure tests pass
- closeout idempotency test passes
- test command is documented in `tools/agent-bridge/README.md`

---

### Step 11: Run failure scenarios

Create or simulate at least four failures:

1. forbidden path changed
2. verifier command failed
3. reviewer P1 finding unresolved
4. required evidence missing

Acceptance:

- gate blocks forbidden path change
- gate blocks verifier command failure
- gate blocks open reviewer P1
- gate returns inconclusive on missing evidence
- report shows exact reason codes

---

### Step 12: Dogfood Phase 1 acceptance

Run Bridge against M1 itself.

Acceptance:

- `validate docs/milestones/M1.md` passes
- at least one task reaches final gate `accepted`
- at least three failure cases are blocked
- closeout lets a new session resume without chat history
- no Phase 1 non-goals were implemented

---

## 16. Phase 1 Task Breakdown

The following tasks should be placed into `docs/milestones/M1.md`.

---

### M1-T01: Repository scan and file plan

```yaml task-contract
schema_version: 1
task_id: M1-T01
title: Repository scan and file plan
canonical_owner: repo-doc
revision: 1
mode: direct
risk: low
lifecycle_status: ready

allowed_paths:
  - AGENTS.md
  - docs/**
  - tools/agent-bridge/**

forbidden_paths:
  - .env
  - .env.*
  - secrets/**
  - infra/prod/**

managed_artifact_paths:
  - docs/milestones/evidence/M1-T01/**
  - docs/milestones/closeout/**

acceptance:
  - Existing AGENTS.md and docs layout are inspected before edits.
  - Final file plan lists create/modify decisions.
  - Equivalent governance files are extended instead of duplicated.
  - Roadmap file presence is checked.

required_evidence:
  verifier: not_applicable
  reviewer: required
  functional_test: not_applicable

backend_refs:
  github_issue: null
  gitlab_issue: null
  multica_issue: null
  pr: null
  branch: null
  commit: null

stop_conditions:
  - roadmap file is missing
  - existing governance files conflict with Phase 1 ownership rules
```

---

### M1-T02: Governance docs baseline

```yaml task-contract
schema_version: 1
task_id: M1-T02
title: Governance docs baseline
canonical_owner: repo-doc
revision: 1
mode: direct
risk: low
lifecycle_status: ready

allowed_paths:
  - AGENTS.md
  - docs/agent/**
  - docs/milestones/_template.md

forbidden_paths:
  - tools/agent-bridge/**
  - .env
  - .env.*
  - secrets/**
  - infra/prod/**

managed_artifact_paths:
  - docs/milestones/evidence/M1-T02/**
  - docs/milestones/closeout/**

acceptance:
  - task-contract.md defines machine-parseable task contract format.
  - evidence-and-gates.md defines evidence schemas and hard gate rules.
  - execution-modes.md defines Direct/Subagent/Borderline criteria.
  - security-boundaries.md defines local, VPN, and secret boundaries.
  - _template.md contains a valid task contract example.
  - AGENTS.md points to governance docs without becoming long.

required_evidence:
  verifier: not_applicable
  reviewer: required
  functional_test: not_applicable

backend_refs:
  github_issue: null
  gitlab_issue: null
  multica_issue: null
  pr: null
  branch: null
  commit: null

stop_conditions:
  - governance docs require platform integration
  - task contract becomes platform-specific
```

---

### M1-T03: M1 milestone as canonical task source

```yaml task-contract
schema_version: 1
task_id: M1-T03
title: Create M1 milestone as canonical task source
canonical_owner: repo-doc
revision: 1
mode: direct
risk: low
lifecycle_status: ready

allowed_paths:
  - docs/milestones/M1.md
  - docs/milestones/evidence/**
  - docs/milestones/closeout/**

forbidden_paths:
  - tools/agent-bridge/**
  - docs/agent/**
  - .env
  - .env.*
  - secrets/**
  - infra/prod/**

managed_artifact_paths:
  - docs/milestones/evidence/M1-T03/**
  - docs/milestones/closeout/**

acceptance:
  - M1.md contains scope, non-goals, task list, risks, and closeout pointer.
  - At least 8 executable Phase 1 tasks exist.
  - Every task uses stable task_id.
  - Every task declares allowed_paths and forbidden_paths.
  - Every task declares required_evidence.
  - Task contracts use fenced yaml task-contract blocks.

required_evidence:
  verifier: not_applicable
  reviewer: required
  functional_test: not_applicable

backend_refs:
  github_issue: null
  gitlab_issue: null
  multica_issue: null
  pr: null
  branch: null
  commit: null

stop_conditions:
  - M1 requires external platform state
  - tasks cannot be expressed as repo-doc canonical contracts
```

---

### M1-T04: Bridge CLI skeleton and parser

```yaml task-contract
schema_version: 1
task_id: M1-T04
title: Implement agent-bridge CLI skeleton and milestone parser
canonical_owner: repo-doc
revision: 1
mode: direct
risk: medium
lifecycle_status: ready

allowed_paths:
  - tools/agent-bridge/**
  - docs/milestones/evidence/M1-T04/**

forbidden_paths:
  - docs/agent/**
  - docs/milestones/M1.md
  - .env
  - .env.*
  - secrets/**
  - infra/prod/**

managed_artifact_paths:
  - docs/milestones/evidence/M1-T04/**
  - docs/milestones/closeout/**

acceptance:
  - agent-bridge executable exists.
  - CLI supports validate, diff-check, gate, closeout subcommands.
  - Parser extracts fenced yaml task-contract blocks from milestone docs.
  - Parser returns useful errors for malformed YAML.
  - Commands support --json or document stable structured output.
  - No model API integration is added.

required_evidence:
  verifier: required
  reviewer: required
  functional_test: not_applicable

backend_refs:
  github_issue: null
  gitlab_issue: null
  multica_issue: null
  pr: null
  branch: null
  commit: null

stop_conditions:
  - implementation requires external platform integration
  - implementation requires model API keys
```

---

### M1-T05: Validate command

```yaml task-contract
schema_version: 1
task_id: M1-T05
title: Implement validate command
canonical_owner: repo-doc
revision: 1
mode: direct
risk: medium
lifecycle_status: ready

allowed_paths:
  - tools/agent-bridge/**
  - docs/milestones/evidence/M1-T05/**

forbidden_paths:
  - docs/agent/**
  - docs/milestones/M1.md
  - .env
  - .env.*
  - secrets/**
  - infra/prod/**

managed_artifact_paths:
  - docs/milestones/evidence/M1-T05/**
  - docs/milestones/closeout/**

acceptance:
  - validate detects missing required fields.
  - validate detects duplicate task IDs.
  - validate validates enum values.
  - validate validates required_evidence values.
  - validate rejects unsupported schema_version.
  - validate returns non-zero exit code on invalid input.
  - test fixtures cover valid and invalid milestones.

required_evidence:
  verifier: required
  reviewer: required
  functional_test: not_applicable

backend_refs:
  github_issue: null
  gitlab_issue: null
  multica_issue: null
  pr: null
  branch: null
  commit: null

stop_conditions:
  - validation requires non-local state
```

---

### M1-T06: Diff-check command

```yaml task-contract
schema_version: 1
task_id: M1-T06
title: Implement diff-check command
canonical_owner: repo-doc
revision: 1
mode: direct
risk: medium
lifecycle_status: ready

allowed_paths:
  - tools/agent-bridge/**
  - docs/milestones/evidence/M1-T06/**

forbidden_paths:
  - docs/agent/**
  - docs/milestones/M1.md
  - .env
  - .env.*
  - secrets/**
  - infra/prod/**

managed_artifact_paths:
  - docs/milestones/evidence/M1-T06/**
  - docs/milestones/closeout/**

acceptance:
  - diff-check supports --base and --head.
  - diff-check supports --worktree.
  - forbidden_paths override allowed_paths.
  - files outside allowed_paths fail unless explicitly allowed.
  - untracked files are included in worktree mode.
  - rename and delete paths are handled.
  - managed evidence paths do not create false failures.
  - output includes changed files and violations.

required_evidence:
  verifier: required
  reviewer: required
  functional_test: not_applicable

backend_refs:
  github_issue: null
  gitlab_issue: null
  multica_issue: null
  pr: null
  branch: null
  commit: null

stop_conditions:
  - git state is unavailable and no fallback can be reported
```

---

### M1-T07: Evidence schema validation

```yaml task-contract
schema_version: 1
task_id: M1-T07
title: Implement evidence schema validation
canonical_owner: repo-doc
revision: 1
mode: direct
risk: medium
lifecycle_status: ready

allowed_paths:
  - tools/agent-bridge/**
  - docs/milestones/evidence/M1-T07/**

forbidden_paths:
  - docs/agent/**
  - docs/milestones/M1.md
  - .env
  - .env.*
  - secrets/**
  - infra/prod/**

managed_artifact_paths:
  - docs/milestones/evidence/M1-T07/**
  - docs/milestones/closeout/**

acceptance:
  - verifier evidence requires command and exit_code.
  - reviewer evidence requires base/head, checklist, findings, and conclusion.
  - functional test evidence supports FT-L0 to FT-L4.
  - blocker evidence supports severity and status.
  - reviewer P0/P1 finding requires status.
  - invalid evidence produces clear reason codes.

required_evidence:
  verifier: required
  reviewer: required
  functional_test: not_applicable

backend_refs:
  github_issue: null
  gitlab_issue: null
  multica_issue: null
  pr: null
  branch: null
  commit: null

stop_conditions:
  - schema validation requires external service
```

---

### M1-T08: Gate command

```yaml task-contract
schema_version: 1
task_id: M1-T08
title: Implement gate command
canonical_owner: repo-doc
revision: 1
mode: direct
risk: medium
lifecycle_status: ready

allowed_paths:
  - tools/agent-bridge/**
  - docs/milestones/evidence/M1-T08/**

forbidden_paths:
  - docs/agent/**
  - docs/milestones/M1.md
  - .env
  - .env.*
  - secrets/**
  - infra/prod/**

managed_artifact_paths:
  - docs/milestones/evidence/M1-T08/**
  - docs/milestones/closeout/**

acceptance:
  - gate returns accepted, failed, or inconclusive.
  - gate distinguishes evidence_gate from final_gate.
  - missing required verifier evidence returns inconclusive.
  - verifier exit_code non-zero returns failed.
  - missing required reviewer evidence returns inconclusive.
  - open P0/P1 reviewer finding returns failed.
  - forbidden path violation returns failed.
  - missing required functional test returns inconclusive.
  - missing closeout returns final_gate inconclusive.
  - output includes machine-readable reason list.

required_evidence:
  verifier: required
  reviewer: required
  functional_test: not_applicable

backend_refs:
  github_issue: null
  gitlab_issue: null
  multica_issue: null
  pr: null
  branch: null
  commit: null

stop_conditions:
  - gate requires model confidence
  - gate needs external platform state
```

---

### M1-T09: Closeout command

```yaml task-contract
schema_version: 1
task_id: M1-T09
title: Implement closeout command
canonical_owner: repo-doc
revision: 1
mode: direct
risk: medium
lifecycle_status: ready

allowed_paths:
  - tools/agent-bridge/**
  - docs/milestones/closeout/**
  - docs/milestones/evidence/M1-T09/**

forbidden_paths:
  - docs/agent/**
  - docs/milestones/M1.md
  - .env
  - .env.*
  - secrets/**
  - infra/prod/**

managed_artifact_paths:
  - docs/milestones/evidence/M1-T09/**
  - docs/milestones/closeout/**

acceptance:
  - closeout writes managed closeout blocks.
  - closeout does not mark failed or inconclusive tasks as accepted.
  - closeout includes changed files, evidence summaries, known risks, and followups.
  - closeout is idempotent when rerun.
  - closeout preserves manual notes outside managed blocks.

required_evidence:
  verifier: required
  reviewer: required
  functional_test: not_applicable

backend_refs:
  github_issue: null
  gitlab_issue: null
  multica_issue: null
  pr: null
  branch: null
  commit: null

stop_conditions:
  - closeout requires rewriting canonical task scope
```

---

### M1-T10: Bridge tests and fixtures

```yaml task-contract
schema_version: 1
task_id: M1-T10
title: Add Bridge tests and fixtures
canonical_owner: repo-doc
revision: 1
mode: direct
risk: medium
lifecycle_status: ready

allowed_paths:
  - tools/agent-bridge/**
  - docs/milestones/evidence/M1-T10/**

forbidden_paths:
  - docs/agent/**
  - docs/milestones/M1.md
  - .env
  - .env.*
  - secrets/**
  - infra/prod/**

managed_artifact_paths:
  - docs/milestones/evidence/M1-T10/**
  - docs/milestones/closeout/**

acceptance:
  - validate has valid and invalid milestone fixtures.
  - diff-check has allowed path and forbidden path tests.
  - gate has verifier failure and reviewer P1 failure tests.
  - gate has missing evidence inconclusive test.
  - closeout idempotency is tested or manually verified.
  - README documents how to run tests.

required_evidence:
  verifier: required
  reviewer: required
  functional_test: not_applicable

backend_refs:
  github_issue: null
  gitlab_issue: null
  multica_issue: null
  pr: null
  branch: null
  commit: null

stop_conditions:
  - tests require external platform
```

---

### M1-T11: Failure scenarios and dogfood acceptance

```yaml task-contract
schema_version: 1
task_id: M1-T11
title: Run failure scenarios and dogfood final acceptance
canonical_owner: repo-doc
revision: 1
mode: subagent
risk: medium
lifecycle_status: ready

allowed_paths:
  - tools/agent-bridge/**
  - docs/milestones/evidence/**
  - docs/milestones/closeout/**

forbidden_paths:
  - .env
  - .env.*
  - secrets/**
  - infra/prod/**

managed_artifact_paths:
  - docs/milestones/evidence/M1-T11/**
  - docs/milestones/closeout/**

acceptance:
  - forbidden path scenario is blocked.
  - verifier command failure is blocked.
  - open reviewer P1 finding is blocked.
  - missing evidence returns inconclusive.
  - at least one real Phase 1 task reaches accepted.
  - closeout allows a new session to resume without chat history.
  - no Phase 1 non-goals were implemented.

required_evidence:
  verifier: required
  reviewer: required
  functional_test: not_applicable

backend_refs:
  github_issue: null
  gitlab_issue: null
  multica_issue: null
  pr: null
  branch: null
  commit: null

stop_conditions:
  - dogfood requires external integration
  - failure scenarios cannot be represented locally
```

---

## 17. Final Phase 1 Acceptance

Phase 1 is complete only if:

- `chatgpt-pro-agent-workflow-roadmap.md` exists in repo
- `phase-1-development-plan.md` exists in repo
- root `AGENTS.md` exists or has been extended
- governance docs exist:
  - `docs/agent/task-contract.md`
  - `docs/agent/evidence-and-gates.md`
  - `docs/agent/execution-modes.md`
  - `docs/agent/security-boundaries.md`
- milestone template exists:
  - `docs/milestones/_template.md`
- M1 milestone exists:
  - `docs/milestones/M1.md`
- evidence directory convention exists
- closeout directory convention exists
- Bridge validate works
- Bridge diff-check works
- Bridge gate works
- Bridge closeout works
- task contracts are schema-checkable
- gate can return accepted / failed / inconclusive
- forbidden path changes are blocked
- verifier evidence requires actual commands and exit codes
- reviewer P0/P1 findings block acceptance
- missing required evidence returns inconclusive
- closeout is generated from evidence, not model confidence
- at least one task reaches final gate `accepted`
- at least three failure cases are blocked
- closeout lets a new session resume without chat history
- no Phase 1 non-goals are implemented

---

## 18. Recommended New Build Session Prompt

Use this prompt to start the implementation session.

```text
We are in /Users/yang/Coshare.

Read these files first if present:

- AGENTS.md
- chatgpt-pro-agent-workflow-roadmap.md
- phase-1-development-plan.md

Goal:

Implement Phase 1 of the agent workflow system.

Phase 1 is local governance baseline only.

Do not integrate:

- Multica
- GitHub Issues
- GitLab
- dashboards
- auto-merge
- model APIs
- autonomous long-running loops
- worker metrics routing
- bidirectional sync
- production secret handling
- VPN/internal network automation

Build only:

- docs/agent/*
- docs/milestones/_template.md
- docs/milestones/M1.md
- docs/milestones/evidence/
- docs/milestones/closeout/
- local tools/agent-bridge commands:
  - validate
  - diff-check
  - gate
  - closeout

Execution rule:

Follow SCAN -> PLAN -> EXECUTE.

Before edits:

1. Inspect the repo.
2. Identify existing governance files.
3. Present a concrete file plan.
4. Only stop for confirmation if:
   - existing files conflict with this plan,
   - destructive changes would be required,
   - roadmap file is missing,
   - or implementation would violate Phase 1 non-goals.

Acceptance:

- task contracts use fenced yaml task-contract blocks
- task contracts are schema-checkable
- evidence files have defined storage paths
- Bridge does not call Codex, DeepSeek, or any model API
- gate can return accepted / failed / inconclusive
- gate distinguishes evidence_gate from final_gate
- forbidden path changes are blocked
- verifier evidence requires actual commands and exit codes
- reviewer P0/P1 findings block acceptance
- missing required evidence returns inconclusive
- closeout is generated from evidence, not model confidence
- closeout is idempotent
- at least three failure cases are blocked
- final closeout lets a new session resume without chat history
```

---

## 19. Phase 1 Completion Report Format

At the end of Phase 1, produce:

```md
# Phase 1 Closeout

## Summary

## Files created

## Files modified

## Bridge commands implemented

## Evidence layout

## Accepted tasks

## Failed or inconclusive tasks

## Failure scenarios tested

## Known risks

## Follow-ups for Phase 2

## Explicit non-goals not implemented

## New session handoff
```

The handoff must be sufficient for a new session to continue without reading chat history.

---

## 20. Phase 2 Candidates

Do not implement these in Phase 1.

Potential Phase 2 items:

- GitHub Issue execution ticket export
- GitHub PR reference collection
- CI status evidence collection
- GitLab issue adapter
- Multica backend profile
- worker registry
- worker metrics
- structured task import/export
- richer functional test harness
- raw log retention policy
- secret scanning integration
- dashboard or board view

Any Phase 2 item discovered during Phase 1 should be recorded as follow-up, not implemented.
