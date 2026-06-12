# GitHub Evidence

Phase 3 introduces normalized GitHub PR/CI evidence.

Milestone docs remain canonical.

GitHub evidence supplements local evidence. It does not replace task contracts, path policy, verifier evidence, reviewer evidence, or closeout rules.

---

## Location

GitHub evidence lives under:

```text
docs/milestones/evidence/<task_id>/
```

Expected files:

- `github-pr.yaml`
- `github-ci.yaml`
- `github-reviews.yaml`
- `github-branch-protection.yaml`

All files must include:

```yaml
schema_version: 1
task_id: M3-T01
source: github
collection:
  mode: fixture
  network: false
  source: from-json
```

`collection.mode` must be one of:

- `fixture`
- `gh`

`collection.network` must be `false` for offline fixture input and `true` only for explicit live GitHub reads.

Collection metadata must not include token values, auth headers, cookies, or raw credential output.

---

## Collection Modes

### Offline Fixture Mode

Offline fixture mode is required for tests and local deterministic verification.

Command shape:

```bash
agent-bridge github-evidence --task M3-T01 --from-json <fixture-path> --write-evidence
```

Rules:

- must not require GitHub auth
- must not use network
- must parse fixture data into the same normalized evidence model as live reads
- may write evidence only when `--write-evidence` is provided
- must not write raw fixture data if it contains secrets

Fixture input should be normalized JSON with optional sections:

```json
{
  "github_pr": {},
  "github_ci": {},
  "github_reviews": {},
  "github_branch_protection": {}
}
```

### Live GitHub Mode

Live GitHub mode may use the `gh` CLI for read-only collection.

Command shapes:

```bash
agent-bridge github-evidence --task M3-T01 --repo Notyet1307/Coshare --pr <number> --dry-run
agent-bridge github-evidence --task M3-T01 --repo Notyet1307/Coshare --pr <number> --write-evidence
```

Rules:

- live network reads must be explicit
- dry-run/read-only behavior is the default
- missing auth returns `inconclusive`
- `--write-evidence` is required before writing files
- no GitHub write operation is allowed

---

## PR Evidence

File:

```text
github-pr.yaml
```

Minimum shape:

```yaml
schema_version: 1
task_id: M3-T01
source: github
collection:
  mode: gh
  network: true
  source: gh-cli
github_pr:
  repo: Notyet1307/Coshare
  pr_number: 1
  pr_url: https://github.com/Notyet1307/Coshare/pull/1
  state: open
  draft: false
  base_branch: main
  head_branch: phase-3-example
  base_sha: abc123
  head_sha: def456
  mergeable_state: clean
  queried_at: "2026-06-12T00:00:00Z"
  conclusion: pass
```

Rules:

- `repo` must be explicit.
- `pr_number` must be explicit.
- `head_sha` must be explicit.
- PR URL is a reference, not acceptance by itself.
- Draft PR is `inconclusive` unless explicitly allowed.
- Closed unmerged PR is `failed` when merge readiness is required.
- Missing PR evidence is `inconclusive` when required.
- `head_sha` is the GitHub value used for task evidence SHA consistency checks.
- If task evidence has a required `head_sha`, PR `head_sha` must match it.

---

## CI Evidence

File:

```text
github-ci.yaml
```

Minimum shape:

```yaml
schema_version: 1
task_id: M3-T01
source: github
collection:
  mode: gh
  network: true
  source: gh-cli
github_ci:
  repo: Notyet1307/Coshare
  head_sha: def456
  required_checks_known: true
  workflow_runs:
    - name: tests
      status: completed
      conclusion: success
      url: https://github.com/Notyet1307/Coshare/actions/runs/1
  check_runs:
    - name: tests
      status: completed
      conclusion: success
  status_checks: []
  conclusion: pass
```

Rules:

- `head_sha` must match PR evidence when both exist.
- `head_sha` must match task evidence when the task requires GitHub SHA consistency.
- Failed required checks are `failed`.
- Pending required checks are `inconclusive`.
- Unknown required checks are `inconclusive` unless the task says branch protection is not required.
- Missing CI evidence is `inconclusive` when required.

---

## Review Evidence

File:

```text
github-reviews.yaml
```

Minimum shape:

```yaml
schema_version: 1
task_id: M3-T01
source: github
collection:
  mode: gh
  network: true
  source: gh-cli
github_reviews:
  repo: Notyet1307/Coshare
  pr_number: 1
  reviews:
    - reviewer: octocat
      state: APPROVED
      commit_id: def456
      submitted_at: "2026-06-12T00:00:00Z"
  open_blocking_reviews: []
  conclusion: pass
```

Rules:

- Open requested changes are blocking.
- Unresolved blocking review state is `failed`.
- Missing review evidence is `inconclusive` when required.
- AI reviewer comments do not override failed checks.
- Review evidence is optional unless the active task contract requires it.

---

## Branch Protection Evidence

File:

```text
github-branch-protection.yaml
```

Minimum shape:

```yaml
schema_version: 1
task_id: M3-T01
source: github
collection:
  mode: gh
  network: true
  source: gh-cli
github_branch_protection:
  repo: Notyet1307/Coshare
  branch: main
  source_available: true
  required_checks:
    - tests
  requires_reviews: true
  conclusion: pass
```

Rules:

- If branch protection data is unavailable, use `conclusion: inconclusive`.
- Do not infer required checks from passing check runs alone.
- Branch protection evidence should not include credentials or raw auth errors.
- Branch protection evidence is optional unless the active task contract requires it.

---

## Closeout Summary

Closeout may summarize:

- PR URL
- PR state
- base/head SHA
- CI conclusion
- review conclusion
- required check availability
- evidence files

Closeout must not claim GitHub acceptance unless evidence supports it.

Closeout must not include tokens, auth headers, cookies, raw `gh auth token` output, or unredacted raw API responses.
