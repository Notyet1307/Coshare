# GitHub Token Boundaries

Phase 4 may use GitHub authentication only at runtime.

Tokens are never repo artifacts.

---

## Allowed Runtime Sources

Allowed when explicitly requested:

- existing authenticated `gh` CLI session
- `GH_TOKEN` environment variable
- `GITHUB_TOKEN` environment variable

Bridge may rely on these sources only for explicit live GitHub operations.

Tests must not require them.

---

## Forbidden Storage

Do not:

- create `.env`
- modify `.env` or `.env.*`
- write tokens to evidence files
- write tokens to closeout files
- print tokens
- commit raw auth output
- commit credential helper output
- store GitHub cookies
- store authorization headers

Evidence and closeout may include GitHub URLs, issue numbers, PR numbers, check names, and non-secret state.

---

## Missing Auth

If live GitHub auth is required but unavailable, Bridge must return:

```text
inconclusive
```

The reason should be explicit, such as:

```text
github_auth_unavailable
```

Missing auth is not a failure by itself.

It is a runtime prerequisite gap.

---

## Redaction

Bridge must redact token-like values before writing evidence.

Token-like keys include:

- token
- authorization
- cookie
- password
- secret

Token-like values include GitHub token prefixes and bearer tokens.

Redacted values should be replaced with:

```text
[REDACTED]
```

---

## Live Write Boundary

Live issue create/edit/comment operations are not default behavior.

They require explicit `--write` and an explicit user request.

This implementation run must not perform live GitHub writes.
