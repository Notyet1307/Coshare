# Phase 3 Development Plan

Version: 0.1
Phase: GitHub PR/CI Evidence Adapter
Canonical task source: repo milestone doc
Execution backend: local git plus read-only GitHub evidence
Platform integrations: GitHub read-only evidence only
Default network behavior: offline / no network unless explicitly requested

---

## 0. Phase 3 Decision

Phase 3 adds a read-only GitHub PR/CI evidence adapter on top of the Phase 1 and Phase 2 governance baseline.

Phase 3 keeps milestone docs as the canonical task source.

GitHub data is evidence, not task authority.

Phase 3 may collect:

- pull request metadata
- pull request branch, base, head, and mergeability facts
- commit SHA consistency
- GitHub Actions workflow runs
- check run and status check conclusions
- PR review summary
- branch protection and required check documentation when available
- closeout links to PR, CI, and review evidence

Phase 3 does not create PRs, merge PRs, push branches, sync issues, or call model APIs.

---

## 1. Source Material

Read first:

- `AGENTS.md`
- `chatgpt-pro-agent-workflow-roadmap.md`
- `phase-1-development-plan.md`
- `phase-2-development-plan.md`
- `docs/milestones/M1.md`
- `docs/milestones/M2.md`
- `docs/milestones/closeout/M1.md`
- `docs/milestones/closeout/M2.md`
- `docs/agent/*`
- `tools/agent-bridge/README.md`

If Phase 1 or Phase 2 gate evidence is not accepted, stop before implementing Phase 3.

---

## 2. Phase 3 Scope

Phase 3 is a GitHub PR/CI Evidence Adapter.

Allowed:

- read PR metadata
- read PR base/head branch and SHA facts
- read PR mergeability facts when available
- read GitHub Actions workflow runs
- read check runs and status checks
- read PR review summaries
- read branch protection / required check documentation when feasible
- write normalized evidence under `docs/milestones/evidence/<task_id>/`
- let Bridge gate consume GitHub evidence
- let closeout include PR/CI/review links and summaries

Forbidden:

- GitHub Issue as canonical task source
- GitHub Issue sync
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
- storing raw GitHub auth output in repo files

---

## 3. Canonical Ownership

| Information type | Phase 3 source of truth |
|---|---|
| Task scope | `docs/milestones/M3.md` |
| Acceptance criteria | `docs/milestones/M3.md` |
| Allowed / forbidden paths | `docs/milestones/M3.md` |
| Lifecycle status | `docs/milestones/M3.md` |
| GitHub auth rules | `docs/agent/github-auth.md` |
| GitHub evidence schemas | `docs/agent/github-evidence.md` |
| PR/CI gate rules | `docs/agent/pr-ci-gates.md` |
| Evidence | `docs/milestones/evidence/<task_id>/` |
| Closeout | `docs/milestones/closeout/M3.md` |
| Final acceptance | Bridge gate result |

GitHub PR numbers, PR URLs, issue IDs, branch names, and CI URLs are evidence references only.

They are not primary task IDs.

---

## 4. Runtime Auth Boundary

Phase 3 may require read-only GitHub runtime authentication.

Allowed runtime sources:

- authenticated `gh` CLI session
- `GH_TOKEN` / `GITHUB_TOKEN` environment variable provided by the caller
- GitHub API token available only at process runtime

Forbidden:

- creating `.env`
- modifying `.env` or `.env.*`
- writing tokens to repo files
- printing tokens
- storing auth headers
- storing raw credential helper output
- committing API debug logs

If authentication is missing, Bridge should return `inconclusive` with a clear prerequisite reason.

Tests must not require live GitHub authentication.

Offline fixture mode must work without GitHub auth.

Live GitHub reads must be explicit and read-only.

---

## 5. Planned Bridge Enhancements

### 5.1 `github-evidence`

Collects normalized GitHub evidence for a task.

Inputs should include:

- `--task`
- `--milestone`
- `--repo`
- `--pr`
- `--from-json <fixture-path>`
- `--write-evidence`
- optional `--head-sha`
- optional `--dry-run`
- optional `--json`

Default behavior should be dry-run/read-only.

Network calls must not be the default. Live GitHub reads are allowed only when the caller explicitly provides live GitHub inputs such as `--repo` and `--pr` without `--from-json`.

Offline fixture mode must parse normalized JSON input and produce the same internal evidence model used by live reads.

When `--write-evidence` is provided, it may write only under the task managed evidence path.

Expected written files:

- `github-pr.yaml`
- `github-ci.yaml`
- `github-reviews.yaml` when review data is available or required
- `github-branch-protection.yaml` when branch protection data is available or required

It must not create issues, create PRs, push, merge, or mutate GitHub state.

Expected command shapes:

```bash
agent-bridge github-evidence --task M3-T01 --repo Notyet1307/Coshare --pr <number> --dry-run
agent-bridge github-evidence --task M3-T01 --repo Notyet1307/Coshare --pr <number> --write-evidence
agent-bridge github-evidence --task M3-T01 --from-json <fixture-path> --write-evidence
```

### 5.2 Gate Integration

Bridge gate may consume GitHub evidence files when the task contract requires them.

Gate behavior:

- missing required GitHub evidence is `inconclusive`.
- missing GitHub auth for required live evidence is `inconclusive`.
- PR closed without merge is `failed` when merge is required.
- PR draft state is `inconclusive` unless explicitly allowed.
- PR head SHA must match the task evidence head SHA when both are available.
- PR head SHA mismatch against task evidence is `failed`.
- unavailable task evidence head SHA is `inconclusive` when the task requires SHA consistency.
- failed required checks are `failed`.
- pending or unavailable required checks are `inconclusive`.
- open blocking reviews are `failed`.
- unavailable branch protection data is `inconclusive`, not pass.

### 5.3 Closeout Integration

Closeout should include:

- PR URL
- PR number
- base/head branch
- base/head SHA
- CI/check summary
- review summary
- branch protection / required checks summary when available
- evidence file references

Closeout must preserve manual notes outside managed blocks.

Closeout must not include tokens, auth headers, raw credential output, or raw API responses that have not been redacted.

---

## 6. Evidence Files

Expected Phase 3 GitHub evidence files:

```text
docs/milestones/evidence/<task_id>/
  github-pr.yaml
  github-ci.yaml
  github-reviews.yaml
  github-branch-protection.yaml
```

These files supplement existing evidence:

- `path-policy.yaml`
- `verifier.yaml`
- `reviewer.yaml`
- `functional-test.yaml`
- `blockers.yaml`
- `gate-report.yaml`

GitHub evidence should include collection metadata:

```yaml
collection:
  mode: fixture
  network: false
  source: from-json
```

or:

```yaml
collection:
  mode: gh
  network: true
  source: gh-cli
```

Collection metadata must not include token values.

---

## 7. M3 Task Sequence

Phase 3 is tracked in:

```text
docs/milestones/M3.md
```

Expected task sequence:

1. `M3-T01` Phase 3 plan/docs
2. `M3-T02` GitHub auth/runtime boundary
3. `M3-T03` GitHub PR evidence schema
4. `M3-T04` GitHub CI/check evidence schema
5. `M3-T05` GitHub review evidence schema
6. `M3-T06` Bridge `github-evidence` command
7. `M3-T07` gate integration for PR/CI evidence
8. `M3-T08` closeout integration
9. `M3-T09` dogfood on a real PR or safe test PR
10. `M3-T10` independent verification and closeout

---

## 8. Acceptance

Phase 3 is accepted when:

- existing Phase 1 and Phase 2 tests still pass.
- `docs/milestones/M1.md`, `docs/milestones/M2.md`, and `docs/milestones/M3.md` validate.
- `docs/milestones/M3.md` validates.
- GitHub auth boundaries are documented.
- GitHub evidence schemas are documented.
- `github-evidence` can parse offline fixture data without network or live auth.
- `github-evidence` can write `github-pr.yaml` and `github-ci.yaml`.
- Bridge can collect read-only PR/CI/review evidence or return clear inconclusive prerequisites.
- Bridge gate consumes GitHub evidence when required.
- Bridge returns `inconclusive` when required GitHub evidence is missing.
- Bridge fails when a required CI conclusion is failure.
- Bridge accepts GitHub evidence only when PR head SHA matches task evidence head SHA where required.
- Bridge detects failed CI checks.
- Bridge detects open blocking PR reviews.
- closeout includes PR URL, CI/check results, and review summary when available.
- at least one safe PR dogfood flow is recorded.
- no GitHub tokens are written to repo files.
- no external write integration is added.
- no GitHub Issue sync, auto-merge, PR creation, push automation, or model API behavior is added.

---

## 9. Compatibility Rule

Do not break Phase 1 or Phase 2.

Existing commands must keep working:

- `validate`
- `task-info`
- `diff-check`
- `evidence-init`
- `prompt-pack`
- `gate`
- `closeout`

Phase 3 commands must support explicit milestone paths, for example:

```bash
tools/agent-bridge/agent-bridge github-evidence --task M3-T06 --milestone docs/milestones/M3.md --repo Notyet1307/Coshare --pr 1
```

Do not modify M1 or M2 evidence unless a task explicitly requires compatibility evidence.
