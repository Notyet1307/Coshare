# Phase 2 Development Plan

Version: 0.1
Phase: Git-backed Execution Baseline
Canonical task source: repo milestone doc
Execution backend: local git
Platform integrations: none in Phase 2

---

## 0. Phase 2 Decision

Phase 2 builds a Git-backed execution baseline on top of the Phase 1 local governance baseline.

Phase 2 keeps milestone docs as the canonical task source.

Phase 2 does not make GitHub Issues, GitLab Issues, Multica Issues, comments, branch names, or chat summaries canonical task state.

Phase 2 adds a stricter bridge between:

- task contracts
- role prompt packs
- lane maps
- git base/head facts
- evidence files
- closeout records

The target outcome is simple:

```text
Given a task ID, a new session can understand the task, produce a role-specific prompt, initialize evidence files, verify git evidence consistency, and close out from repo facts.
```

---

## 1. Source Material

Read first:

- `AGENTS.md`
- `chatgpt-pro-agent-workflow-roadmap.md`
- `phase-1-development-plan.md`
- `docs/milestones/M1.md`
- `docs/milestones/closeout/M1.md`
- `docs/agent/*`
- `tools/agent-bridge/README.md`

Phase 1 is assumed complete and validated.

If Phase 1 closeout is missing or M1 gate is not accepted, stop before implementing Phase 2.

---

## 2. Phase 2 Scope

Phase 2 is a Git-backed Execution Baseline.

It may define and later implement:

- Git execution governance
- task role prompt packs
- lane map format
- Bridge `task-info`
- Bridge `evidence-init`
- Bridge `prompt-pack`
- stronger `base_sha` / `head_sha` evidence checks
- improved closeout from git and evidence facts
- a small dogfood task that creates real git evidence

Phase 2 does not implement external platform integrations.

---

## 3. Non-Goals

Do not implement in Phase 2:

- Multica integration
- GitHub Issue sync
- GitHub Issue as canonical task source
- GitLab integration
- dashboard
- auto-merge
- model API calls
- autonomous long-running loops
- worker metrics routing
- bidirectional sync
- production secret handling
- VPN/internal network automation

If a task appears to require any non-goal, stop and report a blocker.

---

## 4. Canonical Ownership

| Information type | Phase 2 source of truth |
|---|---|
| Task scope | `docs/milestones/M2.md` |
| Acceptance criteria | `docs/milestones/M2.md` |
| Allowed / forbidden paths | `docs/milestones/M2.md` |
| Lifecycle status | `docs/milestones/M2.md` |
| Role instructions | `docs/agent/role-prompt-packs.md` plus task contract |
| Lane ownership | `docs/agent/lane-map.md` plus task contract |
| Git execution rules | `docs/agent/git-execution.md` |
| Evidence | `docs/milestones/evidence/<task_id>/` |
| Closeout | `docs/milestones/closeout/M2.md` |
| Code facts | local git |
| Final acceptance | Bridge gate result |

Milestone docs remain canonical.

Git facts prove what changed.

Evidence files prove what was checked.

Closeout records summarize, but do not override, evidence.

---

## 5. Target Repository Shape

Phase 2 creates or extends:

```text
phase-2-development-plan.md

docs/
  agent/
    git-execution.md
    role-prompt-packs.md
    lane-map.md

  milestones/
    M2.md
    evidence/
      M2-Txx/
    closeout/
      M2.md

tools/
  agent-bridge/
    agent_bridge.py
    README.md
    tests/
```

The planning/docs part only creates:

- `phase-2-development-plan.md`
- `docs/milestones/M2.md`
- `docs/agent/git-execution.md`
- `docs/agent/role-prompt-packs.md`
- `docs/agent/lane-map.md`

Bridge code is implemented later.

---

## 6. Bridge Enhancements Planned

### 6.1 `task-info`

Reads the active milestone doc and prints machine-readable task details:

- task ID
- title
- lifecycle status
- mode
- risk
- allowed paths
- forbidden paths
- managed artifact paths
- required evidence
- backend refs
- stop conditions

It must not mutate files.

### 6.2 `evidence-init`

Creates evidence skeleton files for a task:

- `path-policy.yaml`
- `verifier.yaml` when required
- `reviewer.yaml` when required
- `functional-test.yaml` when required
- `blockers.yaml`

It may write skeletons only under the task managed evidence directory.

It must not mark evidence as passing.

### 6.3 `prompt-pack`

Generates role-specific prompts from the task contract and role prompt pack rules.

Supported roles:

- orchestrator
- builder
- test-builder
- verifier
- reviewer
- functional-tester
- closeout

It must not call model APIs.

### 6.4 Git evidence consistency checks

Bridge should reject stale or unverifiable git evidence.

Expected checks:

- `base_sha` exists
- `head_sha` exists
- `base_sha != head_sha` when changed files are claimed
- `changed_files` match `git diff --name-status base_sha head_sha`
- worktree evidence matches current dirty worktree
- evidence source mode is explicit
- evidence task ID matches its directory

Stale or mismatched evidence should be `inconclusive`.

Forbidden path violations should be `failed`.

### 6.5 Git-aware closeout

Closeout should include:

- task ID
- gate result
- base/head when available
- branch when available
- changed files
- evidence summary
- unresolved risks
- resume instructions

Closeout must preserve manual notes outside managed blocks.

---

## 7. M2 Milestone Tasks

Phase 2 is tracked in:

```text
docs/milestones/M2.md
```

Expected task sequence:

1. `M2-T01` Phase 2 plan/docs
2. `M2-T02` Git execution governance
3. `M2-T03` Role prompt packs
4. `M2-T04` Lane map
5. `M2-T05` Bridge `task-info`
6. `M2-T06` Bridge `evidence-init`
7. `M2-T07` Bridge `prompt-pack`
8. `M2-T08` Git evidence consistency checks
9. `M2-T09` Dogfood real small change
10. `M2-T10` Independent verification and closeout

---

## 8. Acceptance

Phase 2 is accepted when:

- `docs/milestones/M2.md` is valid.
- Phase 2 docs define git execution, prompt packs, and lane maps.
- Bridge can report task info from M2.
- Bridge can initialize evidence skeletons without false pass evidence.
- Bridge can generate role prompts without model calls.
- Bridge can detect stale git evidence.
- Bridge can detect changed file mismatch.
- Bridge can produce git-aware closeout.
- At least one small real dogfood change proves the flow.
- Independent verification confirms gate and closeout.

---

## 9. Compatibility Rule

Do not break Phase 1.

Bridge may keep `M1.md` as the default milestone for backward compatibility.

All Phase 2 commands must support an explicit milestone path, for example:

```bash
tools/agent-bridge/agent-bridge task-info --task M2-T05 --milestone docs/milestones/M2.md
```

Do not change M1 evidence or M1 closeout unless a task explicitly requires it.
