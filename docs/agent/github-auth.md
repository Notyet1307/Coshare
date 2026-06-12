# GitHub Auth

Phase 3 may read GitHub PR/CI evidence at runtime.

Authentication is a runtime prerequisite only.

Do not store GitHub credentials in this repository.

Tests and offline fixture parsing must not require GitHub authentication.

---

## Allowed Runtime Auth

Allowed:

- an already authenticated `gh` CLI session
- `GH_TOKEN` environment variable provided by the caller
- `GITHUB_TOKEN` environment variable provided by the caller
- short-lived read-only token supplied by the execution environment

Bridge may check whether auth is available.

Bridge must not print token values.

Bridge must not write token values.

Bridge must not call or store raw output from:

```bash
gh auth token
```

---

## Forbidden Auth Handling

Forbidden:

- creating `.env`
- modifying `.env`
- modifying `.env.*`
- writing tokens into docs
- writing tokens into evidence
- writing tokens into closeout
- writing tokens into test fixtures
- printing tokens in logs
- storing auth headers
- storing raw `gh auth token` output
- committing API debug logs

If auth is missing, Bridge should return:

```yaml
result: inconclusive
reasons:
  - code: github_auth_unavailable
```

Missing auth must not cause Bridge to prompt for credentials interactively.

Missing auth must not create `.env` or any other credential file.

---

## Token Scope

Prefer read-only access.

Suggested minimum capability:

- read repository metadata
- read pull requests
- read checks / statuses
- read workflow runs
- read reviews
- read branch protection when available

Do not require write scopes for Phase 3.

If a write scope is present in the caller's runtime environment, Bridge must still use read-only commands only.

---

## Redaction Rules

Bridge output must redact token-like values.

Redact:

- values of `GH_TOKEN`
- values of `GITHUB_TOKEN`
- `Authorization` headers
- bearer tokens
- classic GitHub PATs
- fine-grained token strings
- cookie headers

Evidence should store normalized facts only.

Do not store raw API responses unless they have been reviewed for secrets.

Do not store raw `gh` stderr/stdout when it might include credential helper output.

Auth failure messages may be summarized with stable reason codes only.

---

## Failure Modes

Missing or insufficient auth is not a failed task by itself.

It is `inconclusive` unless the task contract explicitly requires GitHub evidence and a valid token was available.

Unavailable branch protection data is also `inconclusive`, not pass.

Offline fixture mode does not require auth and should never inspect token environment variables.

Live GitHub mode may inspect auth availability only after the user explicitly requests a live read with `--repo` and `--pr`.

---

## Runtime Commands

Preferred runtime tools:

```bash
gh pr view
gh api
gh run list
gh pr checks
```

These commands must be used read-only.

Network access must be explicit. Bridge must not make live GitHub calls by default when offline fixture input is supplied.

Do not call:

```bash
gh pr create
gh pr merge
gh issue create
gh issue edit
git push
```
