# GitHub Comment Boundaries

GitHub comments are communication surfaces.

They are not canonical task state and not final acceptance evidence by themselves.

---

## Managed Status Comment

Managed status comments must use markers:

```md
<!-- agent-bridge:status-comment:start M5-T01 -->
...
<!-- agent-bridge:status-comment:end M5-T01 -->
```

The comment body should summarize:

- task ID
- canonical source
- Bridge gate result
- delivery status
- issue reference
- PR reference
- CI/check summary
- review summary
- closeout reference

It must not include raw logs or secrets.

---

## Idempotency

When live writes are implemented or authorized, Bridge should update an existing managed comment when possible.

It should not create duplicate managed comments.

Duplicate managed comments must be reported as inconclusive or failed by policy.

---

## Security

Do not print or write:

- tokens
- auth headers
- cookies
- credential helper output
- raw private comments
- raw CI logs

Missing auth should return `inconclusive` with a clear reason.
