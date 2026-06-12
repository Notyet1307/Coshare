# Phase 4 Development Plan

Version: 0.1
Phase: GitHub Issue Execution Ticket Adapter
Canonical task source: repo milestone doc
Execution backend: local git plus GitHub Issue execution tickets
Default network behavior: offline / no network unless explicitly requested
Default remote write behavior: dry-run only

---

## 0. Phase 4 Decision

Phase 4 adds a GitHub Issue execution ticket adapter on top of the Phase 1, Phase 2, and Phase 3 baseline.

Milestone docs remain canonical.

GitHub Issues are execution tickets and mirrors only. They can help route work, show task summaries, and carry Bridge gate comments, but they do not own task scope, acceptance, lifecycle, or final gate state.

Phase 4 defaults to offline fixture mode and dry-run behavior.

No live GitHub write is allowed unless the user explicitly asks for it in a separate step.

---

## 1. Read First

- `AGENTS.md`
- `chatgpt-pro-agent-workflow-roadmap.md`
- `phase-1-development-plan.md`
- `phase-2-development-plan.md`
- `phase-3-development-plan.md`
- `docs/milestones/M1.md`
- `docs/milestones/M2.md`
- `docs/milestones/M3.md`
- `docs/milestones/closeout/M1.md`
- `docs/milestones/closeout/M2.md`
- `docs/milestones/closeout/M3.md`
- `docs/agent/*`
- `tools/agent-bridge/README.md`

If earlier milestone validation fails, stop before claiming Phase 4 acceptance.

---

## 2. Phase 4 Scope

Allowed:

- define GitHub Issue execution ticket rules
- generate an issue plan from milestone task contracts
- generate issue body text from canonical task contracts
- read issue status from offline fixture input
- optionally read issue status live through `gh`
- prepare managed gate-summary issue comments in dry-run mode
- write normalized issue evidence under `docs/milestones/evidence/<task_id>/`
- let Bridge gate consume issue evidence when required by a task
- let closeout include issue links and issue drift status

Forbidden:

- GitHub Issue as canonical task source
- issue-to-doc sync
- automatic issue creation by default
- live GitHub writes without explicit user request
- GitHub Projects integration
- GitLab integration
- Multica integration
- dashboard
- auto-merge
- automatic PR creation
- push automation
- model API calls inside Bridge
- autonomous long-running loops
- worker metrics routing
- bidirectional sync
- production secret handling
- storing GitHub tokens in repo files
- VPN/internal network automation

---

## 3. Canonical Ownership

| Information type | Phase 4 source of truth |
|---|---|
| Task ID | active milestone doc |
| Task scope | active milestone doc |
| Acceptance criteria | active milestone doc |
| Allowed / forbidden paths | active milestone doc |
| Lifecycle status | active milestone doc |
| Issue execution ticket rules | `docs/agent/github-issue-adapter.md` |
| Issue sync rules | `docs/agent/issue-sync-rules.md` |
| GitHub token boundaries | `docs/agent/github-token-boundaries.md` |
| Issue evidence | `docs/milestones/evidence/<task_id>/` |
| Final acceptance | Bridge gate result |

GitHub Issue numbers, URLs, labels, assignees, and comments are references only.

They must not replace stable task IDs such as `M4-T01`.

---

## 4. Planned Bridge Enhancements

### 4.1 `issue-plan`

Produces an issue execution-ticket plan from a milestone file.

Expected behavior:

- reads milestone task contracts
- reports whether each task has a `backend_refs.github_issue`
- detects duplicate issue refs
- does not write remote GitHub state

### 4.2 `issue-export`

Generates a GitHub Issue title/body from a task contract.

Expected behavior:

- includes task markers:
  - `agent-bridge:task-id`
  - `agent-bridge:canonical-owner`
  - `agent-bridge:task-revision`
- includes acceptance summary and path boundaries
- defaults to dry-run
- supports live write only when `--write` is explicitly provided
- does not store tokens

### 4.3 `issue-status`

Collects normalized GitHub Issue evidence.

Expected behavior:

- supports `--from-json <fixture-path>` offline mode
- supports explicit live read through `gh issue view`
- writes `github-issue.yaml` only with `--write-evidence`
- redacts token-like values
- detects marker drift
- detects duplicate issue refs when fixture data reports them
- marks closed issue without accepted Bridge gate as inconclusive

### 4.4 `issue-comment`

Generates a managed gate-summary comment body.

Expected behavior:

- defaults to dry-run
- may write `github-issue-comment.yaml`
- live comment write requires explicit `--write`
- comment body must be generated from Bridge gate facts
- must not post or write secrets

### 4.5 Gate Integration

Bridge gate may consume Issue evidence when a task declares `required_issue_evidence`.

Gate behavior:

- missing required issue evidence is `inconclusive`
- task marker mismatch is `failed`
- canonical owner marker mismatch is `failed`
- stale task revision is `inconclusive`
- duplicate issue for the same task is `failed`
- closed issue without accepted Bridge gate is `inconclusive`
- issue evidence alone cannot override verifier, reviewer, path policy, GitHub PR/CI, or blocker failures

### 4.6 Closeout Integration

Closeout should include:

- issue URL
- issue state
- issue task revision marker
- issue conclusion
- drift reason codes
- managed comment evidence when available

---

## 5. Security Boundary

Allowed runtime auth:

- existing authenticated `gh` CLI session
- `GH_TOKEN` or `GITHUB_TOKEN` provided at runtime by the caller

Forbidden:

- creating `.env`
- modifying `.env` or `.env.*`
- writing tokens to repo files
- printing tokens
- storing raw credential helper output
- committing raw GitHub API responses that include secrets

If live GitHub auth is unavailable, Bridge returns `inconclusive`.

Tests must use offline fixture mode and must not require live GitHub auth.

---

## 6. Acceptance

Phase 4 is acceptable only when:

- M1, M2, M3, and M4 validate.
- Existing Phase 1, Phase 2, and Phase 3 tests still pass.
- `issue-plan` works without network.
- `issue-export` generates canonical markers in dry-run mode.
- `issue-status` parses offline fixture data and writes `github-issue.yaml`.
- `issue-comment` generates a managed comment body without live write.
- Gate consumes required issue evidence.
- At least three Issue failure scenarios are blocked.
- Closeout includes issue evidence when available.
- No live GitHub write is performed in the implementation run.
- No token or secret is written to repo files.

If current implementation changes are uncommitted, do not claim final Phase 4 acceptance.
